"""LLM extraction with a content-hash cache and a regex fallback (works with no API key)."""
import os, re, json, time, hashlib, datetime as dt
import httpx
from dateutil import parser as dparser

_CACHE: dict[str, tuple[float, dict]] = {}
TTL = 24 * 3600

PROMPT = """Extract opportunity info from the announcement. Reply with JSON only, keys:
title, organization, deadline (YYYY-MM-DD or null), min_gpa (number on 4.0 scale or null),
degree_levels (subset of bachelors, masters, phd; [] if any), fields (study fields; [] if any),
countries (eligible nationalities; [] if any), eligibility_notes (short strings),
documents (required documents). Today is {today}."""

DOC_WORDS = ["transcript", "cv", "resume", "passport", "cnic", "statement of purpose", "personal statement",
             "essay", "recommendation letter", "reference letter", "english test", "ielts", "toefl",
             "research proposal", "degree certificate", "photograph"]

def _fallback(text: str) -> dict:
    low = text.lower()
    deadline = None
    for line in text.splitlines():
        if re.search(r"deadline|apply by|last date|closes", line, re.I):
            try: deadline = dparser.parse(line, fuzzy=True).date().isoformat(); break
            except Exception: pass
    gpa = re.search(r"(?:gpa|cgpa)[^0-9]{0,15}(\d(?:\.\d+)?)", low)
    levels = [l for l, k in [("bachelors", "bachelor"), ("masters", "master"), ("phd", "phd")] if k in low]
    first = next((l.strip() for l in text.splitlines() if l.strip()), "Untitled opportunity")
    return {"title": first[:120], "organization": "", "deadline": deadline,
            "min_gpa": float(gpa.group(1)) if gpa else None, "degree_levels": levels,
            "fields": [], "countries": [], "eligibility_notes": [],
            "documents": [(w.upper() if len(w) <= 5 else w.title()) for w in DOC_WORDS if w in low]}

def extract(text: str) -> dict:
    key = hashlib.sha256(text.strip().encode()).hexdigest()
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    data = None
    if os.getenv("LLM_API_KEY"):
        try:
            r = httpx.post(
                os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1") + "/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}"},
                json={"model": os.getenv("LLM_MODEL", "llama-3.1-8b-instant"), "temperature": 0,
                      "messages": [{"role": "system", "content": PROMPT.format(today=dt.date.today())},
                                   {"role": "user", "content": text[:8000]}]},
                timeout=30)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
            data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        except Exception as e:
            print(f"[LLM ERROR] {type(e).__name__}: {e}")
    else:
        print("[LLM] no LLM_API_KEY set in this terminal")
    if not data:
        print("[LLM] using regex fallback")
        return _fallback(text)
    _CACHE[key] = (time.time(), data)
    return data
