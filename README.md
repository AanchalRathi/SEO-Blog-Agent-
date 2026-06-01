# AI-powered SEO Agent

An AI-powered SEO content agent that discovers high-value keywords 
from live Google search data, scores them by business intent, and 
auto-generates publish-ready SEO blogs using LLM generation with 
built-in quality evaluation.

## What it does
- Phase 1: Mines real-time keywords from Google autocomplete + related searches
- Phase 2: Scores and classifies keywords by search intent (transactional / informational / commercial)
- Phase 3: Generates a full SEO blog (900-1100 words) targeting the highest-value keyword
- Phase 4: Self-evaluates blog quality using LLM-as-judge pattern

## Tech stack
- Groq API (Llama 3.3 70B) — LLM inference
- Serper.dev — Google SERP data
- Python — core pipeline
- Rich — terminal UI

---

## Setup
1. Clone the repo
2. pip install -r requirements.txt
3. Copy .env.example to .env and add your API keys
4. python agent.py

---

## Sample output
<img width="1302" height="877" alt="image" src="https://github.com/user-attachments/assets/f1cef38d-8f2b-41e2-a29e-05a625426148" />
<img width="1290" height="886" alt="image" src="https://github.com/user-attachments/assets/9361f51d-92ed-4aca-9e2f-4793da1e773f" />
<img width="1281" height="878" alt="image" src="https://github.com/user-attachments/assets/ab75db5f-852b-41c5-815f-d70cf869ebbb" />

---

## Why this matters
Businesses spend huge time and money researching keywords, planning content, and writing SEO blogs manually. This agent automates the entire workflow — from keyword discovery to content generation — helping teams scale organic traffic faster while reducing content production cost and effort.

It also prioritizes high-intent keywords, making the generated content more aligned with real user search behavior and potential business conversions.
