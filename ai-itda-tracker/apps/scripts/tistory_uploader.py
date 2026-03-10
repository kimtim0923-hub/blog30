"""
tistory_uploader.py — Selenium으로 티스토리 자동 글 발행
역할: Google Sheets '블로그 콘텐츠' 시트에서 '글완성' 항목을 읽어
      카카오 계정으로 티스토리에 자동 로그인 후 글을 발행한다.

실행: python tistory_uploader.py
      python tistory_uploader.py --headless  (브라우저 숨김)
"""

import os
import sys
import time
import argparse
from datetime import datetime

import markdown
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

from sheets_client import SheetsClient

# .env 로드
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".env")

# 대기 시간 설정 (초)
WAIT_TIMEOUT  = 15
SHORT_WAIT    = 2
MEDIUM_WAIT   = 3


def setup_driver(headless: bool = False) -> webdriver.Chrome:
    """Chrome WebDriver 초기화 (webdriver-manager 자동 설치)."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1280,900")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 자동화 탐지 우회
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def save_screenshot(driver: webdriver.Chrome, prefix: str = "error") -> str:
    """에러 발생 시 스크린샷 저장. 저장 경로 반환."""
    screenshots_dir = _SCRIPT_DIR.parent.parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = screenshots_dir / f"{prefix}_{timestamp}.png"
    driver.save_screenshot(str(path))
    print(f"  📸 스크린샷 저장: {path}")
    return str(path)


def login(driver: webdriver.Chrome, blog_name: str,
          kakao_id: str, kakao_pw: str) -> bool:
    """
    티스토리 카카오 계정 로그인.
    blog_name: 예) myai.tistory.com 또는 myai
    """
    # blog_name 정규화
    if not blog_name.endswith(".tistory.com"):
        blog_name = blog_name + ".tistory.com"

    login_url = f"https://{blog_name}/manage"
    print(f"  🌐 접속: {login_url}")

    try:
        driver.get(login_url)
        wait = WebDriverWait(driver, WAIT_TIMEOUT)

        # "카카오계정으로 로그인" 버튼 클릭 (여러 셀렉터 시도)
        try:
            kakao_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "a.btn_kakao, a[href*='kakao'], .kakao_btn, "
                                      "a.login_btn_kakao, a[data-provider='kakao'], "
                                      ".link_kakao_id, .btn_login.link_kakao")
                )
            )
        except TimeoutException:
            # CSS 실패 시 텍스트로 찾기
            kakao_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(), '카카오') and (contains(text(), '로그인') or contains(text(), '계정'))]")
                )
            )
        kakao_btn.click()
        print("  🔑 카카오 로그인 버튼 클릭")
        time.sleep(SHORT_WAIT)

        # 이메일 입력
        id_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input#loginId, input[name='loginId'], "
                                  "input[type='email'], input#id_email")
            )
        )
        id_input.clear()
        id_input.send_keys(kakao_id)
        time.sleep(0.5)

        # 비밀번호 입력
        pw_input = driver.find_element(
            By.CSS_SELECTOR,
            "input#password, input[name='password'], input[type='password']"
        )
        pw_input.clear()
        pw_input.send_keys(kakao_pw)
        time.sleep(0.5)

        # 로그인 버튼 클릭
        submit_btn = driver.find_element(
            By.CSS_SELECTOR,
            "button[type='submit'], .btn_login, #loginBtn"
        )
        submit_btn.click()
        print("  ✅ 로그인 시도 중...")
        time.sleep(MEDIUM_WAIT)

        # 로그인 성공 확인 (관리 페이지 URL로 이동됐는지)
        wait.until(EC.url_contains("tistory.com"))
        if "manage" in driver.current_url or "write" in driver.current_url:
            print("  ✅ 로그인 성공!")
            return True

        # 2차 인증이나 추가 확인이 필요한 경우 대기
        time.sleep(MEDIUM_WAIT)
        if "tistory.com" in driver.current_url:
            return True

        print(f"  ⚠️ 로그인 후 예상 URL 아님: {driver.current_url}")
        return False

    except TimeoutException:
        print("  ❌ 로그인 타임아웃 — 버튼이나 입력창을 찾지 못했습니다.")
        save_screenshot(driver, "login_timeout")
        return False
    except Exception as e:
        print(f"  ❌ 로그인 오류: {e}")
        save_screenshot(driver, "login_error")
        return False


def post_article(driver: webdriver.Chrome, blog_name: str,
                 title: str, content: str,
                 category: str = "생산성툴") -> bool:
    """
    티스토리 새 글 작성 및 발행.
    blog_name: 예) myai (도메인 없이)
    """
    if blog_name.endswith(".tistory.com"):
        blog_name = blog_name.replace(".tistory.com", "")

    # 마크다운 → HTML 변환
    content = markdown.markdown(
        content,
        extensions=['tables', 'fenced_code', 'nl2br']
    )
    print(f"  🔄 마크다운 → HTML 변환 완료 ({len(content)}자)")

    write_url = f"https://{blog_name}.tistory.com/manage/newpost"
    print(f"  ✏️ 글쓰기 페이지 이동: {write_url}")

    try:
        driver.get(write_url)
        time.sleep(MEDIUM_WAIT)

        # 임시 저장 글 알림 처리 ("이어서 작성하시겠습니까?")
        try:
            alert = driver.switch_to.alert
            print(f"  ℹ️ 알림 팝업 감지: {alert.text[:40]}...")
            alert.dismiss()  # "취소" — 새 글 작성
            time.sleep(SHORT_WAIT)
        except Exception:
            pass  # 알림 없으면 무시

        wait = WebDriverWait(driver, WAIT_TIMEOUT)

        # ── 카테고리 선택 ──
        try:
            # 카테고리 드롭다운 클릭
            cat_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//button[contains(text(), '카테고리')] | "
                     "//span[contains(text(), '카테고리')]/parent::* | "
                     "//div[contains(@class, 'category')]//button | "
                     "//select[contains(@class, 'category')]")
                )
            )
            cat_btn.click()
            time.sleep(1)

            # 카테고리 목록에서 선택
            cat_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     f"//li[contains(text(), '{category}')] | "
                     f"//option[contains(text(), '{category}')] | "
                     f"//span[contains(text(), '{category}')] | "
                     f"//a[contains(text(), '{category}')]")
                )
            )
            cat_option.click()
            print(f"  🏷️ 카테고리 설정: {category}")
            time.sleep(1)
        except (TimeoutException, NoSuchElementException):
            print(f"  ⚠️ 카테고리 '{category}' 설정 실패 — 수동 확인 필요")
            save_screenshot(driver, "category_fail")

        # ── 제목 입력 (새 에디터: placeholder "제목을 입력하세요") ──
        try:
            # 방법 1: placeholder 텍스트가 있는 요소 클릭 후 입력
            title_el = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(@placeholder, '제목') or contains(text(), '제목을 입력')]")
                )
            )
        except TimeoutException:
            # 방법 2: contenteditable 제목 영역
            title_el = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "input#post-title-inp, input[placeholder*='제목'], "
                     "[contenteditable='true']:first-of-type, .tit_post")
                )
            )
        title_el.click()
        time.sleep(0.5)
        # 기존 내용 지우고 입력 (macOS: Command+A)
        title_el.send_keys(Keys.COMMAND + "a")
        title_el.send_keys(title)
        print(f"  📝 제목 입력: {title[:40]}...")
        time.sleep(SHORT_WAIT)

        # ── 본문 입력 (TinyMCE iframe 에디터) ──
        try:
            # TinyMCE iframe 찾기
            iframe = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id*='editor'], iframe[id*='tiny'], "
                                      "iframe[id*='mce'], iframe.tox-edit-area__iframe")
                )
            )
            driver.switch_to.frame(iframe)
            body = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "body#tinymce, body[contenteditable='true'], body")
                )
            )
            body.click()
            body.send_keys(Keys.COMMAND + "a")
            body.send_keys(Keys.DELETE)
            # HTML 콘텐츠 주입 (JavaScript)
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            driver.execute_script(
                "document.body.innerHTML = arguments[0];", content
            )
            driver.switch_to.default_content()
            print("  📄 TinyMCE 에디터에 본문 입력")
        except (TimeoutException, NoSuchElementException):
            driver.switch_to.default_content()
            # contenteditable div 폴백
            try:
                editor = driver.find_element(
                    By.CSS_SELECTOR,
                    "[contenteditable='true'].mce-content-body, "
                    "[contenteditable='true']"
                )
                editor.click()
                editor.send_keys(Keys.COMMAND + "a")
                editor.send_keys(Keys.DELETE)
                editor.send_keys(content)
                print("  📄 contenteditable 에디터에 본문 입력")
            except NoSuchElementException:
                print("  ❌ 에디터를 찾을 수 없습니다.")
                save_screenshot(driver, "editor_not_found")
                return False

        time.sleep(SHORT_WAIT)

        # ── 발행: "완료" 버튼 클릭 ──
        try:
            publish_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), '완료')]")
                )
            )
        except TimeoutException:
            publish_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "button.btn_publish, button#publish-btn, "
                     "button.btn-publish, button.submit, "
                     "button[class*='publish'], button[class*='complete']")
                )
            )
        publish_btn.click()
        print("  🚀 '완료' 버튼 클릭")
        time.sleep(MEDIUM_WAIT)

        # 발행 설정 모달 처리
        time.sleep(SHORT_WAIT)

        # ── 비공개 선택 ──
        try:
            # 방법 1: "비공개" 텍스트가 포함된 라디오/버튼/span 클릭
            private_el = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//label[contains(text(), '비공개')] | "
                     "//span[contains(text(), '비공개')] | "
                     "//input[@value='private' or @value='PRIVATE']/.. | "
                     "//button[contains(text(), '비공개')]")
                )
            )
            private_el.click()
            print("  🔒 비공개 선택 완료")
            time.sleep(1)
        except TimeoutException:
            # 방법 2: JavaScript로 비공개 라디오 선택
            try:
                result = driver.execute_script("""
                    // "비공개" 텍스트를 가진 요소 찾아서 클릭
                    var els = document.querySelectorAll('label, span, div, button');
                    for (var i = 0; i < els.length; i++) {
                        if (els[i].textContent.trim() === '비공개') {
                            els[i].click();
                            return 'clicked';
                        }
                    }
                    // 라디오 input 직접 선택
                    var radios = document.querySelectorAll('input[type="radio"]');
                    for (var i = 0; i < radios.length; i++) {
                        if (radios[i].value === 'private' || radios[i].value === 'PRIVATE') {
                            radios[i].click();
                            return 'radio_clicked';
                        }
                    }
                    return 'not_found';
                """)
                if result and 'clicked' in result:
                    print("  🔒 비공개 선택 완료 (JS)")
                else:
                    print("  ⚠️ 비공개 옵션을 찾지 못했습니다 — 수동 확인 필요")
                    save_screenshot(driver, "private_fail")
            except Exception as e:
                print(f"  ⚠️ 비공개 설정 실패: {e}")
                save_screenshot(driver, "private_fail")

        time.sleep(1)

        # ── 최종 발행 버튼 클릭 ──
        try:
            confirm_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "//button[contains(text(), '발행')]")
                )
            )
            confirm_btn.click()
            print("  ✅ 비공개 발행 버튼 클릭")
            time.sleep(MEDIUM_WAIT)
        except TimeoutException:
            pass

        print(f"  ✅ 글 비공개 발행 완료!")
        return True

    except TimeoutException as e:
        print(f"  ❌ 타임아웃: {e}")
        save_screenshot(driver, "post_timeout")
        return False
    except Exception as e:
        print(f"  ❌ 글 작성 오류: {e}")
        save_screenshot(driver, "post_error")
        return False


def main(headless: bool = False):
    """블로그 콘텐츠 시트에서 '글완성' 항목을 순차 업로드."""
    print("=" * 55)
    print("tistory_uploader.py — 티스토리 자동 업로드 시작")
    print("=" * 55)

    # 환경변수 확인
    tistory_id   = os.environ.get("TISTORY_ID", "")
    tistory_pw   = os.environ.get("TISTORY_PW", "")
    blog_name    = os.environ.get("TISTORY_BLOG_NAME", "")

    missing = []
    if not tistory_id or "카카오" in tistory_id:
        missing.append("TISTORY_ID")
    if not tistory_pw or "비밀번호" in tistory_pw:
        missing.append("TISTORY_PW")
    if not blog_name or "블로그이름" in blog_name:
        missing.append("TISTORY_BLOG_NAME")

    if missing:
        print(f"❌ 다음 환경변수가 .env에 설정되지 않았습니다: {', '.join(missing)}")
        print("   apps/scripts/.env 파일을 열어 값을 입력하세요.")
        return

    # Sheets에서 업로드 대기 목록 조회
    sheets = SheetsClient()
    articles = sheets.get_ready_to_upload()

    if not articles:
        print("✅ 업로드할 글이 없습니다 (글완성 상태 없음).")
        return

    print(f"\n📋 업로드 대기: {len(articles)}개")
    if not headless:
        print("  ℹ️ 브라우저가 표시됩니다. 로그인 과정을 확인하세요.")

    driver = setup_driver(headless=headless)
    success_count = 0
    fail_count = 0

    try:
        # 로그인 (한 번만)
        print(f"\n🔑 티스토리 로그인 중: {blog_name}")
        logged_in = login(driver, blog_name, tistory_id, tistory_pw)

        if not logged_in:
            print("❌ 로그인 실패 — 업로드를 중단합니다.")
            print("   .env의 TISTORY_ID / TISTORY_PW 를 확인하세요.")
            return

        # 글 순차 업로드 (비공개 발행)
        for i, article in enumerate(articles, 1):
            name    = article["name"]
            title   = article["title"]
            content = article["content"]

            print(f"\n[{i}/{len(articles)}] 업로드: {name}")
            print(f"  제목: {title[:50]}...")

            success = post_article(driver, blog_name, title, content)

            if success:
                sheets.update_upload_status(name, "업로드완료")
                sheets.update_blog_status(name, "업로드완료")
                success_count += 1
                print(f"  ✅ 업로드 완료: {name}")
            else:
                sheets.update_upload_status(name, "업로드오류")
                fail_count += 1
                print(f"  ❌ 업로드 실패: {name}")

            # 글 사이 대기
            if i < len(articles):
                print("  ⏳ 5초 대기...")
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n⚠️ 사용자가 중단했습니다.")
    finally:
        driver.quit()

    print("\n" + "=" * 55)
    print(f"✅ 완료 — 성공: {success_count}개 | 실패: {fail_count}개")
    print("스프레드시트 '블로그 콘텐츠' 시트에서 결과를 확인하세요.")
    print("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="티스토리 자동 업로더")
    parser.add_argument(
        "--headless", action="store_true",
        help="브라우저를 숨기고 실행 (기본: 브라우저 표시)"
    )
    args = parser.parse_args()
    main(headless=args.headless)
