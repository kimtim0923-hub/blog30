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
- [x] tistory_uploader.py 비공개 발행 + 예약/공개 파라미터 추가
- [ ] 나머지 13개 툴 블로그 생성 (blog_generator.py)
- [ ] 전체 배치 업로드 테스트

### Phase 4 — FastAPI 백엔드 서버
- [x] api_server.py 생성 (FastAPI + CORS)
- [x] Sheets 엔드포인트 (/api/tools, /api/blog/list 등)
- [x] 블로그 생성 엔드포인트 (단일 + 배치)
- [x] 티스토리 업로드 엔드포인트 (비공개/공개/예약 지원)
- [x] tistory_uploader.py에 visibility + schedule 파라미터 추가
- [x] CORS 설정 (localhost:3000/5500/8080 + file://)
- [x] 로컬 테스트 통과 (전체 엔드포인트 200 OK)
- [ ] 프론트엔드 통합 테스트

> ✅ **Phase 4 백엔드 완료** (2026-03-11)

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

## 터미널 1 — 백엔드 (Phase 4-BE)
> 담당: Python API 서버 + 백엔드 로직 (apps/scripts/)
> 터미널 2(프론트)가 호출할 API 엔드포인트를 만드는 역할

### 담당 파일
- `apps/scripts/api_server.py` ← **신규** FastAPI 서버
- `apps/scripts/blog_generator.py` ← API로 래핑
- `apps/scripts/tistory_uploader.py` ← API로 래핑 (예약 시간 파라미터 추가)
- `apps/scripts/sheets_client.py` ← 기존 유지

### 할 일 (순서대로)
1. **FastAPI 서버 구축** (`api_server.py`)
   - `pip install fastapi uvicorn` 추가
   - CORS 허용 (localhost 웹앱에서 호출)
2. **API 엔드포인트 구현**
   - `GET /api/tools` — 타겟 툴 목록 조회 (sheets_client.get_target_tools)
   - `GET /api/blog/ready` — 업로드 대기 글 목록 (sheets_client.get_ready_to_upload)
   - `POST /api/blog/generate` — 블로그 생성 트리거 (tool_name, blog_type)
   - `POST /api/tistory/upload` — 티스토리 업로드 (tool_name, visibility, schedule_datetime)
3. **tistory_uploader.py 예약 기능 복원**
   - UI에서 받은 schedule_datetime으로 예약 발행
   - visibility: "공개" | "비공개" 선택 가능
4. **서버 실행 및 테스트**
   - `uvicorn api_server:app --reload --port 8000`

### 터미널 1에서 시작할 명령
```
CLAUDE.md 읽고, Phase 4 백엔드를 진행해줘:
1. apps/scripts/에 FastAPI 서버(api_server.py) 생성
2. sheets_client, blog_generator, tistory_uploader를 API 엔드포인트로 래핑
3. tistory_uploader.py에 예약 시간 + 공개/비공개 파라미터 추가
4. CORS 설정 후 로컬 테스트
5. 터미널 2(프론트)가 fetch()로 호출할 수 있도록 엔드포인트 문서화
```

---

## 터미널 2 — 프론트엔드 (Phase 4-FE)
> 담당: 웹앱 UI 대시보드 (apps/webapp/)
> 터미널 1(백엔드)이 만든 API를 호출하는 역할

### 담당 파일
- `apps/webapp/index.html` ← UI 레이아웃 확장
- `apps/webapp/js/ui.js` ← UI 인터랙션 확장
- `apps/webapp/js/main.js` ← 이벤트 바인딩 확장
- `apps/webapp/js/api.js` ← **신규** 백엔드 API 호출 모듈
- `apps/webapp/css/` ← 스타일 확장

### 할 일 (순서대로)
1. **대시보드 레이아웃 설계** (탭 or 섹션 구조)
   - 탭1: 데이터 입력 + 파싱 (기존)
   - 탭2: 시트 연동 (파싱 결과 → 시트 자동 입력)
   - 탭3: 블로그 생성 (타겟 툴 목록 + 생성 버튼 + 미리보기) — **미작성 + 글완성(미업로드) 모두 표시**
   - 탭4: 이미지 삽입 (생성된 글의 [이미지: 설명] 태그를 파싱 → 드롭존 표시 → 사용자가 이미지 드래그앤드롭)
   - 탭5: 티스토리 업로드 (글 목록 + 예약시간 입력 + 업로드)
2. **api.js 작성** — 백엔드 API 호출 래퍼
   - `API_BASE = 'http://localhost:8000'`
   - `fetchTools()`, `generateBlog()`, `uploadToTistory()` 등
3. **각 탭 UI 구현**
   - 탭1: 기존 유지
   - 탭2: Sheets 연동 버튼 + 결과 표시
   - 탭3: 툴 목록 (미작성 + 글완성 모두 표시, 상태 뱃지로 구분) + 유형 드롭다운 + 생성 버튼 + 진행률 + 미리보기
   - 탭4: 이미지 삽입 UI (아래 상세 참조)
   - 탭5: **글 선택 드롭다운/체크박스** (이미지 적용 완료된 글 목록) + 날짜/시간 picker + 공개/비공개 라디오 + 업로드 버튼
4. **탭4 이미지 삽입 — 상세 흐름**
   - 블로그 생성 완료 후 → 글 내용에서 `[이미지: 설명]` 태그를 자동 파싱
   - 각 태그마다 드롭존(dropzone) UI 생성: "설명" 텍스트 + 파일 드래그앤드롭 영역
   - 사용자가 캡처/로컬 이미지를 각 드롭존에 드래그앤드롭
   - 이미지 미리보기 표시 + 순서 확인
   - "이미지 적용" 버튼 → `[이미지: 설명]` 태그를 실제 `<img>` 태그로 교체
   - 이미지 파일은 Base64 인코딩 또는 백엔드 `/api/upload/image` 엔드포인트로 업로드
   - 최종 결과: 이미지 포함된 HTML 블로그 글 완성 → 티스토리 업로드 준비
5. **백엔드 API 연동 테스트**

### 터미널 2에서 시작할 명령
```
CLAUDE.md 읽고, Phase 4 프론트엔드를 진행해줘:
1. apps/webapp/ 기존 코드 읽고 구조 파악
2. 탭 기반 대시보드로 index.html 확장 (5개 탭)
3. api.js 신규 작성 (백엔드 http://localhost:8000 호출)
4. 탭1(데이터 입력)은 기존 유지, 탭2~5 순차 구현
5. 백엔드 API가 아직 없으면 목업 데이터로 UI 먼저 완성
```

---

### Phase 4 API 인터페이스 (터미널 1↔2 공유 규약)
```
GET  /api/tools              → [{ name, tagline, category, price, blog_status, ... }]
                               ⚠️ 미작성 + 글완성(미업로드) 모두 반환 (blog_status로 구분)
GET  /api/blog/ready         → [{ name, title, content, blog_type, has_images, ... }]
                               ⚠️ 이미지 적용 완료 여부(has_images) 포함
POST /api/blog/generate      → { tool_name, blog_type? }  → { title, content }
POST /api/tistory/upload     → { tool_name, visibility, schedule_datetime? } → { success, message }
POST /api/upload/image       → multipart/form-data (file) → { url, filename }
POST /api/blog/apply-images  → { tool_name, images: [{ tag, image_url }] } → 글 내용의 [이미지:] 태그를 <img>로 교체 후 저장
```

## 미해결 이슈
- [ ] **웹앱 Google Sheets API 403 오류**: API 키(`AIzaSyB2d...`)로 Discovery 문서 로드 시 403 Forbidden
  - 원인: Google Cloud Console에서 Google Sheets API 미활성화 또는 API 키 제한 설정
  - 해결: Console → APIs & Services → Google Sheets API Enable + API 키 제한 해제

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
