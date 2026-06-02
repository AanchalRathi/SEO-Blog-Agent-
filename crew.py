"""
crew.py — CrewAI orchestration layer

What this does:
    Wraps the existing 3-phase pipeline into CrewAI agents that
    collaborate sequentially. Each agent owns one phase and passes
    its output as context to the next agent.

Why CrewAI instead of just calling functions directly:
    - Each agent has a ROLE, GOAL, and BACKSTORY — this shapes how
      the LLM reasons inside that agent's task, producing better output
    - Agents can use TOOLS (Serper search, RAG retrieval) autonomously
    - The crew can be extended later — add a Social Media agent,
      Email Newsletter agent etc. with zero changes to existing agents
    - Output is structured and auditable — each agent's result is logged

Agent pipeline (sequential):
    1. Keyword Research Agent   → discovers + scores keywords
    2. SEO Strategy Agent       → picks best keyword, plans content angle
    3. Blog Writer Agent        → writes the full SEO blog post

Install:
    pip install crewai crewai-tools
"""

import os
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool

from keyword_discovery import discover_all_keywords, discover_from_input
from keyword_analysis import analyze_keywords, build_brand_terms
from blog_generator import generate_blog, extract_meta
from tools.rag_tool import setup_rag, get_brand_context

load_dotenv()

# ── TOOLS ─────────────────────────────────────────────────────────────────────

search_tool = SerperDevTool()   # gives agents live Google search capability


# ── COMPANY CONFIG ────────────────────────────────────────────────────────────

class CompanyConfig:
    """
    Single object that holds everything about the company.
    Passed into the crew so all agents share the same context.
    Built from user input in main.py or api.py.
    """
    def __init__(
        self,
        company_name: str,
        niche: str,
        target_audience: str,
        competitors: list[str],
        docs_path: str = "brand_docs/",
        tone: str = "conversational",
        region: str = "India",
        user_query: str = "",          # optional — if user typed a search query
    ):
        self.company_name    = company_name
        self.niche           = niche
        self.target_audience = target_audience
        self.competitors     = competitors
        self.docs_path       = docs_path
        self.tone            = tone
        self.region          = region
        self.user_query      = user_query

        # Build brand terms for keyword scoring
        self.brand_terms = build_brand_terms(company_name, competitors)

        # Setup RAG vectorstore at init time
        # If brand_docs/ is empty or missing → vectorstore is None → graceful skip
        print(f"\n[Crew] Setting up RAG for '{company_name}'...")
        self.vectorstore = setup_rag(docs_path, company_name)


# ── AGENTS ────────────────────────────────────────────────────────────────────

def make_agents(config: CompanyConfig) -> dict:
    """
    Creates the three core agents.
    Each agent is given a specific role so the LLM reasons
    within that frame — this produces more focused output
    than a single general-purpose prompt.
    """

    keyword_agent = Agent(
        role="SEO Keyword Research Specialist",
        goal=(
            f"Discover the highest-value keywords for {config.company_name} "
            f"in the {config.niche} space that will drive organic traffic "
            f"from {config.target_audience}."
        ),
        backstory=(
            f"You are a senior SEO analyst with 10 years of experience in "
            f"the {config.niche} industry. You know exactly which keywords "
            f"drive conversions vs just traffic, and you understand the "
            f"{config.region} market deeply."
        ),
        tools=[search_tool],
        verbose=True,
        allow_delegation=False,
    )

    strategy_agent = Agent(
        role="SEO Content Strategist",
        goal=(
            f"Analyse discovered keywords and select the single best keyword "
            f"for {config.company_name} to target, then plan the content angle "
            f"that will outrank competitors: {', '.join(config.competitors)}."
        ),
        backstory=(
            f"You are a content strategy expert who has helped dozens of "
            f"{config.niche} brands dominate Google's first page. You understand "
            f"search intent deeply and know how to position content to beat "
            f"established competitors."
        ),
        tools=[search_tool],
        verbose=True,
        allow_delegation=False,
    )

    writer_agent = Agent(
        role="SEO Blog Writer",
        goal=(
            f"Write a complete, SEO-optimized, brand-accurate blog post for "
            f"{config.company_name} that ranks for the target keyword and "
            f"converts {config.target_audience} into users."
        ),
        backstory=(
            f"You are an expert SEO content writer who specializes in the "
            f"{config.niche} space. You write in a {config.tone} tone, "
            f"naturally weave in keywords, and always reflect the brand's "
            f"voice accurately. Your blogs consistently rank on page 1."
        ),
        verbose=True,
        allow_delegation=False,
    )

    return {
        "keyword_agent":  keyword_agent,
        "strategy_agent": strategy_agent,
        "writer_agent":   writer_agent,
    }


# ── TASKS ─────────────────────────────────────────────────────────────────────

