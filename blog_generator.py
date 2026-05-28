import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_blog(keyword: str, intent: str, related: list[str]) -> str:
    lsi = ", ".join(related[:8])

    prompt = f"""You are an SEO content writer for Times Prime — India's premium membership platform 
giving users the best deals, coupon codes and subscriptions (Zomato, Swiggy, Hotstar, Amazon etc).

Write a complete SEO blog post for:
Primary keyword: {keyword}
Search intent: {intent}
Related keywords to include naturally: {lsi}

Use EXACTLY this structure:

SEO TITLE: (under 60 chars, keyword included)
META DESCRIPTION: (under 155 chars, keyword + CTA)
SLUG: (url-friendly)

---BLOG START---

[H1]
[2 paragraph intro — hook the reader, mention Times Prime naturally]

[H2 — Section 1]
[content]

[H2 — Section 2]
[content]

[H2 — Top Times Prime Deals Right Now]
List 3 deals in this format:
-DEAL: [name]
-SAVINGS: [amount or %]
-HOW TO CLAIM: Available on Times Prime app

[H2 — Frequently Asked Questions]
Q: [question]
A: [answer]
(3 FAQs)

[Conclusion — 1 paragraph with CTA to download Times Prime]

---BLOG END---

Length: 900-1100 words. Natural keyword use. Conversational tone. Indian audience."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", #using meta's Llama LLM
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.7,
    )
    return response.choices[0].message.content
