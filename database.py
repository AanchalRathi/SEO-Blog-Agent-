"""
database.py — PostgreSQL layer

What this does:
    1. Connects to PostgreSQL using SQLAlchemy
    2. Defines the Blog table and Job table
    3. Creates tables automatically on first run
    4. Provides functions to save and retrieve blogs
    5. Provides functions to manage async generation jobs
"""

import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Text, DateTime, Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# ── CONNECTION ────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── BLOG MODEL ────────────────────────────────────────────────────────────────

class Blog(Base):
    """
    The blogs table — one row per generated blog.
    """
    __tablename__ = "blogs"

    id               = Column(Integer, primary_key=True, index=True)
    company_name     = Column(String,  nullable=False)
    niche            = Column(String,  nullable=True)
    keyword          = Column(String,  nullable=False)
    intent           = Column(String,  nullable=True)
    score            = Column(Integer, nullable=True)
    keywords_found   = Column(Integer, nullable=True)
    seo_title        = Column(String,  nullable=True)
    meta_description = Column(String,  nullable=True)
    slug             = Column(String,  nullable=True)
    blog_content     = Column(Text,    nullable=False)
    status           = Column(String,  default="draft")
    created_at       = Column(DateTime, default=datetime.utcnow)


# ── JOB MODEL ─────────────────────────────────────────────────────────────────

class Job(Base):
    """
    The jobs table — tracks every async blog generation request.
    
    Lifecycle:
        pending  → job created, pipeline not started yet
        running  → pipeline is actively running in background thread
        done     → pipeline finished, result stored in result_json
        failed   → pipeline crashed, error message stored in error
    """
    __tablename__ = "jobs"

    id          = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    status      = Column(String,  default="pending")
    company_name = Column(String, nullable=True)
    niche       = Column(String,  nullable=True)
    result_json = Column(Text,    nullable=True)   # full result dict as JSON string
    error       = Column(Text,    nullable=True)   # error message if failed
    blog_id     = Column(Integer, nullable=True)   # DB id of saved blog when done
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow)


# ── TABLE CREATION ────────────────────────────────────────────────────────────

def init_db():
    """
    Creates all tables if they don't exist yet.
    Safe to call multiple times — won't drop existing data.
    Called once at app startup in api.py.
    """
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables ready")


# ── SESSION HELPER ────────────────────────────────────────────────────────────

def get_db():
    """
    Yields a database session and closes it after use.
    Used as a FastAPI dependency in api.py.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── BLOG CRUD ─────────────────────────────────────────────────────────────────

def save_blog(db, result: dict, niche: str = "") -> Blog:
    blog = Blog(
        company_name     = result.get("company_name", ""),
        niche            = niche,
        keyword          = result.get("keyword", ""),
        intent           = result.get("intent", ""),
        score            = result.get("score", 0),
        keywords_found   = result.get("keywords_found", 0),
        seo_title        = result.get("seo_title", ""),
        meta_description = result.get("meta_description", ""),
        slug             = result.get("slug", ""),
        blog_content     = result.get("blog", ""),
        status           = "draft",
        created_at       = datetime.utcnow(),
    )
    db.add(blog)
    db.commit()
    db.refresh(blog)
    print(f"[DB] Blog saved — ID: {blog.id} | Company: {blog.company_name} | Keyword: {blog.keyword}")
    return blog


def get_blogs_by_company(db, company_name: str) -> list:
    return (
        db.query(Blog)
        .filter(Blog.company_name.ilike(f"%{company_name}%"))
        .order_by(Blog.created_at.desc())
        .all()
    )


def get_all_blogs(db) -> list:
    return db.query(Blog).order_by(Blog.created_at.desc()).all()


def update_blog_status(db, blog_id: int, status: str) -> Blog | None:
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if blog:
        blog.status = status
        db.commit()
        db.refresh(blog)
        print(f"[DB] Blog {blog_id} status updated to '{status}'")
    return blog


def keyword_exists(db, company_name: str, keyword: str) -> bool:
    existing = (
        db.query(Blog)
        .filter(
            Blog.company_name.ilike(f"%{company_name}%"),
            Blog.keyword.ilike(f"%{keyword}%"),
        )
        .first()
    )
    return existing is not None


def delete_blog(db, blog_id: int) -> bool:
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if blog:
        db.delete(blog)
        db.commit()
        print(f"[DB] Blog {blog_id} deleted")
        return True
    return False


# ── JOB CRUD ──────────────────────────────────────────────────────────────────

def create_job(db, company_name: str = "", niche: str = "") -> Job:
    """
    Creates a new job record in pending state.
    Called at the start of every /generate request.
    """
    job = Job(
        company_name = company_name,
        niche        = niche,
        status       = "pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    print(f"[DB] Job created — ID: {job.id}")
    return job


def get_job(db, job_id: str) -> Job | None:
    """
    Fetches a job by ID.
    Called by GET /jobs/{job_id} endpoint.
    """
    return db.query(Job).filter(Job.id == job_id).first()


def update_job_status(db, job_id: str, status: str):
    """
    Updates job to running or failed with no result.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status     = status
        job.updated_at = datetime.utcnow()
        db.commit()
        print(f"[DB] Job {job_id} → {status}")


def complete_job(db, job_id: str, result: dict, blog_id: int):
    """
    Marks job as done and stores the full result as JSON.
    Called after successful pipeline run.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status      = "done"
        job.result_json = json.dumps(result)
        job.blog_id     = blog_id
        job.updated_at  = datetime.utcnow()
        db.commit()
        print(f"[DB] Job {job_id} → done | Blog ID: {blog_id}")


def fail_job(db, job_id: str, error: str):
    """
    Marks job as failed and stores the error message.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status     = "failed"
        job.error      = error
        job.updated_at = datetime.utcnow()
        db.commit()
        print(f"[DB] Job {job_id} → failed: {error}")