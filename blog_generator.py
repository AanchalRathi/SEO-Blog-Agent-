import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# ── BLOG TEMPLATES ────────────────────────────────────────────────────────────

BLOG_STRUCTURES = {
    "listicle": """
Use EXACTLY this structure:

SEO TITLE: (under 60 chars, include primary keyword, start with a number e.g. "7 Best...")
META DESCRIPTION: (under 155 chars, keyword + clear CTA)
SLUG: (url-friendly, lowercase, hyphens only)

---BLOG START---

[H1 — matches SEO title closely, includes number]

[Introduction — 2 paragraphs]
Hook with a relatable problem or question.
Mention {company_name} naturally in second paragraph.

[H2 — Why This List Matters in {region}]
[1-2 paragraphs setting context for the list]

[H2 — The Best {topic}]
For each item use this format:
### {number}. [Item Name]
[2-3 sentences explaining why this item is on the list]
[How {company_name} connects to this item]

[H2 — How to Get the Most From {company_name}]
[2 paragraphs, practical tips, weave in related keywords]

[H2 — Frequently Asked Questions]
Q: [question using a related keyword]
A: [concise answer, 2-3 sentences]
(3 FAQs total)

[Conclusion — 1 paragraph]
Summarize the list value, clear CTA to try {company_name}.

---BLOG END---
""",

    "comparison": """
Use EXACTLY this structure:

SEO TITLE: (under 60 chars, include both things being compared)
META DESCRIPTION: (under 155 chars, keyword + clear CTA)
SLUG: (url-friendly, lowercase, hyphens only)

---BLOG START---

[H1 — matches SEO title, includes vs or comparison language]

[Introduction — 2 paragraphs]
Hook with why this comparison matters to the reader.
Mention {company_name} naturally in second paragraph.

[H2 — Quick Comparison Table]
Create a simple markdown table comparing key features:
| Feature | Option A | Option B |
|---------|----------|----------|

[H2 — Deep Dive: Option A]
[2-3 paragraphs, honest pros and cons]

[H2 — Deep Dive: Option B]
[2-3 paragraphs, honest pros and cons]

[H2 — Which One Should You Choose?]
[2 paragraphs — give a clear recommendation based on user type]
[Position {company_name} as the smarter choice with evidence]

[H2 — Frequently Asked Questions]
Q: [question using a related keyword]
A: [concise answer, 2-3 sentences]
(3 FAQs total)

[Conclusion — 1 paragraph]
Clear verdict, CTA to try {company_name}.

---BLOG END---
""",

    "educational": """
Use EXACTLY this structure:

SEO TITLE: (under 60 chars, include primary keyword, start with How or What)
META DESCRIPTION: (under 155 chars, keyword + clear CTA)
SLUG: (url-friendly, lowercase, hyphens only)

---BLOG START---

[H1 — matches SEO title closely]

[Introduction — 2 paragraphs]
Hook with why this topic matters right now.
Mention {company_name} naturally in second paragraph.

[H2 — What You Need to Know First]
[2 paragraphs — foundational context, define key terms]

[H2 — Step by Step: How to {main topic}]
Use numbered steps:
1. [Step name]
   [2-3 sentences explaining this step clearly]
(4-5 steps total)

[H2 — How {company_name} Makes This Easier]
[2 paragraphs — connect the educational topic to {company_name}'s value]

[H2 — Common Mistakes to Avoid]
[3 mistakes in short paragraphs or bullets]

[H2 — Frequently Asked Questions]
Q: [question using a related keyword]
A: [concise answer, 2-3 sentences]
(3 FAQs total)

[Conclusion — 1 paragraph]
Summarize key learnings, CTA to try {company_name}.

---BLOG END---
""",

    "case_study": """
Use EXACTLY this structure:

SEO TITLE: (under 60 chars, include company name and result)
META DESCRIPTION: (under 155 chars, keyword + clear CTA)
SLUG: (url-friendly, lowercase, hyphens only)

---BLOG START---

[H1 — matches SEO title, focuses on the result/transformation]

[Introduction — 2 paragraphs]
Hook with the problem that was solved.
Introduce {company_name} as the solution naturally.

[H2 — The Challenge]
[2 paragraphs — describe the problem in detail that readers relate to]

[H2 — How {company_name} Helped]
[2-3 paragraphs — specific features or offers that solved the problem]

[H2 — The Results]
[2 paragraphs — concrete outcomes, use numbers where possible]

[H2 — Key Takeaways]
List 3-4 takeaways in this format:
- [Takeaway]: [one sentence explanation]

[H2 — Frequently Asked Questions]
Q: [question using a related keyword]
A: [concise answer, 2-3 sentences]
(3 FAQs total)

[Conclusion — 1 paragraph]
Reinforce the transformation, CTA to try {company_name}.

---BLOG END---
""",

    "faq": """
Use EXACTLY this structure:

SEO TITLE: (under 60 chars, include primary keyword as a question)
META DESCRIPTION: (under 155 chars, keyword + clear CTA)
SLUG: (url-friendly, lowercase, hyphens only)

---BLOG START---

[H1 — matches SEO title, phrased as a question]

[Introduction — 2 paragraphs]
Hook with why people ask this question.
Mention {company_name} naturally in second paragraph.

[H2 — The Short Answer]
[1 paragraph — direct answer to the main question]

[H2 — The Full Explanation]
[2-3 paragraphs — detailed answer with context]

[H2 — {company_name} and {main topic}: What You Need to Know]
[2 paragraphs — connect the answer to {company_name}'s offering]

[H2 — Related Questions People Also Ask]
Q: [related question 1]
A: [2-3 sentence answer]

Q: [related question 2]
A: [2-3 sentence answer]

Q: [related question 3]
A: [2-3 sentence answer]

Q: [related question 4]
A: [2-3 sentence answer]

Q: [related question 5]
A: [2-3 sentence answer]

[Conclusion — 1 paragraph]
Summarize the answer, CTA to try {company_name}.

---BLOG END---
""",

    "standard": """
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
Summarize value, clear CTA to try {company_name}.

---BLOG END---
""",
}


