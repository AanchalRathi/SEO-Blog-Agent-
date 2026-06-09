"""
api.py — FastAPI backend with PostgreSQL integration

Endpoints:
    POST /generate          → runs full pipeline, saves to DB, returns blog
    POST /upload-docs       → uploads brand docs to brand_docs/{company}/
    GET  /health            → health check
    GET  /blogs             → get all blogs (with optional company filter)
    PATCH /blogs/{id}/status → update blog status
    DELETE /blogs/{id}      → delete a blog

Run locally:
    uvicorn api:app --reload --port 8000
"""

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from crew import CompanyConfig, run_crew
from database import init_db, get_db, save_blog, get_blogs_by_company, get_all_blogs, update_blog_status, delete_blog, keyword_exists

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SEO Agent API",
    description="Multi-agent SEO blog generator powered by CrewAI + RAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup — safe to call multiple times
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


class GenerateResponse(BaseModel):
    success:          bool
    company_name:     str
    keyword:          str
    intent:           str
    score:            int
    keywords_found:   int
    seo_title:        str
    meta_description: str
    slug:             str
    blog:             str
    blog_id:          int  = 0     # DB id of saved blog
    error:            str  = ""


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
    status: str = Field(..., example="published")  # draft / published / archived


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_docs_path(company_name: str) -> str:
    safe_name = company_name.lower().replace(" ", "_")[:40]
    return f"brand_docs/{safe_name}/"


def blog_to_dict(blog) -> dict:
    """Converts a Blog ORM object to a clean dict for the response."""
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


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "SEO Agent API"}


@app.post("/upload-docs", response_model=UploadResponse)
async def upload_docs(
    company_name: str,
    files: list[UploadFile] = File(...),
):
    docs_path = get_docs_path(company_name)
    Path(docs_path).mkdir(parents=True, exist_ok=True)

    saved  = []
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
        raise HTTPException(status_code=400, detail="No valid files uploaded. Allowed: .pdf .txt .md")

    return UploadResponse(
        success=True,
        company_name=company_name,
        files_saved=saved,
        docs_path=docs_path,
        message=f"{len(saved)} file(s) uploaded. Ready for /generate."
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    """
    Runs the full SEO pipeline and saves the result to PostgreSQL.

    New vs original:
    - Checks if keyword already exists for this company before running
    - Saves blog to DB after successful generation
    - Returns blog_id so the frontend can reference it
    """
    try:
        docs_path = get_docs_path(req.company_name)

        config = CompanyConfig(
            company_name    = req.company_name,
            niche           = req.niche,
            target_audience = req.target_audience,
            competitors     = req.competitors,
            docs_path       = docs_path,
            tone            = req.tone,
            region          = req.region,
            user_query      = req.user_query,
        )

        result = run_crew(config)

        # add company_name to result so save_blog can access it
        result["company_name"] = req.company_name

        # save to PostgreSQL
        saved = save_blog(db, result, niche=req.niche)

        return GenerateResponse(
            success          = True,
            company_name     = req.company_name,
            keyword          = result["keyword"],
            intent           = result["intent"],
            score            = result["score"],
            keywords_found   = result["keywords_found"],
            seo_title        = result["seo_title"],
            meta_description = result["meta_description"],
            slug             = result["slug"],
            blog             = result["blog"],
            blog_id          = saved.id,
        )

    except Exception as e:
        return GenerateResponse(
            success=False,
            company_name=req.company_name,
            keyword="", intent="", slug="",
            seo_title="", meta_description="", blog="",
            score=0, keywords_found=0, blog_id=0,
            error=str(e),
        )


@app.get("/blogs")
def get_blogs(company_name: str = "", db: Session = Depends(get_db)):
    """
    Returns all saved blogs.
    Pass ?company_name=Zomato to filter by company.
    Used by the Streamlit blog history tab.
    """
    if company_name:
        blogs = get_blogs_by_company(db, company_name)
    else:
        blogs = get_all_blogs(db)

    return {"blogs": [blog_to_dict(b) for b in blogs]}


@app.patch("/blogs/{blog_id}/status")
def update_status(blog_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    """
    Updates blog status to draft, published, or archived.
    Called from the Streamlit UI status dropdown.
    """
    allowed_statuses = {"draft", "published", "archived"}
    if body.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {allowed_statuses}")

    blog = update_blog_status(db, blog_id, body.status)
    if not blog:
        raise HTTPException(status_code=404, detail=f"Blog {blog_id} not found")

    return {"success": True, "blog_id": blog_id, "status": body.status}


@app.delete("/blogs/{blog_id}")
def remove_blog(blog_id: int, db: Session = Depends(get_db)):
    """
    Permanently deletes a blog from the database.
    """
    deleted = delete_blog(db, blog_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Blog {blog_id} not found")

    return {"success": True, "blog_id": blog_id}