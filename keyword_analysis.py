import re #regular expressions,lets you search patterns inside strings

#high value searches
TRANSACTIONAL = ["coupon", "promo code", "discount", "offer", "deal",
                 "cashback", "free trial", "voucher", "redeem", "code today"]
#research words
INFORMATIONAL = ["what is", "how to", "why", "guide", "review",
                 "explained", "worth it", "vs", "compare", "best", "top"]
BRANDS = ["times prime", "amazon prime", "zomato gold", "swiggy one","cult","sony liv","uber","pvr inox","dicovery plus","lenskart",
          "hotstar", "jiocinema", "tata neu", "myntra insider","netmeds","crunchyroll","apollo","yatra","muscleblaze","flipkart","make my trip"]

def classify_intent(keyword: str) -> str:
    kw = keyword.lower()
    t = sum(1 for s in TRANSACTIONAL if s in kw)
    i = sum(1 for s in INFORMATIONAL if s in kw)
    if t > i: return "transactional"
    if i > t: return "informational"
    return "commercial"

def score_keyword(kw_dict: dict) -> dict:
    kw = kw_dict["keyword"].lower()
    intent = classify_intent(kw)
    score = 40

    if intent == "transactional": score += 30
    elif intent == "commercial":  score += 15

    if any(b in kw for b in BRANDS): score += 15
    if len(kw.split()) >= 4:         score += 10 #easier to rank as they are specific 
    if len(kw.split()) >= 6:         score += 5 #add on >4 len
    if re.search(r"202[6-9]|today|this month", kw): score += 10#time specific , urgent 

    return {
        "keyword":        kw_dict["keyword"],
        "intent":         intent,
        "score":          min(score, 100),
        "word_count":     len(kw_dict["keyword"].split()),
        "source":         kw_dict["source"],
        "seed":           kw_dict["seed"],
    }

def analyze_keywords(raw: list[dict]) -> list[dict]:
    scored = [score_keyword(k) for k in raw]
    return sorted(scored, key=lambda x: x["score"], reverse=True)#keywords sorted by best to worst