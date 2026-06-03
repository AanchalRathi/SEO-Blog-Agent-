"""
app.py — Streamlit frontend

What this does:
    Provides a clean web UI so any company can use the SEO agent
    without touching code. They fill a form, upload brand docs,
    click Generate, and get a full blog post with meta fields.

    Calls api.py under the hood via HTTP — so the frontend and
    backend are fully decoupled.

Run locally:
    # Terminal 1 — start the API
    uvicorn api:app --reload --port 8000

    # Terminal 2 — start the UI
    streamlit run app.py

Install:
    pip install streamlit requests
"""

import streamlit as st
import requests
import json

# ── CONFIG ────────────────────────────────────────────────────────────────────

API_URL = "http://localhost:8000"   # change to deployed URL in production

st.set_page_config(
    page_title="SEO Agent",
    page_icon="🔍",
    layout="wide",
)


# ── SIDEBAR — COMPANY SETUP ───────────────────────────────────────────────────

with st.sidebar:
    st.title("🔍 SEO Agent")
    st.caption("Powered by CrewAI + RAG")
    st.divider()

    st.subheader("Company Details")

    company_name = st.text_input(
        "Company name",
        placeholder="e.g. Acme Corp",
    )

    niche = st.text_input(
        "Niche / industry",
        placeholder="e.g. food delivery, e-commerce, edtech",
    )

    target_audience = st.text_input(
        "Target audience",
        placeholder="e.g. urban Indians who order food online",
    )

    competitors_raw = st.text_input(
        "Competitors (comma separated)",
        placeholder="e.g. RivalCo, CompetitorX",
    )
    competitors = [c.strip() for c in competitors_raw.split(",") if c.strip()]

    st.divider()
    st.subheader("Content Settings")

    tone = st.selectbox(
        "Writing tone",
        ["conversational", "professional", "casual", "authoritative"],
    )

    region = st.text_input("Target region", value="India")

    st.divider()
    st.subheader("Brand Documents (optional)")
    st.caption("Upload PDFs, TXTs, or MDs — RAG will inject brand context into the blog")

    uploaded_files = st.file_uploader(
        "Upload brand docs",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
    )


# ── MAIN AREA ─────────────────────────────────────────────────────────────────

st.title("SEO Blog Generator")
st.caption("Fill in your company details in the sidebar, then generate a fully SEO-optimized blog post.")

# Optional: manual keyword query
st.subheader("Keyword Mode")
col1, col2 = st.columns([3, 1])

with col1:
    user_query = st.text_input(
        "Type a search query (optional)",
        placeholder="e.g. best food delivery discount india — leave blank to auto-generate",
    )

with col2:
    st.write("")  # spacer
    st.write("")  # spacer
    generate_btn = st.button("🚀 Generate Blog", use_container_width=True, type="primary")


# ── VALIDATION ────────────────────────────────────────────────────────────────

def validate() -> str | None:
    """Returns error message string if invalid, None if ok."""
    if not company_name.strip():
        return "Please enter your company name in the sidebar."
    if not niche.strip():
        return "Please enter your niche / industry in the sidebar."
    if not target_audience.strip():
        return "Please enter your target audience in the sidebar."
    return None


# ── UPLOAD DOCS ───────────────────────────────────────────────────────────────

