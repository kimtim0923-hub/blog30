"""
api_server.py — FastAPI 백엔드 서버
역할: sheets_client, blog_generator, tistory_uploader를
      REST API 엔드포인트로 래핑하여 프론트엔드(webapp)에서 호출 가능하게 한다.

실행: uvicorn api_server:app --reload --port 8000
"""

import os
import threading
from pathlib import Path
from typing import Optional

import re
import uuid
import base64

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# .env 로드
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".env")

from sheets_client import SheetsClient
from blog_generator import (
    select_blog_type, generate_blog, _is_new_tool
)

# ──────────────────────────────────────────────────────
# FastAPI 앱 초기화
# ──────────────────────────────────────────────────────

app = FastAPI(
    title="AI있다 TAAFT Tracker API",
    description="Google Sheets + Claude 블로그 생성 + 티스토리 업로드 API",
    version="1.0.0",
)

# CORS — Lovable 프론트엔드 + 로컬 개발용
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "null",  # file:// 프로토콜
]

# 환경변수로 추가 origin 허용 (Railway 배포 시 Lovable URL 설정)
_extra_origin = os.environ.get("FRONTEND_URL", "")
if _extra_origin:
    _ALLOWED_ORIGINS.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.lovable\.app",  # Lovable 서브도메인 전체 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 이미지 업로드 디렉토리 (Vercel은 /tmp만 쓰기 가능)
_UPLOADS_DIR = Path("/tmp/uploads/images") if os.environ.get("VERCEL") else _SCRIPT_DIR.parent.parent / "uploads" / "images"
try:
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    _UPLOADS_DIR = Path("/tmp/uploads/images")
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# 정적 파일 서빙 (업로드된 이미지)
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR.parent)), name="uploads")

# Selenium 드라이버 — 전역 (로그인 세션 유지)
_driver = None
_driver_lock = threading.Lock()


def _get_sheets() -> SheetsClient:
    """SheetsClient 인스턴스 생성 (요청마다)."""
    return SheetsClient()


# ──────────────────────────────────────────────────────
# Pydantic 모델
# ──────────────────────────────────────────────────────

class BlogGenerateRequest(BaseModel):
    tool_name: str
    blog_type: Optional[str] = None  # None이면 자동 선택

class BlogGenerateBatchRequest(BaseModel):
    tool_names: list[str]  # 빈 리스트면 전체 타겟 툴
    limit: Optional[int] = None

class UploadRequest(BaseModel):
    tool_name: str
    visibility: str = "private"      # "public" | "private"
    schedule_date: str = ""          # "YYYY-MM-DD" or ""
    schedule_time: str = "09:00"     # "HH:MM"

class UploadBatchRequest(BaseModel):
    tool_names: list[str]  # 빈 리스트면 글완성 전체
    visibility: str = "private"
    schedule_date: str = ""
    schedule_time: str = "09:00"

class ImageMapping(BaseModel):
    tag: str           # "[이미지: 기능 화면]" 원본 태그
    image_url: str     # 업로드된 이미지 URL or base64 data URI

class ApplyImagesRequest(BaseModel):
    tool_name: str
    images: list[ImageMapping]


# ──────────────────────────────────────────────────────
# 1. Sheets 엔드포인트
# ──────────────────────────────────────────────────────

