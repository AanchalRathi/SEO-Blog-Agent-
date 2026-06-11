"""
app.py — Streamlit frontend with Blog History tab
"""

import streamlit as st
import requests

API_URL = "https://seo-agent-api-epz1.onrender.com"

st.set_page_config(
    page_title="SEO Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

/* ── sidebar collapse fix ── */
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[kind="headerNoPadding"] { display: none !important; }
[data-testid="stSidebar"] { min-width: 16rem !important; max-width: 40rem !important; transform: none !important; }

/* ── sidebar styling ── */
[data-testid="stSidebar"] { background: linear-gradient(160deg, #0f0f1a 0%, #1a1a2e 100%); border-right: 1px solid rgba(255,255,255,0.06); }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stTextInput input { background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 8px !important; color: #e2e8f0 !important; }
[data-testid="stSidebar"] label { font-size: 0.78rem !important; font-weight: 500 !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; color: #94a3b8 !important; }

.logo-block { padding: 1.5rem 0 1rem 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 1.5rem; }
.logo-title { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 800; background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin: 0; }
.logo-sub { font-size: 0.72rem; color: #64748b; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 0.3rem; }
.hero { background: linear-gradient(135deg, #0f0f1a 0%, #1e1b4b 50%, #0f172a 100%); border: 1px solid rgba(167,139,250,0.2); border-radius: 20px; padding: 2.5rem 3rem; margin-bottom: 2rem; position: relative; overflow: hidden; }
.hero::before { content: ''; position: absolute; top: -50%; right: -20%; width: 400px; height: 400px; background: radial-gradient(circle, rgba(167,139,250,0.08) 0%, transparent 70%); pointer-events: none; }
.hero-title { font-family: 'Syne', sans-serif; font-size: 2.8rem; font-weight: 800; color: #f8fafc; line-height: 1.1; margin: 0 0 0.5rem 0; }
.hero-title span { background: linear-gradient(135deg, #a78bfa, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.hero-sub { color: #94a3b8; font-size: 1rem; font-weight: 300; margin: 0; max-width: 500px; }
.phases { display: flex; gap: 0.75rem; margin-top: 1.5rem; flex-wrap: wrap; }
.phase-badge { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 100px; padding: 0.3rem 1rem; font-size: 0.75rem; color: #94a3b8; }
.phase-badge strong { color: #a78bfa; }
.metric-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
.metric-card { background: linear-gradient(135deg, #1e1b4b 0%, #1a1a2e 100%); border: 1px solid rgba(167,139,250,0.15); border-radius: 14px; padding: 1.2rem 1.5rem; text-align: center; }
.metric-value { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; color: #a78bfa; line-height: 1; margin-bottom: 0.3rem; }
.metric-label { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; }
.section-header { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: #e2e8f0; letter-spacing: 0.02em; margin: 2rem 0 1rem 0; display: flex; align-items: center; gap: 0.5rem; }
.section-header::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(167,139,250,0.3), transparent); }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
.meta-card { background: #0f172a; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 1rem 1.2rem; }
.meta-card-label { font-size: 0.7rem; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.4rem; }
.meta-card-value { font-size: 0.9rem; color: #e2e8f0; font-weight: 500; word-break: break-all; }
.meta-card-full { grid-column: 1 / -1; }
.keyword-pill { display: inline-block; background: linear-gradient(135deg, rgba(167,139,250,0.2), rgba(96,165,250,0.2)); border: 1px solid rgba(167,139,250,0.3); border-radius: 100px; padding: 0.4rem 1.2rem; font-size: 0.9rem; color: #a78bfa; font-weight: 600; margin-bottom: 1rem; }
.blog-wrapper { background: #0f172a; border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 2rem 2.5rem; line-height: 1.8; color: #cbd5e1; font-size: 0.95rem; }

/* ── history card ── */
.history-card { background: linear-gradient(135deg, #0f172a 0%, #1a1a2e 100%); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; }
.history-card:hover { border-color: rgba(167,139,250,0.25); }
.history-meta { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem; }
.history-tag { font-size: 0.72rem; color: #64748b; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 0.2rem 0.6rem; }
.status-draft     { color: #94a3b8 !important; border-color: rgba(148,163,184,0.3) !important; }
.status-published { color: #34d399 !important; border-color: rgba(52,211,153,0.3) !important; }
.status-archived  { color: #f87171 !important; border-color: rgba(248,113,113,0.3) !important; }

.stButton > button { background: linear-gradient(135deg, #7c3aed, #2563eb) !important; color: white !important; border: none !important; border-radius: 10px !important; font-family: 'Syne', sans-serif !important; font-weight: 700 !important; font-size: 1rem !important; width: 100% !important; }
.stDownloadButton > button { background: rgba(52,211,153,0.1) !important; color: #34d399 !important; border: 1px solid rgba(52,211,153,0.3) !important; border-radius: 10px !important; font-weight: 600 !important; width: 100% !important; }
.stTabs [data-baseweb="tab-list"] { background: transparent; gap: 0.5rem; }
.stTabs [data-baseweb="tab"] { background: rgba(255,255,255,0.04) !important; border-radius: 8px !important; color: #64748b !important; font-size: 0.85rem !important; padding: 0.4rem 1.2rem !important; }
.stTabs [aria-selected="true"] { background: rgba(167,139,250,0.15) !important; color: #a78bfa !important; }
</style>
""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="logo-block"><p class="logo-title">SEO Agent</p><p class="logo-sub">CrewAI · RAG · Groq</p></div>', unsafe_allow_html=True)
    st.markdown("**Company Details**")
    company_name    = st.text_input("Company name",     placeholder="e.g. Zomato")
    niche           = st.text_input("Niche / industry", placeholder="e.g. food delivery")
    target_audience = st.text_input("Target audience",  placeholder="e.g. urban Indians")
    competitors_raw = st.text_input("Competitors",      placeholder="e.g. Swiggy, EatSure")
    competitors     = [c.strip() for c in competitors_raw.split(",") if c.strip()]
    st.markdown("---")
    st.markdown("**Content Settings**")
    tone   = st.selectbox("Writing tone", ["conversational", "professional", "casual", "authoritative"])
    region = st.text_input("Target region", value="India")
    st.markdown("---")
    st.markdown("**Brand Documents**")
    st.caption("Upload PDFs, TXTs, or MDs for RAG brand context")
    uploaded_files = st.file_uploader("docs", type=["pdf", "txt", "md"], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded_files:
        for f in uploaded_files:
            st.caption(f"📄 {f.name}")


# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1 class="hero-title">SEO Blog <span>Generator</span></h1>
    <p class="hero-sub">Multi-agent pipeline that researches real keywords, builds a content strategy, and writes a publish-ready blog post.</p>
    <div class="phases">
        <span class="phase-badge"><strong>01</strong> Keyword Discovery</span>
        <span class="phase-badge"><strong>02</strong> Scoring & Strategy</span>
        <span class="phase-badge"><strong>03</strong> RAG Brand Context</span>
        <span class="phase-badge"><strong>04</strong> Blog Generation</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── MAIN TABS ─────────────────────────────────────────────────────────────────
# Two top-level tabs — Generate and Blog History
main_tab1, main_tab2 = st.tabs(["✍️ Generate Blog", "📚 Blog History"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GENERATE
# ══════════════════════════════════════════════════════════════════════════════

with main_tab1:

    col1, col2 = st.columns([4, 1])
    with col1:
        user_query = st.text_input("query", label_visibility="collapsed", placeholder="Optional — type a keyword to target, or leave blank to auto-generate")
    with col2:
        generate_btn = st.button("🚀 Generate", use_container_width=True, type="primary")

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def validate():
        if not company_name.strip():    return "Please enter your company name in the sidebar."
        if not niche.strip():           return "Please enter your niche / industry in the sidebar."
        if not target_audience.strip(): return "Please enter your target audience in the sidebar."
        return None

    def upload_brand_docs(company, files):
        if not files: return
        try:
            resp = requests.post(f"{API_URL}/upload-docs", params={"company_name": company}, files=[("files", (f.name, f.getvalue(), f.type)) for f in files], timeout=30)
            if resp.status_code == 200:
                st.success(f"✓ Uploaded {len(resp.json()['files_saved'])} brand doc(s)")
        except Exception:
            st.warning("Could not upload docs — continuing without brand context.")

    # ── GENERATE ──────────────────────────────────────────────────────────────
    if generate_btn:
        error = validate()
        if error:
            st.error(error)
        else:
            if uploaded_files:
                with st.spinner("Uploading brand documents..."):
                    upload_brand_docs(company_name, uploaded_files)

            with st.spinner("Running SEO agent pipeline... this takes ~30-60 seconds"):
                try:
                    resp   = requests.post(f"{API_URL}/generate", json={"company_name": company_name.strip(), "niche": niche.strip(), "target_audience": target_audience.strip(), "competitors": competitors, "user_query": user_query.strip(), "tone": tone, "region": region.strip()}, timeout=180)
                    result = resp.json()
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to the API. Make sure `uvicorn api:app --reload --port 8000` is running.")
                    st.stop()
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
                    st.stop()

            if not result.get("success"):
                st.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")
            else:
                st.success(f"✓ Blog generated and saved to database (ID: {result.get('blog_id', '—')})")

                st.markdown("""<div class="metric-row">
                    <div class="metric-card"><div class="metric-value">{kw}</div><div class="metric-label">Keywords Found</div></div>
                    <div class="metric-card"><div class="metric-value">{sc}</div><div class="metric-label">Best Score</div></div>
                    <div class="metric-card"><div class="metric-value">{it}</div><div class="metric-label">Intent</div></div>
                    <div class="metric-card"><div class="metric-value">✓</div><div class="metric-label">Blog Ready</div></div>
                </div>""".format(kw=result["keywords_found"], sc=result["score"], it=result["intent"].capitalize()[:5]), unsafe_allow_html=True)

                st.markdown(f'<div class="keyword-pill">🎯 {result["keyword"]}</div>', unsafe_allow_html=True)
                st.markdown('<div class="section-header">SEO Meta</div>', unsafe_allow_html=True)
                st.markdown(f"""<div class="meta-grid">
                    <div class="meta-card"><div class="meta-card-label">SEO Title</div><div class="meta-card-value">{result["seo_title"]}</div></div>
                    <div class="meta-card"><div class="meta-card-label">URL Slug</div><div class="meta-card-value">/{result["slug"]}</div></div>
                    <div class="meta-card meta-card-full"><div class="meta-card-label">Meta Description</div><div class="meta-card-value">{result["meta_description"]}</div></div>
                </div>""", unsafe_allow_html=True)

                st.markdown('<div class="section-header">Generated Blog Post</div>', unsafe_allow_html=True)
                tab1, tab2 = st.tabs(["📄 Formatted", "📋 Raw Text"])
                with tab1:
                    st.markdown('<div class="blog-wrapper">', unsafe_allow_html=True)
                    st.markdown(result["blog"])
                    st.markdown('</div>', unsafe_allow_html=True)
                with tab2:
                    st.text_area("", value=result["blog"], height=500, label_visibility="collapsed")

                st.markdown("---")
                st.download_button(label="⬇️ Download Blog as .txt", data=f"COMPANY: {result['company_name']}\nKEYWORD: {result['keyword']}\nSEO TITLE: {result['seo_title']}\nMETA: {result['meta_description']}\nSLUG: {result['slug']}\n\n{'='*60}\n\n{result['blog']}", file_name=f"{result['slug'] or 'blog'}.txt", mime="text/plain", use_container_width=True)

    # ── EMPTY STATE ───────────────────────────────────────────────────────────
    else:
        st.markdown('<div class="section-header">How It Works</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**🔍 Keyword Discovery**\n\nFinds hundreds of real keywords from Google autocomplete and Serper based on your company and competitors.")
        with c2:
            st.markdown("**📊 Scoring & Strategy**\n\nScores every keyword by intent, brand relevance, and long-tail value. Picks the best one to target.")
        with c3:
            st.markdown("**🧠 RAG Brand Context**\n\nReads your brand docs and retrieves relevant context so the blog sounds like your brand, not generic AI.")
        with c4:
            st.markdown("**✍️ Blog Generation**\n\nWrites a complete 900-1100 word SEO blog with H2s, FAQs, offers, and a CTA using Groq + Llama.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — BLOG HISTORY
# ══════════════════════════════════════════════════════════════════════════════

with main_tab2:

    st.markdown('<div class="section-header">Blog History</div>', unsafe_allow_html=True)

    # filter row
    col_filter, col_refresh = st.columns([3, 1])
    with col_filter:
        filter_company = st.text_input("Filter by company", placeholder="e.g. Zomato — leave blank for all", label_visibility="collapsed")
    with col_refresh:
        refresh_btn = st.button("🔄 Refresh", use_container_width=True)

    # fetch blogs from API
    try:
        params = {"company_name": filter_company} if filter_company.strip() else {}
        resp   = requests.get(f"{API_URL}/blogs", params=params, timeout=10)
        blogs  = resp.json().get("blogs", [])
    except Exception:
        st.error("Cannot connect to the API. Make sure `uvicorn api:app --reload --port 8000` is running.")
        blogs = []

    if not blogs:
        st.info("No blogs generated yet. Go to the Generate tab to create your first blog.")
    else:
        st.caption(f"{len(blogs)} blog(s) found")

        for blog in blogs:
            # status color class
            status_class = f"status-{blog['status']}"

            with st.expander(f"#{blog['id']}  {blog['seo_title'] or blog['keyword']}  —  {blog['company_name']}  ·  {blog['created_at']}", expanded=False):

                # meta row
                st.markdown(f"""
                <div class="history-meta">
                    <span class="history-tag">🎯 {blog['keyword']}</span>
                    <span class="history-tag">📊 Score: {blog['score']}</span>
                    <span class="history-tag">🔍 {blog['intent'].capitalize() if blog['intent'] else '—'}</span>
                    <span class="history-tag">🏢 {blog['niche'] or '—'}</span>
                    <span class="history-tag {status_class}">● {blog['status'].capitalize()}</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("---")

                # blog content tabs
                h_tab1, h_tab2 = st.tabs(["📄 Formatted", "📋 Raw Text"])
                with h_tab1:
                    st.markdown(blog["blog_content"])
                with h_tab2:
                    st.text_area("", value=blog["blog_content"], height=400, label_visibility="collapsed", key=f"raw_{blog['id']}")

                st.markdown("---")

                # action row — status update + delete
                action_col1, action_col2, action_col3 = st.columns([2, 2, 1])

                with action_col1:
                    new_status = st.selectbox(
                        "Status",
                        ["draft", "published", "archived"],
                        index=["draft", "published", "archived"].index(blog["status"]),
                        key=f"status_{blog['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != blog["status"]:
                        try:
                            requests.patch(f"{API_URL}/blogs/{blog['id']}/status", json={"status": new_status}, timeout=5)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()
                        except Exception:
                            st.error("Could not update status.")

                with action_col2:
                    st.download_button(
                        label="⬇️ Download",
                        data=f"COMPANY: {blog['company_name']}\nKEYWORD: {blog['keyword']}\nSEO TITLE: {blog['seo_title']}\nMETA: {blog['meta_description']}\nSLUG: {blog['slug']}\n\n{'='*60}\n\n{blog['blog_content']}",
                        file_name=f"{blog['slug'] or 'blog'}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key=f"dl_{blog['id']}",
                    )

                with action_col3:
                    if st.button("🗑️ Delete", key=f"del_{blog['id']}", use_container_width=True):
                        try:
                            requests.delete(f"{API_URL}/blogs/{blog['id']}", timeout=5)
                            st.success("Blog deleted.")
                            st.rerun()
                        except Exception:
                            st.error("Could not delete blog.")