# ── PROMPT BUILDER ────────────────────────────────────────────────────────────

def build_prompt(
    keyword: str,
    intent: str,
    related: list[str],
    company_name: str,
    niche: str,
    target_audience: str,
    brand_context: str = "",
    tone: str = "conversational",
    region: str = "India",
    blog_type: str = "standard",
    angle: str = "",
) -> str:
    lsi = ", ".join(related[:8]) if related else ""
    year = 2026

    structure = BLOG_STRUCTURES.get(blog_type, BLOG_STRUCTURES["standard"])
    structure = structure.replace("{company_name}", company_name)
    structure = structure.replace("{region}", region)

    brand_context_block = ""
    if brand_context.strip():
        brand_context_block = f"""
BRAND CONTEXT (use this to stay accurate and on-brand — do not invent 
details not present here):
\"\"\"
{brand_context.strip()}
\"\"\"
"""

    angle_block = ""
    if angle.strip():
        angle_block = f"""
CONTENT ANGLE (what makes this post better than competitors):
{angle.strip()}
"""

    lsi_block = ""
    if lsi:
        lsi_block = f"Related keywords to include naturally: {lsi}\n"

    prompt = f"""You are an expert SEO content writer specializing in {niche}.
You are writing for {company_name} — {target_audience}.
Tone: {tone}. Target region: {region}. Year: {year}.
{brand_context_block}
{angle_block}
Write a complete SEO-optimized blog post for:
Primary keyword : {keyword}
Search intent   : {intent}
{lsi_block}
{structure}

Length: 900-1100 words.
Use keywords naturally — never stuff.
Write for a {region} audience in {year}.
{tone.capitalize()} but authoritative tone.
If brand context is provided, use real product details, pricing, and USPs from it.
Never invent features, prices, or offers not listed in the brand context.
Return ONLY the blog content starting from SEO TITLE — no preamble, 
no commentary, no explanation before or after."""

    return prompt


# ── MAIN GENERATOR ────────────────────────────────────────────────────────────

def generate_blog(
    keyword: str,
    intent: str,
    related: list[str],
    company_name: str,
    niche: str,
    target_audience: str,
    brand_context: str = "",
    tone: str = "conversational",
    region: str = "India",
    blog_type: str = "standard",
    angle: str = "",
) -> str:
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
        blog_type=blog_type,
        angle=angle,
    )
    try: 
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=2000,
                temperature=0.7,
            )
        )
        return response.text
    except Exception as e:
        print(f"[Gemini] Generation failed: {e}")
        raise


# ── META EXTRACTOR ────────────────────────────────────────────────────────────

def extract_meta(blog_output: str) -> dict:
    import re

    def extract(pattern: str) -> str:
        match = re.search(pattern, blog_output, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return {
        "seo_title":        extract(r"SEO TITLE:\s*(.+)"),
        "meta_description": extract(r"META DESCRIPTION:\s*(.+)"),
        "slug":             extract(r"SLUG:\s*(.+)"),
    }