import requests
import os
from dotenv import load_dotenv

load_dotenv()
SERPER_KEY = os.getenv("SERPER_API_KEY")

# These are your seed topics — what Times Prime is about
SEED_KEYWORDS = [

    "times prime membership",       
    "times prime benefits",            
    "times prime coupon code",         
    "times prime vs cash karo", 
    "times prime vs coupon dunia",
    "times prime vs grab on",    
    "zomato gold vs swiggy one",   
    "best membership app india",

    "zomato gold coupon",             
    "swiggy one membership discount", 
    "amazon prime discount india",   
    "hotstar subscription offer",     
    "myntra insider benefits",       

    "best subscription deals india", 
    "how to save money on food delivery india", 
    "cashback offers india 2025",     
    "free ott subscription india",

    "ipl streaming discount 2025",   
    "diwali offers membership india", 

]

def get_google_suggestions(seed:str)->list[str]:
    """Free Google autocomplete API endpoint(no api key)"""
    url= "https://suggestqueries.google.com/complete/search"
    params= {"client": "firefox", "q": seed, "hl": "en", "gl": "in"}
    headers= {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        suggestions = r.json()[1] #[0] is original query,[1]is list of suggestions
        return suggestions
    except:
        return []

def get_serper_results(seed: str) -> list[str]:
    """Get related searches from Google via Serper."""
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"}
    payload = {"q": seed, "gl": "in", "hl": "en", "num": 5}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        data = r.json()
        related = [item["query"] for item in data.get("relatedSearches", [])]
        people_ask = [item["question"] for item in data.get("peopleAlsoAsk", [])]
        return related + people_ask
    except:
        return []

def discover_all_keywords() -> list[dict]:
    all_keywords = []
    seen = set()#no duplicates,almost instant instaed of list 

    for seed in SEED_KEYWORDS:#loops through all seed keywords
        #Source 1:free google autocomplete
        for kw in get_google_suggestions(seed):
            if kw not in seen:
                seen.add(kw)
                all_keywords.append({"keyword": kw, "source": "autocomplete", "seed": seed})

        #source 2:serper related searches + people also ask
        for kw in get_serper_results(seed):
            if kw not in seen:
                seen.add(kw)
                all_keywords.append({"keyword": kw, "source": "serper", "seed": seed})

    return all_keywords