def make_tasks(config: CompanyConfig, agents: dict) -> list[Task]:
    """
    Defines what each agent must produce.
    context= chains tasks — each agent sees the previous agent's output.
    """

    # ── Task 1: Keyword Discovery + Scoring ───────────────────────────────────
    task_keywords = Task(
        description=(
            f"Discover and score SEO keywords for {config.company_name}.\n\n"
            f"Company     : {config.company_name}\n"
            f"Niche       : {config.niche}\n"
            f"Audience    : {config.target_audience}\n"
            f"Competitors : {', '.join(config.competitors)}\n"
            f"Region      : {config.region}\n\n"
            f"Steps:\n"
            f"1. Run keyword discovery using Google autocomplete and Serper\n"
            f"2. Score each keyword by intent, brand relevance, and long-tail value\n"
            f"3. Return the top 15 keywords as a structured list with intent and score"
        ),
        expected_output=(
            "A ranked list of 15 keywords, each with: keyword text, "
            "search intent (transactional/informational/commercial), "
            "score (0-100), and source."
        ),
        agent=agents["keyword_agent"],
    )

    # ── Task 2: Strategy — pick best keyword + plan angle ─────────────────────
    task_strategy = Task(
        description=(
            f"Analyse the keyword list from Task 1 and produce a content strategy.\n\n"
            f"Select the single best keyword for {config.company_name} to target "
            f"based on intent, score, and competitive opportunity.\n\n"
            f"Then plan:\n"
            f"- The content angle (what makes this post better than competitors)\n"
            f"- 8 related/LSI keywords to weave in naturally\n"
            f"- The recommended H2 structure (section headings)\n"
            f"- Why this keyword beats the alternatives"
        ),
        expected_output=(
            "A content brief containing: chosen keyword, intent, score, "
            "content angle, 8 LSI keywords, recommended H2 headings, "
            "and justification for the choice."
        ),
        agent=agents["strategy_agent"],
        context=[task_keywords],   # sees Task 1 output
    )

    # ── Task 3: Blog Writing ──────────────────────────────────────────────────
    # RAG context is retrieved here — just before writing starts
    # so it's always fresh and keyword-specific

    task_write = Task(
        description=(
            f"Write a complete SEO blog post using the strategy from Task 2.\n\n"
            f"Company         : {config.company_name}\n"
            f"Niche           : {config.niche}\n"
            f"Audience        : {config.target_audience}\n"
            f"Tone            : {config.tone}\n"
            f"Region          : {config.region}\n\n"
            f"Requirements:\n"
            f"- Follow the EXACT blog structure from blog_generator.py\n"
            f"- Include SEO TITLE, META DESCRIPTION, SLUG at the top\n"
            f"- 900-1100 words, natural keyword usage\n"
            f"- Use the brand context provided to stay accurate and on-brand\n"
            f"- Include H2 sections, 3 offers/features, 3 FAQs, CTA conclusion"
        ),
        expected_output=(
            "A complete blog post with SEO TITLE, META DESCRIPTION, SLUG, "
            "and full blog content between ---BLOG START--- and ---BLOG END--- markers. "
            "900-1100 words."
        ),
        agent=agents["writer_agent"],
        context=[task_strategy],   # sees Task 2 output
    )

    return [task_keywords, task_strategy, task_write]


# ── CREW RUNNER ───────────────────────────────────────────────────────────────

def run_crew(config: CompanyConfig) -> dict:
    """
    Main entry point. Called by main.py and api.py.

    1. Discovers keywords using existing pipeline functions
    2. Retrieves RAG brand context for the best keyword
    3. Builds agents + tasks
    4. Runs CrewAI sequential crew
    5. Returns structured result dict

    Returns:
        {
            "blog":             full blog post string,
            "seo_title":        extracted title,
            "meta_description": extracted meta,
            "slug":             extracted slug,
            "keyword":          best keyword used,
            "intent":           keyword intent,
            "score":            keyword score,
            "keywords_found":   total discovered,
        }
    """

    # ── Step A: Keyword discovery (your existing functions) ───────────────────
    print(f"\n[Crew] Running keyword discovery for '{config.company_name}'...")

    if config.user_query:
        raw = discover_from_input(
            config.user_query,
            company_name=config.company_name,
            niche=config.niche,
        )
    else:
        raw = discover_all_keywords(
            company_name=config.company_name,
            niche=config.niche,
            competitors=config.competitors,
        )

    analyzed = analyze_keywords(raw, brand_terms=config.brand_terms)
    best     = analyzed[0]
    related  = [k["keyword"] for k in analyzed[1:12]]

    print(f"[Crew] Best keyword: '{best['keyword']}' (score: {best['score']})")

    # ── Step B: RAG retrieval ─────────────────────────────────────────────────
    brand_context = get_brand_context(
        vectorstore=config.vectorstore,
        keyword=best["keyword"],
        niche=config.niche,
        company_name=config.company_name,
    )

    # ── Step C: Build and run the crew ────────────────────────────────────────
    agents = make_agents(config)
    tasks  = make_tasks(config, agents)

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,   # keyword → strategy → write, in order
        verbose=True,
    )

    print(f"\n[Crew] Starting CrewAI pipeline...\n")
    crew_result = crew.kickoff()

    # ── Step D: Generate final blog via blog_generator (uses RAG context) ─────
    # CrewAI handles strategy + reasoning; blog_generator handles
    # the structured prompt + Groq API call with brand context injected
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
    )

    meta = extract_meta(blog)

    return {
        "blog":             blog,
        "seo_title":        meta["seo_title"],
        "meta_description": meta["meta_description"],
        "slug":             meta["slug"],
        "keyword":          best["keyword"],
        "intent":           best["intent"],
        "score":            best["score"],
        "keywords_found":   len(raw),
        "crew_log":         str(crew_result),
    }