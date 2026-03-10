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
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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

        # "카카오계정으로 로그인" 버튼 클릭
        kakao_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a.btn_kakao, a[href*='kakao'], .kakao_btn, "
                                  "a.login_btn_kakao, a[data-provider='kakao']")
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
                 category: str = "AI 툴 리뷰") -> bool:
    """
    티스토리 새 글 작성 및 발행.
    blog_name: 예) myai (도메인 없이)
    """
    if blog_name.endswith(".tistory.com"):
        blog_name = blog_name.replace(".tistory.com", "")

    write_url = f"https://{blog_name}.tistory.com/manage/post/write"
    print(f"  ✏️ 글쓰기 페이지 이동: {write_url}")

    try:
        driver.get(write_url)
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        time.sleep(MEDIUM_WAIT)

        # ── 제목 입력 ──
        title_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 "input#post-title-inp, input[placeholder*='제목'], "
                 ".title_area input, input.txt_tit")
            )
        )
        title_input.click()
        title_input.clear()
        title_input.send_keys(title)
        print(f"  📝 제목 입력: {title[:40]}...")
        time.sleep(SHORT_WAIT)

        # ── HTML 모드 전환 ──
        # 기본 에디터(iframe)에서 HTML 모드로 전환 시도
        try:
            html_btn = driver.find_element(
                By.CSS_SELECTOR,
                "button[data-mode='html'], button.btn_html, "
                "button[title='HTML'], .toolbar_item_html"
            )
            html_btn.click()
            print("  🔄 HTML 모드 전환")
            time.sleep(SHORT_WAIT)
        except NoSuchElementException:
            print("  ℹ️ HTML 모드 버튼 없음 — 기본 에디터 사용")

        # ── 본문 입력 ──
        # iframe 에디터인 경우
        try:
            iframe = driver.find_element(
                By.CSS_SELECTOR,
                "iframe#editor-tistory, iframe.tistory-editor, "
                "iframe[id*='editor']"
            )
            driver.switch_to.frame(iframe)
            body = driver.find_element(By.CSS_SELECTOR, "body, #tinymce")
            body.click()
            # 기존 내용 전체 선택 후 교체
            body.send_keys(Keys.CONTROL + "a")
            body.send_keys(Keys.DELETE)
            body.send_keys(content)
            driver.switch_to.default_content()
            print("  📄 iframe 에디터에 본문 입력")
        except NoSuchElementException:
            # contenteditable div 에디터인 경우
            editor = driver.find_element(
                By.CSS_SELECTOR,
                "[contenteditable='true'], .ProseMirror, "
                ".toastui-editor-contents, #editor-content"
            )
            editor.click()
            editor.send_keys(Keys.CONTROL + "a")
            editor.send_keys(Keys.DELETE)
            editor.send_keys(content)
            print("  📄 contenteditable 에디터에 본문 입력")

        time.sleep(SHORT_WAIT)

        # ── 카테고리 설정 ──
        try:
            cat_select = driver.find_element(
                By.CSS_SELECTOR,
                "select#category, select[name='categoryId'], "
                ".category_select select"
            )
            options = cat_select.find_elements(By.TAG_NAME, "option")
            for opt in options:
                if category in opt.text:
                    opt.click()
                    print(f"  🏷️ 카테고리 설정: {category}")
                    break
        except NoSuchElementException:
            print(f"  ℹ️ 카테고리 '{category}' 설정 생략 (없거나 다른 형태)")

        time.sleep(SHORT_WAIT)

        # ── 발행 버튼 클릭 ──
        publish_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "button.btn_publish, button#publish-btn, "
                 "button[class*='publish'], button.submit")
            )
        )
        publish_btn.click()
        print("  🚀 발행 버튼 클릭")
        time.sleep(MEDIUM_WAIT)

        # 발행 확인 팝업이 있는 경우 처리
        try:
            confirm_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "button.btn_ok, button.btn_confirm, "
                     ".layer_confirm button.btn_blue")
                )
            )
            confirm_btn.click()
            print("  ✅ 발행 확인 팝업 처리")
            time.sleep(MEDIUM_WAIT)
        except TimeoutException:
            pass  # 팝업 없으면 넘어감

        # 발행 성공 확인 (URL 변화)
        if "/manage/post/" not in driver.current_url:
            print(f"  ✅ 글 발행 완료!")
            return True
        else:
            print(f"  ⚠️ 발행 후 URL 확인 필요: {driver.current_url}")
            return True  # URL이 그대로여도 성공으로 처리 (에디터 형태에 따라 다름)

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

        # 글 순차 업로드
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
