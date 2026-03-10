# AI있다 TAAFT Tracker

TAAFT(There's An AI For That) 주간 인기 툴 수집 → Google Sheets 업데이트 → Claude API 블로그 생성 → 티스토리 자동 업로드 파이프라인

## 빠른 시작

### 1. 환경 설정
```bash
cd apps/scripts
cp ../../.env.example .env
# .env 파일 열어서 API 키 입력
pip install -r requirements.txt
```

### 2. Sheets 연결 테스트
```bash
python sheets_client.py
```

### 3. 블로그 자동 생성
```bash
python blog_generator.py
```

### 4. 티스토리 자동 업로드
```bash
python tistory_uploader.py
```

## 프로젝트 구조
```
ai-itda-tracker/
├── apps/
│   ├── scripts/         ← Python 자동화 (메인)
│   │   ├── sheets_client.py     Google Sheets 연동
│   │   ├── blog_generator.py    Claude API 블로그 생성
│   │   └── tistory_uploader.py  Selenium 티스토리 업로드
│   └── webapp/          ← 브라우저 웹앱 (Phase 2)
├── docs/                ← 문서
└── gas/                 ← Google Apps Script 백업
```

## 스프레드시트 구조
- **툴 DB**: 누적 툴 데이터베이스 (블로그 작성 상태 관리)
- **블로그 콘텐츠**: 생성된 블로그 글 저장 (자동 생성됨)
- **주간 로그**: 주차별 수집 기록
