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
- **시트 구조:**
  - `툴 DB`: A툴이름/B태그라인/C타프트카테고리/D AI있다카테고리/E가격/F출시/G저장수/H타겟?/I블로그작성상태/J첫수집일
  - `블로그 콘텐츠`: A툴이름/B제목/C내용/D생성일시/E업로드상태/F글유형 (scripts가 자동 생성)
  - `주간 로그`: 수집일/순위/툴이름/Tagline/TAAFT카테고리/AI있다카테고리/가격/저장수/타겟?/신규중복/블로그생성

## 파일 역할 요약
```
apps/scripts/
  .env                 ← 환경변수 (API 키 등) — Git 제외
  credentials.json     ← Google 서비스 계정 키 — Git 제외 (사용자가 준비)
  requirements.txt     ← Python 패키지 목록
  sheets_client.py     ← Google Sheets 읽기/쓰기 공통 모듈
  blog_generator.py    ← Claude API로 블로그 생성 + Sheets 저장 (B/C/D/E 4가지 유형 랜덤 선택)
  tistory_uploader.py  ← Selenium으로 티스토리 자동 업로드

apps/webapp/           ← Phase 2 (나중에)
  index.html           ← 복붙 UI 진입점
  css/                 ← 스타일 (base, layout, components)
  js/                  ← 파서, Sheets API, UI, 메인

docs/
  workflow.md          ← 전체 워크플로우 설명
  sheets_schema.md     ← 스프레드시트 컬럼 명세

gas/tracker.gs         ← Google Apps Script 백업
```

## 진행 현황 체크리스트

### Phase 1 — Python 파이프라인 (우선)
- [x] STEP 0: 폴더 뼈대 + CLAUDE.md + .env 파일 생성
- [x] STEP 7: requirements.txt + sheets_client.py
- [x] STEP 8: blog_generator.py (6가지 유형 → B/C/D/E 랜덤 선택, 유형 스프레드시트 기록)
- [x] STEP 9: tistory_uploader.py

> ✅ **Phase 1 완료** (2026-03-10) — Python 파이프라인 전체 구현 완료
> 사용자 준비 사항(credentials.json + .env 입력) 후 바로 실행 가능

### Phase 2 — 웹앱 UI (나중)
- [ ] STEP 2: parser.js
- [ ] STEP 3: CSS 3파일 (base, layout, components)
- [ ] STEP 4: ui.js
- [ ] STEP 5: sheets.js
- [ ] STEP 6: main.js + index.html

## 사용자 준비 사항 (스크립트 실행 전)
- [ ] Google Cloud Console 서비스 계정 생성
  1. https://console.cloud.google.com → 새 프로젝트 생성
  2. APIs & Services → Library → "Google Sheets API" 활성화
  3. Credentials → "서비스 계정" 생성 → JSON 키 다운로드
  4. `credentials.json`을 `apps/scripts/` 폴더에 저장
- [ ] 스프레드시트에 서비스 계정 이메일을 **"편집자"로 공유**
- [ ] `apps/scripts/.env` 파일에 값 입력:
  - `ANTHROPIC_API_KEY=sk-ant-...`
  - `TISTORY_ID=카카오이메일`
  - `TISTORY_PW=카카오비밀번호`
  - `TISTORY_BLOG_NAME=블로그명.tistory.com`

## 전체 실행 명령어 (준비 완료 후)
```bash
cd /Users/sorakim/Desktop/ai\ blog30/ai-itda-tracker/apps/scripts

# 1. 패키지 설치
pip install -r requirements.txt

# 2. Sheets 연결 테스트
python sheets_client.py

# 3. 블로그 자동 생성 (타겟 ✅ 툴 ~10개)
python blog_generator.py

# 4. 티스토리 자동 업로드
python tistory_uploader.py
```

## 다음 세션 시작법
```
"CLAUDE.md 읽고 남은 STEP 이어서 진행해줘"
```

## 환경변수 목록
| 변수명 | 용도 |
|--------|------|
| `GOOGLE_CREDENTIALS_JSON` | 서비스 계정 JSON 경로 (Python 쓰기용) |
| `SPREADSHEET_ID` | Google Sheets 문서 ID (이미 입력됨) |
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `TISTORY_ID` | 카카오 로그인 이메일 |
| `TISTORY_PW` | 카카오 로그인 비밀번호 |
| `TISTORY_BLOG_NAME` | 티스토리 블로그 주소 |
