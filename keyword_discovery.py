import requests
import datetime
import os
from dotenv import load_dotenv

load_dotenv()
SERPER_KEY = os.getenv("SERPER_API_KEY")


#SEED GENERATION 
# Instead of a hardcoded list for Times Prime, we now BUILD seeds dynamically
# from whatever company/niche the user provides.

def build_seeds(company_name: str, niche: str, competitors: list[str]) -> list[str]:
    """
    Generate seed keywords from company context.
    Previously this was a hardcoded SEED_KEYWORDS list for Times Prime.
    Now any company can use this by passing their own details.
    """
    year = datetime.datetime.now().year
    seeds = []

    # brand seeds — about this company directly
    seeds += [
        f"{company_name} benefits",
        f"{company_name} review",
        f"{company_name} offers",
        f"{company_name} discount {year}",
        f"is {company_name} worth it",
        f"{company_name} vs",
    ]

    # niche seeds — category-level searches
    seeds += [
        f"best {niche} platform india",
        f"{niche} deals india {year}",
        f"top {niche} offers india",
        f"how to save money on {niche}",
        f"best {niche} subscription india",
        f"cheapest {niche} india",
    ]

    #competitor comparison seeds — high commercial intent
    for competitor in competitors[:4]:  # cap at 4 to avoid too many API calls
        seeds += [
            f"{company_name} vs {competitor}",
            f"{competitor} discount india",
        ]

    # informational/long-tail seeds
    seeds += [
        f"how to get {niche} discount india",
        f"cashback on {niche} india",
        f"free {niche} subscription india",
        f"{niche} coupon code {year}",
    ]

    # deduplicate while preserving order
    seen = set()
    unique_seeds = []
    for s in seeds:
        if s not in seen:
            seen.add(s)
            unique_seeds.append(s)

    return unique_seeds


#  KEYWORD FETCHERS 

def get_google_suggestions(seed: str) -> list[str]:
    """Free Google autocomplete — no API key needed."""
    url = "https://suggestqueries.google.com/complete/search"
    params = {"client": "firefox", "q": seed, "hl": "en", "gl": "in"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        return r.json()[1]
    except Exception:
        return []


def get_serper_results(seed: str) -> list[str]:
    """Related searches + People Also Ask via Serper API."""
    if not SERPER_KEY:
        return []
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
    payload = {"q": seed, "gl": "in", "hl": "en", "num": 5}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        data = r.json()
        related = [item["query"] for item in data.get("relatedSearches", [])]
        people_ask = [item["question"] for item in data.get("peopleAlsoAsk", [])]
        return related + people_ask
    except Exception:
        return []


#  MAIN DISCOVERY FUNCTIONS 

def discover_all_keywords(
    company_name: str,
    niche: str,
    competitors: list[str],
) -> list[dict]:
    """
    Full keyword discovery from dynamically built seeds.
    Previously ran on hardcoded Times Prime seeds.
    Now works for any company.
    """
    seeds = build_seeds(company_name, niche, competitors)
    return _run_discovery(seeds)


def discover_from_input(
    user_query: str,
    company_name: str = "",
    niche: str = "",
) -> list[dict]:
    """
    Expand a single user search query into multiple seeds, then discover.
    Kept from original — now also mixes in company context if provided.
    """
    query = user_query.strip().lower()
    year = datetime.datetime.now().year

    seeds = [query]

    if "india" not in query:
        seeds.append(query + " india")

    if str(year) not in query:
        seeds.append(query + f" {year}")

    transactional_words = ["coupon", "discount", "offer", "deal", "promo", "code"]
    if not any(w in query for w in transactional_words):
        seeds.append(query + " discount india")
        seeds.append(query + " coupon code")

    if "best" not in query:
        seeds.append("best " + query)

    # mix in company context if available
    if company_name:
        seeds.append(f"{company_name} {query}")
    if niche:
        seeds.append(f"{niche} {query} india")

    return _run_discovery(seeds)


def _run_discovery(seeds: list[str]) -> list[dict]:
    """
    Shared runner: loops through seeds, fetches from both sources,
    deduplicates, and returns a flat list of keyword dicts.
    """
    all_keywords = []
    seen = set()

    for seed in seeds:
        for kw in get_google_suggestions(seed):
            if kw not in seen:
                seen.add(kw)
                all_keywords.append({"keyword": kw, "source": "autocomplete", "seed": seed})

        for kw in get_serper_results(seed):
            if kw not in seen:
                seen.add(kw)
                all_keywords.append({"keyword": kw, "source": "serper", "seed": seed})

    return all_keywords