@app.get("/api/tools")
def get_all_tools(filter: str = "target"):
    """
    툴 DB 조회.
    filter=target (기본): 타겟 ✅ 중 미작성 + 글완성(미업로드) 툴만 반환
    filter=all: 전체 반환
    """
    sheets = _get_sheets()
    sheet = sheets.spreadsheet.worksheet("📦 툴 DB")
    rows = sheet.get_all_values()
    if len(rows) <= 1:
        return {"tools": [], "total": 0}

    tools = []
    for i, row in enumerate(rows[1:], start=2):
        while len(row) < 10:
            row.append("")
        tool = {
            "row_index": i,
            "name": row[0].strip(),
            "tagline": row[1].strip(),
            "taaft_category": row[2].strip(),
            "ai_category": row[3].strip(),
            "price": row[4].strip(),
            "released": row[5].strip(),
            "saves": row[6].strip(),
            "target": row[7].strip(),
            "blog_status": row[8].strip() or "미작성",
            "first_date": row[9].strip(),
            "is_new": _is_new_tool(row[5].strip()),
        }

        if filter == "all":
            tools.append(tool)
        else:
            # 타겟 ✅ 이면서 미작성 또는 글완성(아직 업로드 안 된) 툴
            is_target = tool["target"] == "✅" or "타겟" in tool["target"]
            if is_target and tool["blog_status"] in ("미작성", "글완성"):
                tools.append(tool)

    return {"tools": tools, "total": len(tools)}


@app.get("/api/tools/target")
def get_target_tools():
    """타겟 ✅ + 블로그 미작성 툴 목록."""
    sheets = _get_sheets()
    tools = sheets.get_target_tools()
    return {"tools": tools, "total": len(tools)}


@app.get("/api/blog/list")
def get_blog_list():
    """블로그 콘텐츠 시트 전체 목록."""
    sheets = _get_sheets()
    try:
        sheet = sheets.spreadsheet.worksheet("블로그 콘텐츠")
        rows = sheet.get_all_values()
    except Exception:
        return {"articles": [], "total": 0}

    articles = []
    for i, row in enumerate(rows[1:], start=2):
        while len(row) < 6:
            row.append("")
        articles.append({
            "row_index": i,
            "name": row[0].strip(),
            "title": row[1].strip(),
            "content_length": len(row[2]),
            "content_preview": row[2][:200].strip(),
            "created": row[3].strip(),
            "status": row[4].strip(),
            "blog_type": row[5].strip(),
        })
    return {"articles": articles, "total": len(articles)}


