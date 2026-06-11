"""
database.py — PostgreSQL layer

What this does:
    1. Connects to PostgreSQL using SQLAlchemy
    2. Defines the Blog table as a Python class
    3. Creates the table automatically on first run
    4. Provides functions to save and retrieve blogs
"""

import os
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, Column, Integer, String,
    Text, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# ── CONNECTION ────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True,connect_args={"sslmode": "require"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── MODEL ─────────────────────────────────────────────────────────────────────

class Blog(Base):
    """
    The blogs table — one row per generated blog.
    SQLAlchemy reads this class and creates the actual SQL table.
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


# ── TABLE CREATION ────────────────────────────────────────────────────────────

def init_db():
    """
    Creates all tables if they don't exist yet.
    Safe to call multiple times.
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


# ── CRUD OPERATIONS ───────────────────────────────────────────────────────────

def save_blog(db, result: dict, niche: str = "") -> Blog:
    """
    Saves a generated blog result to the database.
    Called in api.py after every successful /generate run.
    """
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
    """
    Returns all blogs for a specific company, newest first.
    Used in the Streamlit UI blog history tab.
    """
    return (
        db.query(Blog)
        .filter(Blog.company_name.ilike(f"%{company_name}%"))
        .order_by(Blog.created_at.desc())
        .all()
    )


def get_all_blogs(db) -> list:
    """
    Returns all blogs across all companies, newest first.
    """
    return db.query(Blog).order_by(Blog.created_at.desc()).all()


def update_blog_status(db, blog_id: int, status: str) -> Blog | None:
    """
    Updates the status of a blog — draft, published, or archived.
    """
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if blog:
        blog.status = status
        db.commit()
        db.refresh(blog)
        print(f"[DB] Blog {blog_id} status updated to '{status}'")
    return blog


def keyword_exists(db, company_name: str, keyword: str) -> bool:
    """
    Checks if a blog for this keyword already exists for this company.
    Prevents wasting API calls regenerating the same content.
    """
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
    """
    Permanently deletes a blog. Returns True if deleted, False if not found.
    """
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if blog:
        db.delete(blog)
        db.commit()
        print(f"[DB] Blog {blog_id} deleted")
        return True
    return False