def upload_brand_docs(company: str, files) -> bool:
    """Uploads brand docs to the API before generating."""
    if not files:
        return True  # no docs is fine — RAG just skips

    file_tuples = [
        ("files", (f.name, f.getvalue(), f.type))
        for f in files
    ]

    try:
        resp = requests.post(
            f"{API_URL}/upload-docs",
            params={"company_name": company},
            files=file_tuples,
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.success(f"✓ Uploaded {len(data['files_saved'])} brand doc(s): {', '.join(data['files_saved'])}")
            return True
        else:
            st.warning(f"Doc upload issue: {resp.text} — continuing without brand context.")
            return True  # still continue, RAG just skips
    except Exception as e:
        st.warning(f"Could not upload docs: {e} — continuing without brand context.")
        return True


# ── GENERATE ──────────────────────────────────────────────────────────────────

if generate_btn:
    error = validate()
    if error:
        st.error(error)
    else:
        # Step 1 — upload docs if any
        if uploaded_files:
            with st.spinner("Uploading brand documents..."):
                upload_brand_docs(company_name, uploaded_files)

        # Step 2 — run the pipeline
        with st.spinner("Running SEO agent pipeline... this takes ~30-60 seconds"):
            payload = {
                "company_name":    company_name.strip(),
                "niche":           niche.strip(),
                "target_audience": target_audience.strip(),
                "competitors":     competitors,
                "user_query":      user_query.strip(),
                "tone":            tone,
                "region":          region.strip(),
            }

            try:
                resp = requests.post(
                    f"{API_URL}/generate",
                    json=payload,
                    timeout=180,    # pipeline can take up to 3 min
                )
                result = resp.json()

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to the API. "
                    "Make sure `uvicorn api:app --reload --port 8000` is running."
                )
                st.stop()

            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.stop()

        # Step 3 — display results
        if not result.get("success"):
            st.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")
        else:
            st.success(f"✓ Blog generated for **{result['company_name']}**")

            # ── METRICS ROW ───────────────────────────────────────────────────
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Keywords Found", result["keywords_found"])
            m2.metric("Best Keyword Score", result["score"])
            m3.metric("Search Intent", result["intent"].capitalize())
            m4.metric("Target Keyword", result["keyword"][:20] + "..." if len(result["keyword"]) > 20 else result["keyword"])

            st.divider()

            # ── SEO META ──────────────────────────────────────────────────────
            st.subheader("SEO Meta")
            col_a, col_b = st.columns(2)

            with col_a:
                st.text_input("SEO Title", value=result["seo_title"], disabled=True)
                st.text_input("Slug", value=result["slug"], disabled=True)

            with col_b:
                st.text_area("Meta Description", value=result["meta_description"], height=90, disabled=True)

            st.divider()

            # ── BLOG OUTPUT ───────────────────────────────────────────────────
            st.subheader("Generated Blog Post")

            tab1, tab2 = st.tabs(["📄 Formatted", "📋 Raw Text"])

            with tab1:
                st.markdown(result["blog"])

            with tab2:
                st.text_area(
                    "Raw blog text — copy and paste into your CMS",
                    value=result["blog"],
                    height=600,
                )

            # ── DOWNLOAD ──────────────────────────────────────────────────────
            st.divider()
            download_content = (
                f"COMPANY       : {result['company_name']}\n"
                f"KEYWORD       : {result['keyword']}\n"
                f"INTENT        : {result['intent']} | SCORE: {result['score']}\n"
                f"SEO TITLE     : {result['seo_title']}\n"
                f"META DESC     : {result['meta_description']}\n"
                f"SLUG          : {result['slug']}\n"
                f"\n{'='*60}\n\n"
                f"{result['blog']}"
            )

            st.download_button(
                label="⬇️ Download Blog as .txt",
                data=download_content,
                file_name=f"{result['slug'] or 'blog'}.txt",
                mime="text/plain",
                use_container_width=True,
            )


# ── EMPTY STATE ───────────────────────────────────────────────────────────────

else:
    st.info(
        "👈 Fill in your company details in the sidebar, then click **Generate Blog** to start."
    )

    with st.expander("How it works"):
        st.markdown("""
**Phase 1 — Keyword Discovery**
Discovers hundreds of real keywords from Google autocomplete and Serper based on your company and competitors.

**Phase 2 — Scoring & Strategy**
Scores every keyword by search intent, brand relevance, and long-tail value. Picks the best one to target.

**Phase 3 — Blog Generation**
Writes a complete 900-1100 word SEO blog post with H2 sections, FAQs, offers, and a CTA — using your brand docs for accuracy.

**RAG (optional)**
Upload your brand guidelines, product docs, or past blogs — the system uses them to write content that actually sounds like your brand.
        """)