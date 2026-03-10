# AI있다 TAAFT Tracker — 전체 워크플로우

## 개요

TAAFT(There's An AI For That) 주간 인기 AI 툴 데이터를 수집하고,
Claude API로 SEO 최적화 블로그 글을 자동 생성한 뒤,
티스토리에 자동 업로드하는 반자동 파이프라인이다.

---

## Phase 1 — Python 파이프라인 (현재 구현 완료)

### 전체 흐름

```
TAAFT 사이트 방문
      │
      ▼
수동으로 주간 인기 툴 복사
      │
      ▼
Google Sheets '툴 DB' 시트에 붙여넣기
(A툴이름 ~ J첫수집일, H열 '타겟?' 표시)
      │
      ▼
blog_generator.py 실행
  - sheets_client.py로 '툴 DB'에서 타겟 ✅ + 미작성 툴 조회
  - 같은 카테고리 동료 수에 따라 글 유형 가중 랜덤 선택
    B(리뷰 40%) / C(비교 20%) / D(대안 20%) / E(순위 20%)
  - Claude API (claude-opus-4-5) 호출로 블로그 초안 생성
  - '블로그 콘텐츠' 시트에 제목/본문/유형 저장
  - '툴 DB' I열 상태를 '글완성'으로 업데이트
      │
      ▼
tistory_uploader.py 실행
  - sheets_client.py로 '블로그 콘텐츠'에서 '글완성' 항목 조회
  - Selenium + Chrome WebDriver로 티스토리 접속
  - 카카오 계정 자동 로그인
  - 제목/본문 입력 후 발행
  - 시트 상태를 '업로드완료'로 업데이트
```

### 블로그 글 유형 (4가지)

| 유형 | 이름 | 기본 가중치 | 필요 동료 수 | 목표 글자수 |
|------|------|------------|------------|------------|
| B | 단일 툴 심층 리뷰 | 40% | 없음 | 2,500~3,000자 |
| C | 두 툴 비교 | 20% | 1개 이상 | 2,000~2,500자 |
| D | 대안 툴 소개 | 20% | 2개 이상 | 2,500~3,000자 |
| E | 카테고리 TOP N 순위 | 20% | 3개 이상 | 3,000~3,500자 |

동료(같은 `ai_category`의 다른 툴)가 부족하면 해당 가중치는 B(리뷰)로 귀속된다.

### 상태 흐름

```
미작성 → 생성중 → 글완성 → 업로드완료
                 ↘ 생성오류
                         ↘ 업로드오류
```

### 실행 순서 및 명령어

```bash
cd /Users/sorakim/Desktop/ai\ blog30/ai-itda-tracker/apps/scripts

# 1. 패키지 설치 (최초 1회)
pip install -r requirements.txt

# 2. Google Sheets 연결 테스트
python sheets_client.py

# 3. 블로그 자동 생성 (타겟 ✅ + 미작성 툴 대상)
python blog_generator.py

# 4. 티스토리 자동 업로드 (브라우저 표시)
python tistory_uploader.py

# 4-1. 브라우저 숨김 모드
python tistory_uploader.py --headless
```

### 사전 준비 사항

1. Google Cloud Console에서 서비스 계정 생성 및 JSON 키 다운로드
2. `credentials.json`을 `apps/scripts/` 폴더에 저장
3. 스프레드시트를 서비스 계정 이메일에 **편집자**로 공유
4. `apps/scripts/.env` 파일에 API 키 및 계정 정보 입력

---

## Phase 2 — 웹앱 UI (예정)

### 전체 흐름

```
TAAFT 사이트에서 인기 툴 텍스트 복사
      │
      ▼
웹앱(index.html) 붙여넣기 영역에 텍스트 입력
      │
      ▼
parser.js가 텍스트를 파싱
  - 툴이름, 태그라인, 카테고리, 가격, 저장수 등 추출
      │
      ▼
ui.js가 파싱 결과를 테이블로 표시
  - 사용자가 타겟 여부 체크, 카테고리 수정 가능
      │
      ▼
sheets.js가 Google Sheets API로 스프레드시트에 저장
  - '툴 DB' 시트에 새 행 추가 또는 기존 행 업데이트
  - '주간 로그' 시트에 수집 기록 추가
```

### 파일 구성 (예정)

```
apps/webapp/
  index.html         ← 메인 진입점
  css/
    base.css         ← 기본 스타일 (타이포그래피, 리셋)
    layout.css       ← 레이아웃 (그리드, 컨테이너)
    components.css   ← 컴포넌트 (버튼, 테이블, 카드)
  js/
    parser.js        ← TAAFT 텍스트 파서
    sheets.js        ← Google Sheets API 연동
    ui.js            ← DOM 조작 및 이벤트 핸들링
    main.js          ← 앱 초기화 및 모듈 연결
```

---

## 핵심 의존 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| gspread | >= 5.12.0 | Google Sheets 읽기/쓰기 |
| google-auth | >= 2.23.0 | Google 서비스 계정 인증 |
| anthropic | >= 0.25.0 | Claude API 호출 |
| selenium | >= 4.15.0 | 브라우저 자동화 |
| webdriver-manager | >= 4.0.1 | ChromeDriver 자동 설치 |
| python-dotenv | >= 1.0.0 | .env 파일 로드 |
