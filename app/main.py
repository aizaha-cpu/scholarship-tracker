import datetime as dt
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from . import jobs, llm
from .auth import hash_pw, verify_pw, make_token, current_user
from .models import Base, engine, get_db, User, Opportunity, DocItem
from .services import opp_view, dashboard

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    sched = jobs.start()
    yield
    sched.shutdown()

app = FastAPI(title="Scholarship & Opportunity Tracker", lifespan=lifespan)

class Creds(BaseModel):
    email: str
    password: str
class Profile(BaseModel):
    full_name: str = ""; degree_level: str = ""; field: str = ""; gpa: float | None = None; country: str = ""
class NewOpp(BaseModel):
    text: str
class StatusIn(BaseModel):
    status: str  # saved/applied/won/rejected

@app.post("/auth/register", status_code=201)
def register(c: Creds, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=c.email.lower()).first(): raise HTTPException(409, "Email already registered")
    u = User(email=c.email.lower(), password=hash_pw(c.password)); db.add(u); db.commit()
    return {"token": make_token(u.id)}

@app.post("/auth/login")
def login(c: Creds, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=c.email.lower()).first()
    if not u or not verify_pw(c.password, u.password): raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(u.id)}

@app.get("/me")
def me(u: User = Depends(current_user)):
    return {"email": u.email, "full_name": u.full_name, "degree_level": u.degree_level, "field": u.field, "gpa": u.gpa, "country": u.country}

@app.put("/me")
def update_me(p: Profile, u: User = Depends(current_user), db: Session = Depends(get_db)):
    for k, v in p.model_dump().items(): setattr(u, k, v)
    db.commit(); return {"ok": True}

@app.post("/opportunities", status_code=201)
def add_opportunity(body: NewOpp, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Paste an announcement; the LLM extracts deadline, eligibility and required documents."""
    d = llm.extract(body.text)
    try: deadline = dt.date.fromisoformat(d["deadline"]) if d.get("deadline") else None
    except ValueError: deadline = None
    o = Opportunity(user_id=u.id, title=d.get("title") or "Untitled", organization=d.get("organization") or "",
                    deadline=deadline, raw_text=body.text[:8000],
                    requirements={k: d.get(k) for k in ("min_gpa", "degree_levels", "fields", "countries", "eligibility_notes")})
    o.items = [DocItem(name=n) for n in d.get("documents") or []]
    db.add(o); db.commit()
    return opp_view(o, u)

@app.get("/opportunities")
def list_opportunities(u: User = Depends(current_user)):
    return [opp_view(o, u) for o in u.opportunities]

def _own(db, u, oid):
    o = db.get(Opportunity, oid)
    if not o or o.user_id != u.id: raise HTTPException(404, "Not found")
    return o

@app.get("/opportunities/{oid}")
def get_opportunity(oid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return opp_view(_own(db, u, oid), u)

@app.patch("/opportunities/{oid}/status")
def set_status(oid: int, s: StatusIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if s.status not in {"saved", "applied", "won", "rejected"}: raise HTTPException(422, "Invalid status")
    o = _own(db, u, oid); o.status = s.status; db.commit(); return opp_view(o, u)

@app.patch("/opportunities/{oid}/checklist/{item_id}")
def toggle_doc(oid: int, item_id: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    o = _own(db, u, oid); item = next((i for i in o.items if i.id == item_id), None)
    if not item: raise HTTPException(404, "Checklist item not found")
    item.done = not item.done; db.commit(); return opp_view(o, u)

@app.delete("/opportunities/{oid}", status_code=204)
def delete_opportunity(oid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_own(db, u, oid)); db.commit()

@app.get("/dashboard")
def get_dashboard(u: User = Depends(current_user)):
    """Open opportunities ranked by priority = fit + urgency, discounted by readiness."""
    return dashboard(u)

@app.post("/digest/send-now")
def send_digest_now(u: User = Depends(current_user)):
    jobs.send_email(u.email, "📬 Your scholarship digest", jobs.digest_for(u)); return {"sent": True}
