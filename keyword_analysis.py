import re
import datetime

#intent signals
#these stay the same — they are universal across any niche

TRANSACTIONAL = [
    "coupon", "promo code", "discount", "offer", "deal",
    "cashback", "free trial", "voucher", "redeem", "code today",
    "buy", "get", "claim", "subscribe", "sign up"
]

INFORMATIONAL = [
    "what is", "how to", "why", "guide", "review",
    "explained", "worth it", "vs", "compare", "best", "top",
    "difference between", "should i", "is it"
]

# Keywords about these topics should never become blog content for a brand —
# wrong audience (job seekers, not customers) and high risk of hallucinated
# salary/employment data since brand docs never cover this.
EXCLUDE_TOPICS = [
    "salary", "delivery boy", "delivery partner", "delivery job",
    "job", "career", "hiring", "vacancy", "recruitment",
    "income", "earn money", "how much do", "pay scale",
    "joining", "work for", "become a delivery"
    # exclude financial topic that is not customer-facing content
    "profit", "loss", "revenue", "share price", "shares", "stock",
    "ipo", "valuation", "funding", "investor", "quarterly results",
    "net worth", "market cap"
]

#intent classifier

def classify_intent(keyword: str) -> str:
    """
    Same logic as before — counts transactional vs informational signals.
    No change needed here since intent words are universal.
    """
    kw = keyword.lower()
    t = sum(1 for s in TRANSACTIONAL if s in kw)
    i = sum(1 for s in INFORMATIONAL if s in kw)
    if t > i:
        return "transactional"
    if i > t:
        return "informational"
    return "commercial"


# scrorer

def score_keyword(kw_dict: dict, brand_terms: list[str] = None) -> dict | None:
    kw = kw_dict["keyword"].lower()

    # exclude off-brand topics entirely — return None to signal "skip this keyword", checked
    if any(topic in kw for topic in EXCLUDE_TOPICS):
        return None
    
    kw = kw_dict["keyword"].lower()
    intent = classify_intent(kw)
    score = 40  # base score

    #intent bonus —same as original
    if intent == "transactional":
        score += 30
    elif intent == "commercial":
        score += 15

    # penalize pure coupon hunting keywords — low editorial value, repeatedly wins otherwise
    if any(w in kw for w in ["coupon code", "promo code", "offers today code", "discount code"]):
        score -= 25
    #brand relevance bonus —now dynamic instead of hardcoded
    if brand_terms:
        if any(b.lower() in kw for b in brand_terms):
            score += 15

    #long-tail bonus — easier to rank, same logic as original
    word_count = len(kw.split())
    if word_count >= 4:
        score += 10
    if word_count >= 6:
        score += 5   #additive on top of >=4 bonus

    #recency/urgency bonus— same as original
    year = datetime.datetime.now().year
    #match current year and next two years, plus time-sensitive words
    if re.search(rf"{year}|{year+1}|today|this month|this week", kw):
        score += 10

    return {
        "keyword":    kw_dict["keyword"],
        "intent":     intent,
        "score":      min(score, 100),
        "word_count": word_count,
        "source":     kw_dict["source"],
        "seed":       kw_dict["seed"],
    }
# batch analyser

def analyze_keywords(raw: list[dict],brand_terms: list[str] = None,) -> list[dict]:
    """
    Scores and sorts all discovered keywords.

    brand_terms — pass in a flat list of:
        - company name          e.g. "times prime"
        - competitor names      e.g. "amazon prime", "zomato gold"
        - product/partner names e.g. "hotstar", "swiggy one"

    If nothing is passed, brand bonus is simply skipped —
    so this works even with zero brand context.

    Example call:
        analyze_keywords(raw, brand_terms=["acme corp", "rivalco", "partnerx"])
    """
    scored = [score_keyword(k, brand_terms=brand_terms) for k in raw]
    scored = [s for s in scored if s is not None] #to filter out excludded keywords 
    return sorted(scored, key=lambda x: x["score"], reverse=True)


#helper function:build brand_terms from company config

def build_brand_terms(
    company_name: str,
    competitors: list[str],
    extra_terms: list[str] = None,
) -> list[str]:
    """
    Convenience function to assemble the brand_terms list
    from the company config collected in main.py.

    company_name  — the brand itself
    competitors   — rival brands (already high commercial intent)
    extra_terms   — any partner/product names the company wants to target
    """
    terms = [company_name] + competitors
    if extra_terms:
        terms += extra_terms

    # lowercase and deduplicate
    seen = set()
    clean = []
    for t in terms:
        t_lower = t.strip().lower()
        if t_lower and t_lower not in seen:
            seen.add(t_lower)
            clean.append(t_lower)

    return clean