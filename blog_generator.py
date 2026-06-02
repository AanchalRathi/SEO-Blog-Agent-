import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


#PROMPT BUILDER 

def build_prompt(
    keyword: str,
    intent: str,
    related: list[str],
    company_name: str,
    niche: str,
    target_audience: str,
    brand_context: str = "",       # RAG-retrieved brand context
    tone: str = "conversational",
    region: str = "India",
) -> str:
    """
    Builds the full blog generation prompt dynamically.

    Previously this was hardcoded inside generate_blog() with
    Times Prime details baked in. Now every company-specific
    detail is a parameter — the prompt structure stays the same.

    brand_context is the RAG chunk (empty string until Step 4 adds it).
    """
    lsi = ", ".join(related[:8])
    year = 2026  # can also pass as param if needed

    # only include brand context block if RAG has provided something
    brand_context_block = ""
    if brand_context.strip():
        brand_context_block = f"""
BRAND CONTEXT (use this to stay accurate and on-brand):
\"\"\"
{brand_context.strip()}
\"\"\"
"""

    prompt = f"""You are an expert SEO content writer specializing in {niche}.
You are writing for {company_name} — {target_audience}.
Tone: {tone}. Target region: {region}.
{brand_context_block}
Write a complete SEO-optimized blog post for:
Primary keyword : {keyword}
Search intent   : {intent}
Related keywords to include naturally: {lsi}

Use EXACTLY this structure:

SEO TITLE: (under 60 chars, include primary keyword)
META DESCRIPTION: (under 155 chars, keyword + clear CTA)
SLUG: (url-friendly, lowercase, hyphens only)

---BLOG START---

[H1 — matches SEO title closely]

[Introduction — 2 paragraphs]
Hook the reader with a relatable problem or question.
Mention {company_name} naturally in the second paragraph.

[H2 — Section 1: explain the main topic]
[2-3 paragraphs of useful content]

[H2 — Section 2: how {company_name} helps with this]
[2-3 paragraphs, weave in primary + related keywords naturally]

[H2 — Top {company_name} Offers Right Now]
List 3 current offers or features in this format:
- OFFER: [name or feature]
- BENEFIT: [what the user gets]
- HOW TO ACCESS: [short instruction]

[H2 — Frequently Asked Questions]
Q: [question using a related keyword]
A: [concise answer, 2-3 sentences]
(3 FAQs total)

[Conclusion — 1 paragraph]
Summarize value, include a clear CTA to try or visit {company_name}.

---BLOG END---

Length: 900-1100 words.
Use keywords naturally — never stuff.
Write for a {region} audience in {year}.
Conversational but authoritative tone."""

    return prompt


# MAIN GENERATOR 

def generate_blog(
    keyword: str,
    intent: str,
    related: list[str],
    company_name: str,
    niche: str,
    target_audience: str,
    brand_context: str = "",       #injected by RAG in Step 4, empty for now
    tone: str = "conversational",
    region: str = "India",
) -> str:
    """
    Generates a full SEO blog post using Groq + Llama 3.3.

    Previously accepted only keyword, intent, related —
    all company context was hardcoded in the prompt.
    Now accepts full company config and optional RAG context.

    brand_context stays an empty string until rag_tool.py is wired in (Step 4).
    The function works perfectly without it — RAG just makes it better.
    """
    prompt = build_prompt(
        keyword=keyword,
        intent=intent,
        related=related,
        company_name=company_name,
        niche=niche,
        target_audience=target_audience,
        brand_context=brand_context,
        tone=tone,
        region=region,
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.7,
    )

    return response.choices[0].message.content


# META GENERATOR 
# NEW — extracts SEO title, meta description, slug from the blog output
# so main.py and the API can use them separately without parsing manually

def extract_meta(blog_output: str) -> dict:
    """
    Parses the structured blog output and returns meta fields as a dict.
    Returns empty strings if a field is not found.
    """
    import re

    def extract(pattern: str) -> str:
        match = re.search(pattern, blog_output, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return {
        "seo_title":        extract(r"SEO TITLE:\s*(.+)"),
        "meta_description": extract(r"META DESCRIPTION:\s*(.+)"),
        "slug":             extract(r"SLUG:\s*(.+)"),
    }