@app.get("/api/blog/content/{tool_name}")
def get_blog_content(tool_name: str):
    """특정 툴의 블로그 본문 전체 반환."""
    sheets = _get_sheets()
    try:
        sheet = sheets.spreadsheet.worksheet("블로그 콘텐츠")
        cell = sheet.find(tool_name, in_column=1)
        if not cell:
            raise HTTPException(status_code=404, detail=f"'{tool_name}' 블로그 없음")
        row = sheet.row_values(cell.row)
        while len(row) < 6:
            row.append("")
        return {
            "name": row[0].strip(),
            "title": row[1].strip(),
            "content": row[2].strip(),
            "created": row[3].strip(),
            "status": row[4].strip(),
            "blog_type": row[5].strip(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/blog/ready")
def get_ready_to_upload():
    """업로드 대기(글완성) 글 목록. has_images 필드 포함."""
    sheets = _get_sheets()
    articles = sheets.get_ready_to_upload()

    # 각 글에 has_images 필드 추가 (내용에 [이미지:] 태그가 남아있으면 false)
    image_tag_pattern = re.compile(r'\[이미지:\s*[^\]]+\]')
    for article in articles:
        content = article.get("content", "")
        article["has_images"] = not bool(image_tag_pattern.search(content))

    return {"articles": articles, "total": len(articles)}


# ──────────────────────────────────────────────────────
# 2. 블로그 생성 엔드포인트
# ──────────────────────────────────────────────────────

@app.post("/api/blog/generate")
def generate_single_blog(req: BlogGenerateRequest):
    """단일 툴 블로그 생성 (동기)."""
    sheets = _get_sheets()
    all_tools = sheets.get_target_tools()

    # 전체 툴 DB에서 찾기 (미작성 아니어도 생성 가능)
    tool = None
    sheet_db = sheets.spreadsheet.worksheet("📦 툴 DB")
    rows = sheet_db.get_all_values()
    for i, row in enumerate(rows[1:], start=2):
        while len(row) < 10:
            row.append("")
        if row[0].strip() == req.tool_name:
            tool = {
                "name": row[0].strip(),
                "tagline": row[1].strip(),
                "taaft_category": row[2].strip(),
                "ai_category": row[3].strip(),
                "price": row[4].strip(),
                "released": row[5].strip(),
                "saves": row[6].strip(),
                "row_index": i,
            }
            break

    if not tool:
        raise HTTPException(status_code=404, detail=f"툴 '{req.tool_name}'을 찾을 수 없음")

    # 유형 선택
    blog_type = req.blog_type or select_blog_type(tool, all_tools)

    # 상태 업데이트
    sheets.update_blog_status(req.tool_name, "생성중")

    try:
        title, content = generate_blog(tool, blog_type, all_tools)
        sheets.save_blog_content(req.tool_name, title, content, blog_type)
        sheets.update_blog_status(req.tool_name, "글완성")
        return {
            "success": True,
            "tool_name": req.tool_name,
            "blog_type": blog_type,
            "title": title,
            "content_length": len(content),
            "content_preview": content[:300],
        }
    except Exception as e:
        sheets.update_blog_status(req.tool_name, "생성오류")
        raise HTTPException(status_code=500, detail=f"블로그 생성 실패: {e}")


# 백그라운드 작업 상태 추적
_batch_status: dict = {}


def _run_batch_generate(job_id: str, tool_names: list[str], limit: int | None):
    """백그라운드 배치 생성."""
    _batch_status[job_id] = {"status": "running", "done": 0, "total": 0, "errors": []}

    sheets = _get_sheets()
    all_tools = sheets.get_target_tools()

    if tool_names:
        targets = [t for t in all_tools if t["name"] in tool_names]
    else:
        targets = all_tools

    if limit:
        targets = targets[:limit]

    _batch_status[job_id]["total"] = len(targets)

    for i, tool in enumerate(targets):
        try:
            blog_type = select_blog_type(tool, all_tools)
            sheets.update_blog_status(tool["name"], "생성중")
            title, content = generate_blog(tool, blog_type, all_tools)
            sheets.save_blog_content(tool["name"], title, content, blog_type)
            sheets.update_blog_status(tool["name"], "글완성")
        except Exception as e:
            sheets.update_blog_status(tool["name"], "생성오류")
            _batch_status[job_id]["errors"].append({"name": tool["name"], "error": str(e)})

        _batch_status[job_id]["done"] = i + 1

    _batch_status[job_id]["status"] = "completed"


@app.post("/api/blog/generate/batch")
def generate_batch_blog(req: BlogGenerateBatchRequest, bg: BackgroundTasks):
    """배치 블로그 생성 (비동기 — 백그라운드)."""
    import uuid
    job_id = uuid.uuid4().hex[:8]
    bg.add_task(_run_batch_generate, job_id, req.tool_names, req.limit)
    return {"job_id": job_id, "message": "배치 생성 시작됨. /api/blog/generate/status/{job_id}로 진행 확인"}


@app.get("/api/blog/generate/status/{job_id}")
def get_batch_status(job_id: str):
    """배치 생성 진행 상태 조회."""
    if job_id not in _batch_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없음")
    return _batch_status[job_id]


# ──────────────────────────────────────────────────────
# 3. 티스토리 업로드 엔드포인트
# ──────────────────────────────────────────────────────

def _ensure_driver():
    """Selenium 드라이버 + 로그인 세션 확보."""
    global _driver
    with _driver_lock:
        if _driver is not None:
            try:
                _driver.current_url  # 살아있는지 확인
                return _driver
            except Exception:
                _driver = None

        from tistory_uploader import setup_driver, login

        blog_name = os.environ.get("TISTORY_BLOG_NAME", "")
        tistory_id = os.environ.get("TISTORY_ID", "")
        tistory_pw = os.environ.get("TISTORY_PW", "")

        if not all([blog_name, tistory_id, tistory_pw]):
            raise HTTPException(status_code=500, detail="티스토리 환경변수 미설정")

        _driver = setup_driver(headless=True)
        logged_in = login(_driver, blog_name, tistory_id, tistory_pw)
        if not logged_in:
            _driver.quit()
            _driver = None
            raise HTTPException(status_code=500, detail="티스토리 로그인 실패")

        return _driver


@app.post("/api/upload")
def upload_single(req: UploadRequest):
    """단일 글 티스토리 업로드."""
    from tistory_uploader import post_article

    sheets = _get_sheets()
    blog_name = os.environ.get("TISTORY_BLOG_NAME", "")

    # 블로그 콘텐츠에서 글 가져오기
    try:
        sheet = sheets.spreadsheet.worksheet("블로그 콘텐츠")
        cell = sheet.find(req.tool_name, in_column=1)
        if not cell:
            raise HTTPException(status_code=404, detail=f"'{req.tool_name}' 블로그 없음")
        row = sheet.row_values(cell.row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    title = row[1].strip() if len(row) > 1 else ""
    content = row[2].strip() if len(row) > 2 else ""

    if not content:
        raise HTTPException(status_code=400, detail="블로그 내용이 비어있음")

    driver = _ensure_driver()

    success = post_article(
        driver, blog_name, title, content,
        visibility=req.visibility,
        schedule_date=req.schedule_date,
        schedule_time=req.schedule_time,
    )

    if success:
        status = "업로드완료"
        sheets.update_upload_status(req.tool_name, status)
        sheets.update_blog_status(req.tool_name, status)
        mode = f"예약({req.schedule_date})" if req.schedule_date else req.visibility
        return {"success": True, "tool_name": req.tool_name, "mode": mode}
    else:
        sheets.update_upload_status(req.tool_name, "업로드오류")
        raise HTTPException(status_code=500, detail="업로드 실패")


@app.post("/api/upload/batch")
def upload_batch(req: UploadBatchRequest, bg: BackgroundTasks):
    """배치 업로드 (비동기)."""
    import uuid
    job_id = uuid.uuid4().hex[:8]

    def _run():
        from tistory_uploader import post_article

        _batch_status[job_id] = {"status": "running", "done": 0, "total": 0, "errors": []}
        sheets = _get_sheets()
        blog_name = os.environ.get("TISTORY_BLOG_NAME", "")

        if req.tool_names:
            articles = [a for a in sheets.get_ready_to_upload() if a["name"] in req.tool_names]
        else:
            articles = sheets.get_ready_to_upload()

        _batch_status[job_id]["total"] = len(articles)
        driver = _ensure_driver()

        for i, article in enumerate(articles):
            try:
                success = post_article(
                    driver, blog_name, article["title"], article["content"],
                    visibility=req.visibility,
                    schedule_date=req.schedule_date,
                    schedule_time=req.schedule_time,
                )
                if success:
                    sheets.update_upload_status(article["name"], "업로드완료")
                    sheets.update_blog_status(article["name"], "업로드완료")
                else:
                    _batch_status[job_id]["errors"].append({"name": article["name"], "error": "발행 실패"})
            except Exception as e:
                _batch_status[job_id]["errors"].append({"name": article["name"], "error": str(e)})

            _batch_status[job_id]["done"] = i + 1
            import time
            time.sleep(5)

        _batch_status[job_id]["status"] = "completed"

    bg.add_task(_run)
    return {"job_id": job_id, "message": "배치 업로드 시작됨. /api/blog/generate/status/{job_id}로 진행 확인"}


# ──────────────────────────────────────────────────────
# 4. 이미지 업로드 + 적용 엔드포인트
# ──────────────────────────────────────────────────────

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """
    이미지 파일 업로드.
    반환: { url, filename } — url은 /uploads/images/filename 형태
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능")

    # 파일명 충돌 방지
    ext = Path(file.filename or "image.png").suffix or ".png"
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    save_path = _UPLOADS_DIR / unique_name

    content = await file.read()
    save_path.write_bytes(content)

    url = f"/uploads/images/{unique_name}"
    return {"url": url, "filename": unique_name, "size": len(content)}


@app.post("/api/blog/apply-images")
def apply_images(req: ApplyImagesRequest):
    """
    블로그 글의 [이미지: 설명] 태그를 <img> 태그로 교체 후 시트에 저장.
    req.images: [{ tag: "[이미지: 기능 화면]", image_url: "/uploads/images/xxx.png" }, ...]
    """
    sheets = _get_sheets()

    # 블로그 콘텐츠에서 글 가져오기
    try:
        sheet = sheets.spreadsheet.worksheet("블로그 콘텐츠")
        cell = sheet.find(req.tool_name, in_column=1)
        if not cell:
            raise HTTPException(status_code=404, detail=f"'{req.tool_name}' 블로그 없음")
        row = sheet.row_values(cell.row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    content = row[2] if len(row) > 2 else ""
    replaced_count = 0

    for mapping in req.images:
        tag = mapping.tag        # "[이미지: 기능 화면]"
        url = mapping.image_url  # "/uploads/images/xxx.png" or full URL

        # 절대 URL 생성 (상대 경로면 그대로 사용 — 프론트에서 처리)
        img_tag = f'<img src="{url}" alt="{tag}" style="max-width:100%; border-radius:8px; margin:16px 0;">'

        if tag in content:
            content = content.replace(tag, img_tag, 1)
            replaced_count += 1

    # 시트에 업데이트된 내용 저장
    if replaced_count > 0:
        sheet.update_cell(cell.row, 3, content)  # C열 = 내용

    return {
        "success": True,
        "tool_name": req.tool_name,
        "replaced_count": replaced_count,
        "total_tags": len(req.images),
        "content_length": len(content),
    }


@app.get("/api/blog/image-tags/{tool_name}")
def get_image_tags(tool_name: str):
    """
    특정 툴 블로그 글에서 [이미지: 설명] 태그 목록 추출.
    프론트엔드 탭4에서 드롭존 생성에 사용.
    """
    sheets = _get_sheets()
    try:
        sheet = sheets.spreadsheet.worksheet("블로그 콘텐츠")
        cell = sheet.find(tool_name, in_column=1)
        if not cell:
            raise HTTPException(status_code=404, detail=f"'{tool_name}' 블로그 없음")
        row = sheet.row_values(cell.row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    content = row[2] if len(row) > 2 else ""

    # [이미지: ...] 패턴 추출
    pattern = r'\[이미지:\s*([^\]]+)\]'
    matches = re.findall(pattern, content)
    tags = [{"index": i, "description": desc.strip(), "tag": f"[이미지: {desc.strip()}]"}
            for i, desc in enumerate(matches)]

    return {"tool_name": tool_name, "tags": tags, "total": len(tags)}


# ──────────────────────────────────────────────────────
# 5. 헬스체크 / 서버 정보
# ──────────────────────────────────────────────────────

@app.get("/")
def root():
    """루트 — Vercel 배포 확인용."""
    return {"status": "ok", "service": "AI있다 TAAFT Tracker API"}


@app.get("/api/health")
def health_check():
    """서버 상태 확인."""
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    has_tistory = all([
        os.environ.get("TISTORY_ID"),
        os.environ.get("TISTORY_PW"),
        os.environ.get("TISTORY_BLOG_NAME"),
    ])
    return {
        "status": "ok",
        "anthropic_api_key": has_api_key,
        "tistory_configured": has_tistory,
        "selenium_active": _driver is not None,
    }


@app.on_event("shutdown")
def shutdown_event():
    """서버 종료 시 브라우저 정리."""
    global _driver
    if _driver:
        _driver.quit()
        _driver = None


# ──────────────────────────────────────────────────────
# 직접 실행
# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
