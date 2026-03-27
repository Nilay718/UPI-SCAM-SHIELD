from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents.ocr import extract_text_from_image
from app.feedback_db import init_db, insert_feedback, stats as feedback_stats
from app.pipeline import analyze_text, analyze_text_verbose
from app.schemas import AnalyzeResponseV2, AnalyzeResponseVerbose, FeedbackRequest
from app.settings import settings


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origin_list or ["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=bool(settings.cors_allow_credentials),
    allow_methods=["*"],
    allow_headers=["*"],
)


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    """Lightweight check for Docker / load balancers."""
    return {"status": "ok", "app": settings.app_name}


@app.get("/")
def index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"status": "ok", "message": "Frontend not found. Place UI in /frontend."}


@app.get("/analyzer")
def analyzer_page():
    analyzer_path = FRONTEND_DIR / "analyzer.html"
    if analyzer_path.exists():
        return FileResponse(str(analyzer_path))
    raise HTTPException(status_code=404, detail="Analyzer page not found.")


@app.get("/analyze", response_model=AnalyzeResponseV2)
async def analyze(
    text: str,
    sender_type: str = "unknown",
    transaction_context: str = "expected",
    user_type: str = "general",
):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Query param 'text' is required.")
    return await analyze_text(
        text,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )


@app.get("/analyze-verbose", response_model=AnalyzeResponseVerbose)
async def analyze_verbose(
    text: str,
    sender_type: str = "unknown",
    transaction_context: str = "expected",
    user_type: str = "general",
):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Query param 'text' is required.")
    return await analyze_text_verbose(
        text,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )


@app.post("/analyze-image", response_model=AnalyzeResponseV2)
async def analyze_image(
    file: UploadFile = File(...),
    sender_type: str = Form("unknown"),
    transaction_context: str = Form("expected"),
    user_type: str = Form("general"),
):
    if not file:
        raise HTTPException(status_code=400, detail="File is required.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in set(settings.allowed_image_content_type_list):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Allowed: {', '.join(settings.allowed_image_content_type_list)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    max_bytes = int(max(1, settings.max_upload_mb) * 1024 * 1024)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_upload_mb} MB.")

    try:
        extracted, warning = extract_text_from_image(content)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail="Could not read text from image. Try a clearer screenshot.",
        ) from e

    if not extracted or len(extracted.strip()) < 5:
        raise HTTPException(
            status_code=422,
            detail="Could not read text from image. Try a clearer screenshot.",
        )

    result = await analyze_text(
        extracted,
        extracted_text=extracted,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )
    # Include warning as a reason (non-fatal)
    if warning and result.final_decision.reason:
        result.final_decision.reason = [warning] + result.final_decision.reason
    return result


@app.post("/analyze-image-verbose", response_model=AnalyzeResponseVerbose)
async def analyze_image_verbose(
    file: UploadFile = File(...),
    sender_type: str = Form("unknown"),
    transaction_context: str = Form("expected"),
    user_type: str = Form("general"),
):
    if not file:
        raise HTTPException(status_code=400, detail="File is required.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in set(settings.allowed_image_content_type_list):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Allowed: {', '.join(settings.allowed_image_content_type_list)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    max_bytes = int(max(1, settings.max_upload_mb) * 1024 * 1024)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.max_upload_mb} MB.")

    try:
        extracted, warning = extract_text_from_image(content)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail="Could not read text from image. Try a clearer screenshot.",
        ) from e

    if not extracted or len(extracted.strip()) < 5:
        raise HTTPException(
            status_code=422,
            detail="Could not read text from image. Try a clearer screenshot.",
        )

    result = await analyze_text_verbose(
        extracted,
        extracted_text=extracted,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )
    if warning and result.final_decision.reason:
        result.final_decision.reason = [warning] + result.final_decision.reason
    return result


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    insert_feedback(
        input_text=req.input_text,
        extracted_text=req.extracted_text,
        predicted_risk_level=req.predicted_risk_level,
        predicted_is_scam=req.predicted_is_scam,
        user_label=req.user_label,
        analysis_log_id=req.analysis_log_id,
    )
    return {"status": "ok"}


@app.get("/feedback-stats")
def feedback_stats_endpoint():
    return feedback_stats()

