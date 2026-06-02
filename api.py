"""
api.py — FastAPI backend

What this does:
    Exposes the full SEO agent pipeline as an HTTP API.
    Any frontend (Streamlit, Next.js, mobile app) can call it.

Endpoints:
    POST /generate        → runs full pipeline, returns blog + meta
    POST /upload-docs     → uploads brand docs to brand_docs/{company}/
    GET  /health          → health check

Run locally:
    uvicorn api:app --reload --port 8000

Install:
    pip install fastapi uvicorn python-multipart
"""

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from crew import CompanyConfig, run_crew

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SEO Agent API",
    description="Multi-agent SEO blog generator powered by CrewAI + RAG",
    version="1.0.0",
)

# Allow all origins for now — restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REQUEST / RESPONSE MODELS ─────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    company_name:    str         = Field(...,  example="Acme Corp")
    niche:           str         = Field(...,  example="food delivery")
    target_audience: str         = Field(...,  example="urban Indians who order food online")
    competitors:     list[str]   = Field([],   example=["RivalCo", "CompetitorX"])
    user_query:      str         = Field("",   example="best food delivery discount india")
    tone:            str         = Field("conversational", example="conversational")
    region:          str         = Field("India",          example="India")

    # docs_path is set server-side from uploaded docs — not passed by client
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
    error:            str = ""


class UploadResponse(BaseModel):
    success:      bool
    company_name: str
    files_saved:  list[str]
    docs_path:    str
    message:      str


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_docs_path(company_name: str) -> str:
    """
    Each company gets their own brand_docs subfolder.
    Prevents docs from different companies mixing.
    """
    safe_name = company_name.lower().replace(" ", "_")[:40]
    return f"brand_docs/{safe_name}/"


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Simple health check — used by Docker and deployment platforms."""
    return {"status": "ok", "service": "SEO Agent API"}


@app.post("/upload-docs", response_model=UploadResponse)
async def upload_docs(
    company_name: str,
    files: list[UploadFile] = File(...),
):
    """
    Upload brand documents for a company.
    Saves files to brand_docs/{company_name}/
    Supported: .pdf, .txt, .md

    Call this BEFORE /generate if you want RAG brand context.
    If you skip this, /generate still works — just without brand context.
    """
    docs_path = get_docs_path(company_name)
    Path(docs_path).mkdir(parents=True, exist_ok=True)

    saved = []
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
        raise HTTPException(
            status_code=400,
            detail="No valid files uploaded. Allowed types: .pdf, .txt, .md"
        )

    return UploadResponse(
        success=True,
        company_name=company_name,
        files_saved=saved,
        docs_path=docs_path,
        message=f"{len(saved)} file(s) uploaded. Ready for /generate."
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """
    Main endpoint — runs the full SEO agent pipeline.

    Flow:
        1. Build CompanyConfig (sets up RAG from uploaded docs if any)
        2. Run CrewAI pipeline: keyword discovery → strategy → writing
        3. Return blog + all meta fields

    If no docs were uploaded → RAG is skipped, blog still generates fine.
    """
    try:
        docs_path = get_docs_path(req.company_name)

        config = CompanyConfig(
            company_name=req.company_name,
            niche=req.niche,
            target_audience=req.target_audience,
            competitors=req.competitors,
            docs_path=docs_path,
            tone=req.tone,
            region=req.region,
            user_query=req.user_query,
        )

        result = run_crew(config)

        return GenerateResponse(
            success=True,
            company_name=req.company_name,
            keyword=result["keyword"],
            intent=result["intent"],
            score=result["score"],
            keywords_found=result["keywords_found"],
            seo_title=result["seo_title"],
            meta_description=result["meta_description"],
            slug=result["slug"],
            blog=result["blog"],
        )

    except Exception as e:
        return GenerateResponse(
            success=False,
            company_name=req.company_name,
            keyword="", intent="", slug="",
            seo_title="", meta_description="", blog="",
            score=0, keywords_found=0,
            error=str(e),
        )