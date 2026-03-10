"""
sheets_client.py — Google Sheets 읽기/쓰기 공통 모듈
역할: gspread로 TAAFT Tracker 스프레드시트를 읽고 쓰는 공통 클라이언트

스프레드시트 ID: 1WXJ-6pbTv8Dg-fYhNyvKK98wo8VWonxo8TZPk6I-H1A
시트 구조:
  툴 DB   : A툴이름 B태그라인 C타프트카테고리 D AI있다카테고리 E가격 F출시 G저장수 H타겟? I블로그작성상태 J첫수집일
  블로그 콘텐츠: A툴이름 B제목 C내용 D생성일시 E업로드상태 (없으면 자동 생성)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# .env 로드 (이 파일 위치 기준, 기존 환경변수를 덮어쓰지 않음)
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".env", override=False)

# Google Sheets API 스코프
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# 툴 DB 컬럼 인덱스 (0-based)
COL_NAME       = 0   # A: 툴 이름
COL_TAGLINE    = 1   # B: 태그라인
COL_TAAFT_CAT  = 2   # C: TAAFT 카테고리
COL_AI_CAT     = 3   # D: AI있다 카테고리
COL_PRICE      = 4   # E: 가격
COL_RELEASED   = 5   # F: 출시
COL_SAVES      = 6   # G: 저장수
COL_TARGET     = 7   # H: AI있다 타겟?
COL_BLOG_STATUS= 8   # I: 블로그 작성 상태
COL_FIRST_DATE = 9   # J: 첫 수집일

# 블로그 콘텐츠 시트 컬럼 (0-based)
BLOG_COL_NAME     = 0  # A: 툴이름
BLOG_COL_TITLE    = 1  # B: 블로그 제목
BLOG_COL_CONTENT  = 2  # C: 내용
BLOG_COL_CREATED  = 3  # D: 생성일시
BLOG_COL_STATUS   = 4  # E: 업로드 상태
BLOG_COL_TYPE     = 5  # F: 글 유형 (B/C/D/E)


class SheetsClient:
    """Google Sheets TAAFT Tracker 읽기/쓰기 클라이언트"""

    def __init__(self):
        creds_env = os.environ.get("GOOGLE_CREDENTIALS_JSON", "./credentials.json")
        spreadsheet_id = os.environ.get("SPREADSHEET_ID", "")

        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID가 .env에 설정되지 않았습니다.")

        # Railway 배포: 환경변수에 JSON 내용 직접 입력 → json.loads로 파싱
        # 로컬: 파일 경로 → from_service_account_file로 로드
        import json
        if creds_env.strip().startswith("{"):
            # JSON 문자열이 직접 들어온 경우 (Railway 등 클라우드 배포)
            creds_info = json.loads(creds_env)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            # 파일 경로인 경우 (로컬 개발)
            creds_path = creds_env
            if not Path(creds_path).exists():
                raise FileNotFoundError(
                    f"credentials.json을 찾을 수 없습니다: {creds_path}\n"
                    "Google Cloud Console에서 서비스 계정 키를 다운로드하세요."
                )
            creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        print(f"✅ 스프레드시트 연결 완료: {self.spreadsheet.title}")

    # ──────────────────────────────────────
    # 툴 DB 읽기
    # ──────────────────────────────────────

    def get_target_tools(self) -> list[dict]:
        """
        툴 DB에서 AI있다 타겟 ✅ + 블로그 미작성 항목만 반환.
        반환: [{ name, tagline, taaft_category, ai_category, price, released, saves, row_index }, ...]
        """
        sheet = self.spreadsheet.worksheet("📦 툴 DB")
        rows = sheet.get_all_values()

        if len(rows) <= 1:
            print("⚠️ 툴 DB에 데이터가 없습니다.")
            return []

        results = []
        for i, row in enumerate(rows[1:], start=2):  # 헤더 스킵, 1-based row
            # 행이 짧으면 패딩
            while len(row) < 10:
                row.append("")

            target_val = row[COL_TARGET].strip()   # H열: 타겟?
            status_val = row[COL_BLOG_STATUS].strip()  # I열: 블로그작성상태

            is_target = "타겟" in target_val
            is_pending = status_val in ("미작성", "")

            if is_target and is_pending:
                results.append({
                    "name":          row[COL_NAME].strip(),
                    "tagline":       row[COL_TAGLINE].strip(),
                    "taaft_category":row[COL_TAAFT_CAT].strip(),
                    "ai_category":   row[COL_AI_CAT].strip(),
                    "price":         row[COL_PRICE].strip(),
                    "released":      row[COL_RELEASED].strip(),
                    "saves":         row[COL_SAVES].strip(),
                    "row_index":     i,   # 업데이트 시 사용
                })

        print(f"📋 블로그 생성 대상 툴: {len(results)}개")
        return results

    # ──────────────────────────────────────
    # 툴 DB 상태 업데이트
    # ──────────────────────────────────────

    def update_blog_status(self, tool_name: str, status: str) -> bool:
        """
        툴 DB의 I열(블로그 작성 상태)을 업데이트.
        status: "미작성" | "생성중" | "글완성" | "생성오류" | "업로드완료" | "업로드오류"
        """
        try:
            sheet = self.spreadsheet.worksheet("📦 툴 DB")
            cell = sheet.find(tool_name, in_column=COL_NAME + 1)  # gspread는 1-based
            if cell is None:
                print(f"⚠️ 툴을 찾을 수 없음: {tool_name}")
                return False
            sheet.update_cell(cell.row, COL_BLOG_STATUS + 1, status)
            print(f"  📝 상태 업데이트: {tool_name} → {status}")
            return True
        except Exception as e:
            print(f"  ❌ 상태 업데이트 실패 ({tool_name}): {e}")
            return False

    # ──────────────────────────────────────
    # 블로그 콘텐츠 시트 저장
    # ──────────────────────────────────────

    def _get_or_create_blog_sheet(self) -> gspread.Worksheet:
        """블로그 콘텐츠 시트가 없으면 생성."""
        try:
            return self.spreadsheet.worksheet("블로그 콘텐츠")
        except gspread.WorksheetNotFound:
            print("📄 '블로그 콘텐츠' 시트를 새로 생성합니다...")
            sheet = self.spreadsheet.add_worksheet(
                title="블로그 콘텐츠", rows=200, cols=7
            )
            sheet.append_row(
                ["툴이름", "블로그 제목", "내용", "생성일시", "업로드 상태", "글 유형"],
                value_input_option="RAW"
            )
            return sheet

    def save_blog_content(self, tool_name: str, title: str, content: str,
                          blog_type: str = "B") -> bool:
        """
        생성된 블로그 글을 '블로그 콘텐츠' 시트에 저장.
        이미 존재하면 덮어쓰기.
        blog_type: "B" | "C" | "D" | "E"
        """
        try:
            sheet = self._get_or_create_blog_sheet()
            now = datetime.now().strftime("%Y-%m-%d %H:%M")

            # 기존 행 검색
            existing = sheet.find(tool_name, in_column=BLOG_COL_NAME + 1)
            row_data = [tool_name, title, content, now, "글완성", blog_type]

            if existing:
                # 기존 행 업데이트
                row_num = existing.row
                sheet.update(f"A{row_num}:F{row_num}", [row_data])
                print(f"  🔄 기존 행 업데이트: {tool_name} (유형 {blog_type})")
            else:
                # 새 행 추가
                sheet.append_row(row_data, value_input_option="RAW")
                print(f"  ➕ 새 행 추가: {tool_name} (유형 {blog_type})")

            return True
        except Exception as e:
            print(f"  ❌ 블로그 저장 실패 ({tool_name}): {e}")
            return False

    # ──────────────────────────────────────
    # 업로드 대기 목록 조회
    # ──────────────────────────────────────

    def get_ready_to_upload(self) -> list[dict]:
        """
        블로그 콘텐츠 시트에서 업로드 상태 == "글완성" 항목 반환.
        반환: [{ name, title, content, row_index }, ...]
        """
        try:
            sheet = self._get_or_create_blog_sheet()
            rows = sheet.get_all_values()
        except Exception as e:
            print(f"❌ 블로그 콘텐츠 시트 읽기 실패: {e}")
            return []

        results = []
        for i, row in enumerate(rows[1:], start=2):  # 헤더 스킵
            while len(row) < 6:
                row.append("")
            if row[BLOG_COL_STATUS].strip() == "글완성":
                results.append({
                    "name":      row[BLOG_COL_NAME].strip(),
                    "title":     row[BLOG_COL_TITLE].strip(),
                    "content":   row[BLOG_COL_CONTENT].strip(),
                    "blog_type": row[BLOG_COL_TYPE].strip() or "B",
                    "row_index": i,
                })

        print(f"🚀 업로드 대기 글: {len(results)}개")
        return results

    def update_upload_status(self, tool_name: str, status: str) -> bool:
        """블로그 콘텐츠 시트의 업로드 상태 업데이트."""
        try:
            sheet = self.spreadsheet.worksheet("블로그 콘텐츠")
            cell = sheet.find(tool_name, in_column=BLOG_COL_NAME + 1)
            if cell:
                sheet.update_cell(cell.row, BLOG_COL_STATUS + 1, status)
                return True
        except Exception as e:
            print(f"  ❌ 업로드 상태 업데이트 실패: {e}")
        return False


# ──────────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("sheets_client.py — 연결 테스트")
    print("=" * 50)

    try:
        client = SheetsClient()

        print("\n📋 블로그 생성 대상 툴 목록:")
        tools = client.get_target_tools()
        for t in tools:
            print(f"  [{t['row_index']:2d}] {t['name']:<20} | {t['ai_category']:<25} | {t['price']}")

        print(f"\n✅ 테스트 완료 — 총 {len(tools)}개 대상 툴 확인")

    except FileNotFoundError as e:
        print(f"\n❌ 인증 파일 없음:\n{e}")
        print("\n📌 해결 방법:")
        print("  1. https://console.cloud.google.com 접속")
        print("  2. APIs & Services → Credentials → 서비스 계정 생성")
        print("  3. JSON 키 다운로드 → apps/scripts/credentials.json 저장")
        print("  4. 스프레드시트를 서비스 계정 이메일에 '편집자'로 공유")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
