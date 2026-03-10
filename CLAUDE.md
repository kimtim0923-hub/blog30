# AI있다 TAAFT Tracker — CLAUDE.md
> 이 파일을 읽으면 어느 세션에서든 작업을 이어받을 수 있습니다.

## 프로젝트 위치
```
/Users/sorakim/Desktop/ai blog30/ai-itda-tracker/
```

## 프로젝트 목적
TAAFT(There's An AI For That) 주간 인기 툴을 수동으로 복붙 →
Google Sheets 업데이트 → Claude API로 블로그 초안 생성 →
티스토리 자동 업로드하는 반자동 파이프라인

## 스프레드시트 정보
- **ID:** `1WXJ-6pbTv8Dg-fYhNyvKK98wo8VWonxo8TZPk6I-H1A`
- **URL:** https://docs.google.com/spreadsheets/d/1WXJ-6pbTv8Dg-fYhNyvKK98wo8VWonxo8TZPk6I-H1A
- **시트 이름 (이모지 포함!):**
  - `📦 툴 DB`: A툴이름/B태그라인/C타프트카테고리/D AI있다카테고리/E가격/F출시/G저장수/H타겟?/I블로그작성상태/J첫수집일
  - `블로그 콘텐츠`: A툴이름/B제목/C내용/D생성일시/E업로드상태/F글유형 (scripts가 자동 생성)
  - `📅 주간 로그`: 수집일/순위/툴이름/Tagline/TAAFT카테고리/AI있다카테고리/가격/저장수/타겟?/신규중복/블로그생성
- **서비스 계정:** `blog30sheet@project-0977d009-7cf5-4649-959.iam.gserviceaccount.com`

## 파일 역할 요약
```
apps/scripts/
  .env                 ← 환경변수 (API 키 등) — Git 제외
  credentials.json     ← Google 서비스 계정 키 — Git 제외
  requirements.txt     ← Python 패키지 목록 (gspread, anthropic, selenium, markdown)
  sheets_client.py     ← Google Sheets 읽기/쓰기 공통 모듈
  blog_generator.py    ← Claude API로 블로그 생성 + Sheets 저장 (B/C/D/E 4가지 유형 랜덤 선택)
  tistory_uploader.py  ← Selenium으로 티스토리 자동 업로드 (마크다운→HTML 변환 포함)

apps/webapp/
  index.html           ← 복붙 UI 진입점
  css/                 ← 스타일 (base, layout, components)
  js/config.js         ← API 키 보관 — Git 제외
  js/parser.js         ← TAAFT 데이터 파서 (TSV/번호/대시 3형식)
  js/sheets.js         ← Google Sheets API v4 브라우저 클라이언트
  js/ui.js             ← UI 인터랙션
  js/main.js           ← 모듈 조합 + 이벤트 바인딩

docs/
  workflow.md          ← 전체 워크플로우 설명
  sheets_schema.md     ← 스프레드시트 컬럼 명세

gas/tracker.gs         ← Google Apps Script 백업 (빈 파일)
```

## 진행 현황 체크리스트

### Phase 1 — Python 파이프라인
- [x] STEP 0: 폴더 뼈대 + CLAUDE.md + .env 파일 생성
- [x] STEP 7: requirements.txt + sheets_client.py
- [x] STEP 8: blog_generator.py (B/C/D/E 4가지 유형 랜덤 선택)
- [x] STEP 9: tistory_uploader.py

> ✅ **Phase 1 완료** (2026-03-10)

### Phase 2 — 웹앱 UI
- [x] STEP 2: parser.js
- [x] STEP 3: CSS 3파일 (base, layout, components)
- [x] STEP 4: ui.js
- [x] STEP 5: sheets.js
- [x] STEP 6: main.js + index.html + config.js
- [x] 문서: docs/workflow.md + docs/sheets_schema.md 작성
- [x] QA: parser.js 유닛 테스트 4건 PASS, Python↔JS 컬럼 매핑 검증

> ✅ **Phase 2 완료** (2026-03-11)

### Phase 3 — 통합 테스트 + 수정 (진행 중)
- [x] 환경변수 설정 (.env에 모든 키 입력 완료)
- [x] credentials.json 배치 + 서비스 계정 스프레드시트 공유
- [x] sheets_client.py 연결 테스트 성공 (14개 타겟 툴 확인)
- [x] blog_generator.py 테스트 (Idea2Clip, 유형 D, 4707자 생성 성공)
- [x] tistory_uploader.py 로그인 성공
- [x] tistory_uploader.py 카테고리 "생산성툴" 설정 성공
- [x] 마크다운 → HTML 변환 (markdown 라이브러리) 적용
- [ ] **tistory_uploader.py 비공개 글 저장 방식으로 변경 필요**
  - 현재: "공개 발행" 클릭 → 즉시 공개됨
  - 변경: "비공개" 선택 후 발행 → 비공개로 저장
  - 발행 모달 구조: 기본(공개/공개보호/비공개) + 발행일 + 공개발행 버튼
- [ ] 나머지 13개 툴 블로그 생성 (blog_generator.py)
- [ ] 전체 배치 업로드 테스트

### 티스토리 에디터 참고 (새 에디터, 2026년 기준)
- **글쓰기 URL:** `https://buu2.tistory.com/manage/newpost`
- **제목:** placeholder "제목을 입력하세요" (XPath로 찾기)
- **본문:** TinyMCE iframe 에디터 (POWERED BY TINY)
- **카카오 로그인:** XPath `//\*[contains(text(), '카카오')]` 로 버튼 찾기
- **발행 모달:** "완료" 버튼 클릭 시 모달 표시
  - 기본: 공개 ✅ / 공개(보호) / 비공개
  - 발행일: YYYY-MM-DD | HH : MM | 현재 | 예약
  - 하단: 취소 / 공개 발행 버튼
- **임시저장 알림:** `driver.switch_to.alert.dismiss()` 로 처리

## 전체 실행 명령어
```bash
cd /Users/sorakim/Desktop/ai\ blog30/ai-itda-tracker/apps/scripts

# 1. 패키지 설치
pip3 install -r requirements.txt

# 2. Sheets 연결 테스트
python3 sheets_client.py

# 3. 블로그 자동 생성 (타겟 ✅ 툴)
python3 blog_generator.py

# 4. 티스토리 자동 업로드
python3 tistory_uploader.py
```

## 터미널 1 이어서 할 작업
```
CLAUDE.md 읽고, tistory_uploader.py를 수정해줘:
1. 발행 모달에서 "비공개" 라디오 선택 후 발행 (예약 로직 제거)
2. 예약 관련 코드(schedule_date, schedule_time) 전부 제거
3. Idea2Clip 상태 리셋 후 테스트: python3 -c "from sheets_client import SheetsClient; s=SheetsClient(); s.update_upload_status('Idea2Clip','글완성'); s.update_blog_status('Idea2Clip','글완성')"
4. python3 tistory_uploader.py 실행하여 비공개 저장 확인
5. 성공 시 나머지 13개 blog_generator.py 실행
```

## 환경변수 목록
| 변수명 | 용도 |
|--------|------|
| `GOOGLE_CREDENTIALS_JSON` | 서비스 계정 JSON 경로 |
| `SPREADSHEET_ID` | Google Sheets 문서 ID |
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `GOOGLE_API_KEY` | Google API 키 (웹앱용) |
| `GOOGLE_CLIENT_ID` | OAuth2 클라이언트 ID (웹앱용) |
| `TISTORY_ID` | 카카오 로그인 이메일 |
| `TISTORY_PW` | 카카오 로그인 비밀번호 |
| `TISTORY_BLOG_NAME` | 티스토리 블로그 주소 (buu2.tistory.com) |
