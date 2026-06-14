"""
crew.py — SEO Blog Generation Pipeline

Pipeline (single-call mode — optimized for free tier):
    1. Keyword Discovery (Google autocomplete + Serper)
    2. Keyword Scoring and Selection
    3. Blog type auto-selection based on keyword intent
    4. RAG Brand Context retrieval
    5. Blog Generation (one Groq call)

CrewAI multi-agent mode is commented out at the bottom.
Uncomment run_crew_multi_agent() when on Groq Dev tier.
"""

import os
import time
from dotenv import load_dotenv

from keyword_discovery import discover_all_keywords, discover_from_input
from keyword_analysis import analyze_keywords, build_brand_terms
from blog_generator import generate_blog, extract_meta
from tools.rag_tool import setup_rag, get_brand_context

load_dotenv()


# ── COMPANY CONFIG ────────────────────────────────────────────────────────────

class CompanyConfig:
    def __init__(
        self,
        company_name: str,
        niche: str,
        target_audience: str,
        competitors: list[str],
        docs_path: str = "brand_docs/",
        tone: str = "conversational",
        region: str = "India",
        user_query: str = "",
    ):
        self.company_name    = company_name
        self.niche           = niche
        self.target_audience = target_audience
        self.competitors     = competitors
        self.docs_path       = docs_path
        self.tone            = tone
        self.region          = region
        self.user_query      = user_query
        self.brand_terms     = build_brand_terms(company_name, competitors)

        print(f"\n[Pipeline] Setting up RAG for '{company_name}'...")
        self.vectorstore = setup_rag(docs_path, company_name)


# ── BLOG TYPE SELECTOR ────────────────────────────────────────────────────────

def select_blog_type(keyword: str) -> str:
    """
    Auto-selects blog type based on keyword text and intent signals.
    No LLM call needed — simple rule-based matching.
    """
    kw = keyword.lower()

    if any(w in kw for w in ["vs", "versus", "better", "difference", "compare", "alternative"]):
        return "comparison"
    elif any(w in kw for w in ["how to", "how do", "guide", "tips", "ways to", "steps"]):
        return "educational"
    elif any(w in kw for w in ["best", "top", "list", "ranking"]):
        return "listicle"
    elif any(w in kw for w in ["what is", "why", "when", "who", "?"]):
        return "faq"
    elif any(w in kw for w in ["success", "case", "story", "result", "achieved"]):
        return "case_study"
    else:
        return "standard"


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────

def run_crew(config: CompanyConfig) -> dict:
    """
    Main entry point. Called by api.py.

    Single Groq call pipeline — fast, reliable, free tier safe.
    """

    # ── Step 1: Keyword Discovery ─────────────────────────────────────────────
    print(f"\n[Pipeline] Discovering keywords for '{config.company_name}'...")

    if config.user_query:
        print(f"[Pipeline] User query mode: '{config.user_query}'")
        raw = discover_from_input(
            config.user_query,
            company_name=config.company_name,
            niche=config.niche,
        )
    else:
        print(f"[Pipeline] Auto mode — building from company context...")
        raw = discover_all_keywords(
            company_name=config.company_name,
            niche=config.niche,
            competitors=config.competitors,
        )

    # ── Step 2: Keyword Scoring ───────────────────────────────────────────────
    analyzed = analyze_keywords(raw, brand_terms=config.brand_terms)
    if not analyzed:
        raise ValueError(
            "No suitable keywords found after filtering. "
            "All discovered keywords were off-brand topics (jobs, salaries, etc). "
            "Try a different niche or competitors."
        )
    best     = analyzed[0]
    related  = [k["keyword"] for k in analyzed[1:12]]

    print(f"[Pipeline] Best keyword: '{best['keyword']}' | score: {best['score']} | intent: {best['intent']}")

    # ── Step 3: Blog Type Selection ───────────────────────────────────────────
    # select blog type from winning keyword
    blog_type = select_blog_type(best["keyword"])

    # but if user typed a query with stronger intent signals, respect that
    if config.user_query and blog_type == "standard":
        query_blog_type = select_blog_type(config.user_query)
        if query_blog_type != "standard":
            blog_type = query_blog_type
            print(f"[Pipeline] Blog type overridden by user query: {blog_type}")
    print(f"[Pipeline] Blog type: {blog_type}")

    # ── Step 4: RAG Brand Context ─────────────────────────────────────────────
    brand_context = get_brand_context(
        vectorstore=config.vectorstore,
        keyword=best["keyword"],
        niche=config.niche,
        company_name=config.company_name,
    )
    print(f"[DEBUG] Brand context preview: {brand_context[:300] if brand_context else 'EMPTY'}")
    print(f"[Pipeline] Brand context retrieved: {'yes' if brand_context else 'no (no docs uploaded)'}")

    # ── Step 5: Blog Generation ───────────────────────────────────────────────
    print(f"[Pipeline] Generating blog...")
    blog = generate_blog(
        keyword=best["keyword"],
        intent=best["intent"],
        related=related,
        company_name=config.company_name,
        niche=config.niche,
        target_audience=config.target_audience,
        brand_context=brand_context,
        tone=config.tone,
        region=config.region,
        blog_type=blog_type,
        angle="",
    )

    meta = extract_meta(blog)

    print(f"[Pipeline] Done — blog generated for '{best['keyword']}'")

    return {
        "blog":             blog,
        "seo_title":        meta["seo_title"],
        "meta_description": meta["meta_description"],
        "slug":             meta["slug"],
        "keyword":          best["keyword"],
        "intent":           best["intent"],
        "score":            best["score"],
        "keywords_found":   len(raw),
        "blog_type":        blog_type,
        "angle":            "",
        "success":          True,
    }

