"""
api.py — FastAPI backend with async job pattern

Endpoints:
    POST /generate           → starts pipeline in background, returns job_id instantly
    GET  /jobs/{job_id}      → poll this to check job status and get result
    POST /upload-docs        → uploads brand docs
    GET  /health             → health check
    GET  /blogs              → get all blogs
    PATCH /blogs/{id}/status → update blog status
    DELETE /blogs/{id}       → delete a blog

The async pattern:
    POST /generate → {"job_id": "abc-123", "status": "pending"}  ← instant
    GET  /jobs/abc-123 → {"status": "running"}                   ← after 1s
    GET  /jobs/abc-123 → {"status": "done", "result": {...}}     ← after ~60-90s
"""

import os
import json
import shutil
import asyncio
from pathlib import Path
import threading

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from crew import CompanyConfig, run_crew
from database import (
    init_db, get_db, SessionLocal,
    save_blog, get_blogs_by_company, get_all_blogs,
    update_blog_status, delete_blog, keyword_exists,
    create_job, get_job, update_job_status, complete_job, fail_job,
)

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SEO Agent API",
    description="Multi-agent SEO blog generator powered by CrewAI + RAG",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()


# ── REQUEST / RESPONSE MODELS ─────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    company_name:    str       = Field(..., example="Acme Corp")
    niche:           str       = Field(..., example="food delivery")
    target_audience: str       = Field(..., example="urban Indians who order food online")
    competitors:     list[str] = Field([], example=["RivalCo", "CompetitorX"])
    user_query:      str       = Field("", example="best food delivery discount india")
    tone:            str       = Field("conversational")
    region:          str       = Field("India")

    class Config:
        json_schema_extra = {
            "example": {
                "company_name":    "Acme Corp",
                "niche":           "food delivery",
                "target_audience": "urban Indians who order food online",
                "competitors":     ["RivalCo", "CompetitorX"],
                "user_query":      "",
                "tone":            "conversational",
                "region":          "India",
            }
        }


class UploadResponse(BaseModel):
    success:      bool
    company_name: str
    files_saved:  list[str]
    docs_path:    str
    message:      str


class BlogResponse(BaseModel):
    id:               int
    company_name:     str
    niche:            str | None
    keyword:          str
    intent:           str | None
    score:            int | None
    keywords_found:   int | None
    seo_title:        str | None
    meta_description: str | None
    slug:             str | None
    blog_content:     str
    status:           str
    created_at:       str

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str = Field(..., example="published")


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_docs_path(company_name: str) -> str:
    safe_name = company_name.lower().replace(" ", "_")[:40]
    return f"brand_docs/{safe_name}/"


def blog_to_dict(blog) -> dict:
    return {
        "id":               blog.id,
        "company_name":     blog.company_name,
        "niche":            blog.niche or "",
        "keyword":          blog.keyword,
        "intent":           blog.intent or "",
        "score":            blog.score or 0,
        "keywords_found":   blog.keywords_found or 0,
        "seo_title":        blog.seo_title or "",
        "meta_description": blog.meta_description or "",
        "slug":             blog.slug or "",
        "blog_content":     blog.blog_content,
        "status":           blog.status or "draft",
        "created_at":       blog.created_at.strftime("%Y-%m-%d %H:%M") if blog.created_at else "",
    }


# ── BACKGROUND PIPELINE ───────────────────────────────────────────────────────

def _run_pipeline(job_id: str, req_data: dict):
    """
    Runs the full CrewAI pipeline in a background thread.
    
    Uses its own DB session (separate from the request session)
    because this runs outside the FastAPI request/response cycle.
    Render never sees this as a slow request — it runs invisibly
    in the background while /jobs/{id} polling handles the wait.
    """
    db = SessionLocal()
    try:
        # mark job as running
        update_job_status(db, job_id, "running")

        config = CompanyConfig(
            company_name    = req_data["company_name"],
            niche           = req_data["niche"],
            target_audience = req_data["target_audience"],
            competitors     = req_data["competitors"],
            docs_path       = get_docs_path(req_data["company_name"]),
            tone            = req_data["tone"],
            region          = req_data["region"],
            user_query      = req_data["user_query"],
        )

        # run the full pipeline — takes 60-90 seconds, no timeout issue
        result = run_crew(config)
        result["company_name"] = req_data["company_name"]

        # save blog to DB
        saved = save_blog(db, result, niche=req_data["niche"])

        # mark job as done with full result
        complete_job(db, job_id, result, blog_id=saved.id)

    except Exception as e:
        fail_job(db, job_id, error=str(e))
        print(f"[Pipeline] Job {job_id} failed: {e}")
    finally:
        db.close()


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "SEO Agent API"}


@app.post("/generate")
async def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    # create job record in DB
    job = create_job(db, company_name=req.company_name, niche=req.niche)

    # use threading directly — more reliable than run_in_executor on Render
    thread = threading.Thread(
        target=_run_pipeline,
        args=(job.id, req.model_dump()),
        daemon=True,
    )
    thread.start()

    return {
        "job_id":  job.id,
        "status":  "pending",
        "message": "Pipeline started. Poll /jobs/{job_id} for updates.",
    }


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Streamlit polls this every 5 seconds after submitting /generate.
    
    Returns:
        pending → pipeline queued, not started
        running → pipeline actively generating
        done    → result is ready, full blog in response
        failed  → something went wrong, error message included
    """
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    response = {
        "job_id":     job.id,
        "status":     job.status,
        "error":      job.error or "",
        "blog_id":    job.blog_id,
        "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # only attach full result when done — keeps polling responses small
    if job.status == "done" and job.result_json:
        response["result"] = json.loads(job.result_json)

    return response


@app.post("/upload-docs", response_model=UploadResponse)
async def upload_docs(
    company_name: str,
    files: list[UploadFile] = File(...),
):
    docs_path = get_docs_path(company_name)
    Path(docs_path).mkdir(parents=True, exist_ok=True)

    saved   = []
    allowed = {".pdf", ".txt", ".md"}

    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed:
            continue
        dest = os.path.join(docs_path, file.filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved.append(file.filename)

    if not saved:
        raise HTTPException(status_code=400, detail="No valid files. Allowed: .pdf .txt .md")

    return UploadResponse(
        success=True,
        company_name=company_name,
        files_saved=saved,
        docs_path=docs_path,
        message=f"{len(saved)} file(s) uploaded. Ready for /generate.",
    )


@app.get("/blogs")
def get_blogs(company_name: str = "", db: Session = Depends(get_db)):
    if company_name:
        blogs = get_blogs_by_company(db, company_name)
    else:
        blogs = get_all_blogs(db)
    return {"blogs": [blog_to_dict(b) for b in blogs]}


@app.patch("/blogs/{blog_id}/status")
def update_status(blog_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    allowed_statuses = {"draft", "published", "archived"}
    if body.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {allowed_statuses}")
    blog = update_blog_status(db, blog_id, body.status)
    if not blog:
        raise HTTPException(status_code=404, detail=f"Blog {blog_id} not found")
    return {"success": True, "blog_id": blog_id, "status": body.status}


@app.delete("/blogs/{blog_id}")
def remove_blog(blog_id: int, db: Session = Depends(get_db)):
    deleted = delete_blog(db, blog_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Blog {blog_id} not found")
    return {"success": True, "blog_id": blog_id}