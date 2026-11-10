# Scholarship & Opportunity Tracker

Students miss scholarships because deadlines, eligibility rules and document lists are buried in long announcements.
Paste an announcement → the app extracts the details, scores your **fit**, builds a **document checklist**, and tells you **what to work on first**.

## The "10x" feature
Each opportunity gets an explainable **Fit Score** (degree, field, nationality, GPA vs. your profile) and a **Readiness** %
(checklist progress). `/dashboard` ranks everything by `priority = fit + urgency, discounted by readiness` and gives a **next action**.

## Concepts covered
| Concept | Where |
|---|---|
| API endpoints | `app/main.py` (FastAPI) |
| Database | `app/models.py` (SQLite + SQLAlchemy) |
| Authentication | `app/auth.py` (PBKDF2 + JWT) |
| Cron jobs | `app/jobs.py` (daily reminders at 7/3/1 days, weekly digest) |
| Email reporting | `app/jobs.py` (SMTP, console fallback) |
| Caching | `app/llm.py` (content-hash cache, 24h TTL) |
| LLM integration | `app/llm.py` (Groq/Gemini free tier, regex fallback) |

## Run
```bash
pip install -r requirements.txt "pydantic[email]"
cp .env.example .env   # add a free LLM key (optional)
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload     # docs at http://127.0.0.1:8000/docs
```
Flow: `POST /auth/register` → `PUT /me` (profile) → `POST /opportunities` {"text": "..."} → `GET /dashboard`.
Use `POST /digest/send-now` to demo the email without waiting for Monday.

## Ideas to extend
Telegram reminders, PDF weekly report, Urdu announcement support, RAG over past awards.