# ══════════════════════════════════════════════════════════════════════════════
# CREWAI MULTI-AGENT MODE
# Uncomment and replace run_crew() with run_crew_multi_agent()
# when upgraded to Groq Dev tier (higher TPM limits)
# Requires: pip install crewai langchain-core
# ══════════════════════════════════════════════════════════════════════════════

# from crewai import Agent, Task, Crew, Process
# from langchain_core.tools import tool
#
#
# def make_agents(config: CompanyConfig) -> dict:
#     llm_model = "groq/llama-3.3-70b-versatile"
#
#     @tool("Keyword Discovery Tool")
#     def keyword_discovery_tool(company_name: str, niche: str, competitors: str) -> str:
#         """Discovers real keywords from Google autocomplete and Serper API."""
#         competitors_list = [c.strip() for c in competitors.split(",") if c.strip()]
#         raw = discover_all_keywords(company_name, niche, competitors_list)
#         brand_terms = build_brand_terms(company_name, competitors_list)
#         analyzed = analyze_keywords(raw, brand_terms=brand_terms)
#         top15 = analyzed[:15]
#         output_lines = [f"KEYWORD DISCOVERY RESULTS for {company_name}:\n"]
#         for i, k in enumerate(top15, 1):
#             output_lines.append(
#                 f"{i}. {k['keyword']}\n"
#                 f"   Intent: {k['intent']} | Score: {k['score']} | "
#                 f"Words: {k['word_count']} | Source: {k['source']}"
#             )
#         return "\n".join(output_lines)
#
#     @tool("Brand Context Tool")
#     def brand_strategy_tool(keyword: str) -> str:
#         """Retrieves relevant brand context from uploaded documents."""
#         brand_context = get_brand_context(
#             vectorstore=config.vectorstore,
#             keyword=keyword,
#             niche=config.niche,
#             company_name=config.company_name,
#         )
#         if not brand_context:
#             return f"No brand documents found for {config.company_name}."
#         return f"BRAND CONTEXT for keyword '{keyword}':\n\n{brand_context}"
#
#     keyword_agent = Agent(
#         role="SEO Keyword Research Specialist",
#         goal=f"Discover highest-value keywords for {config.company_name} in {config.niche}.",
#         backstory=f"Senior SEO analyst with 10 years experience in {config.niche}.",
#         tools=[keyword_discovery_tool],
#         verbose=False,
#         llm=llm_model,
#         allow_delegation=False,
#     )
#
#     strategy_agent = Agent(
#         role="SEO Content Strategist",
#         goal=f"Pick best keyword for {config.company_name}, decide blog type and content angle.",
#         backstory=f"Content strategy expert who helps {config.niche} brands rank on page 1.",
#         tools=[brand_strategy_tool],
#         verbose=False,
#         llm=llm_model,
#         allow_delegation=False,
#     )
#
#     return {"keyword_agent": keyword_agent, "strategy_agent": strategy_agent}
#
#
# def make_tasks(config: CompanyConfig, agents: dict) -> list:
#     task_keywords = Task(
#         description=(
#             f"Use Keyword Discovery Tool for {config.company_name}, "
#             f"niche: {config.niche}, competitors: {', '.join(config.competitors)}. "
#             f"Return top 15 scored keywords."
#         ),
#         expected_output="Ranked list of 15 keywords with intent, score, word count, source.",
#         agent=agents["keyword_agent"],
#     )
#
#     task_strategy = Task(
#         description=(
#             f"From Task 1 keywords, pick best for {config.company_name}. "
#             f"Use Brand Context Tool. Choose blog type and write content angle.\n\n"
#             f"Return EXACTLY:\n"
#             f"KEYWORD: <value>\nINTENT: <value>\nSCORE: <value>\n"
#             f"BLOG_TYPE: <listicle|comparison|educational|case_study|faq|standard>\n"
#             f"ANGLE: <one sentence>\nBRAND_CONTEXT: <retrieved context>"
#         ),
#         expected_output="Six lines: KEYWORD, INTENT, SCORE, BLOG_TYPE, ANGLE, BRAND_CONTEXT.",
#         agent=agents["strategy_agent"],
#         context=[task_keywords],
#     )
#
#     return [task_keywords, task_strategy]
#
#
# def parse_strategy_output(raw: str) -> dict:
#     import re
#     def extract(label):
#         match = re.search(rf"^{label}:\s*(.+)", raw, re.MULTILINE | re.IGNORECASE)
#         return match.group(1).strip() if match else ""
#     brand_match = re.search(r"BRAND_CONTEXT:\s*(.+)", raw, re.DOTALL | re.IGNORECASE)
#     return {
#         "keyword":       extract("KEYWORD"),
#         "intent":        extract("INTENT"),
#         "score":         int(extract("SCORE")) if extract("SCORE").isdigit() else 0,
#         "blog_type":     extract("BLOG_TYPE") or "standard",
#         "angle":         extract("ANGLE"),
#         "brand_context": brand_match.group(1).strip() if brand_match else "",
#     }
#
#
# def run_crew_multi_agent(config: CompanyConfig) -> dict:
#     agents = make_agents(config)
#     tasks  = make_tasks(config, agents)
#     crew   = Crew(
#         agents=list(agents.values()),
#         tasks=tasks,
#         process=Process.sequential,
#         verbose=False,
#     )
#     for attempt in range(3):
#         try:
#             crew_result = crew.kickoff()
#             break
#         except Exception as e:
#             error_str = str(e).lower()
#             if ("rate_limit" in error_str or "429" in error_str) and attempt < 2:
#                 print(f"[Crew] Rate limit — waiting {30 * (attempt+1)}s...")
#                 time.sleep(30 * (attempt + 1))
#             else:
#                 raise
#     raw_output = str(crew_result.raw) if hasattr(crew_result, "raw") else str(crew_result)
#     strategy   = parse_strategy_output(raw_output)
#     if not strategy["keyword"]:
#         # fallback to rule-based pipeline
#         return run_crew(config)
#     blog = generate_blog(
#         keyword=strategy["keyword"],
#         intent=strategy["intent"],
#         related=[],
#         company_name=config.company_name,
#         niche=config.niche,
#         target_audience=config.target_audience,
#         brand_context=strategy["brand_context"],
#         tone=config.tone,
#         region=config.region,
#         blog_type=strategy["blog_type"],
#         angle=strategy["angle"],
#     )
#     meta = extract_meta(blog)
#     return {
#         "blog":           blog,
#         "seo_title":      meta["seo_title"],
#         "meta_description": meta["meta_description"],
#         "slug":           meta["slug"],
#         "keyword":        strategy["keyword"],
#         "intent":         strategy["intent"],
#         "score":          strategy["score"],
#         "keywords_found": 15,
#         "blog_type":      strategy["blog_type"],
#         "angle":          strategy["angle"],
#         "success":        True,
#     }