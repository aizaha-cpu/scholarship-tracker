import os, smtplib, datetime as dt
from email.message import EmailMessage
from apscheduler.schedulers.background import BackgroundScheduler
from .models import SessionLocal, User, Reminder
from .services import dashboard

def send_email(to, subject, body):
    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"\n[EMAIL → {to}] {subject}\n{body}\n"); return
    msg = EmailMessage(); msg["To"], msg["Subject"], msg["From"] = to, subject, os.getenv("SMTP_USER")
    msg.set_content(body)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", 587))) as s:
        s.starttls(); s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")); s.send_message(msg)

def deadline_reminders():
    """Daily cron: email at 7, 3 and 1 days before a deadline (once each)."""
    with SessionLocal() as db:
        for user in db.query(User).all():
            for v in dashboard(user):
                d = v["days_left"]
                if d in (7, 3, 1) and not db.query(Reminder).filter_by(opportunity_id=v["id"], days_before=d).first():
                    send_email(user.email, f"⏰ {d} day(s) left: {v['title']}",
                               f"Deadline {v['deadline']}. Readiness {int(v['readiness']*100)}%. {v['next_action']}")
                    db.add(Reminder(opportunity_id=v["id"], days_before=d)); db.commit()

def digest_for(user) -> str:
    rows = dashboard(user)[:10]
    if not rows: return "No open opportunities. Paste a new announcement to get started!"
    lines = [f"{i}. {v['title']} — fit {v['fit_score']}%, ready {int(v['readiness']*100)}%, "
             f"{'no deadline' if v['days_left'] is None else str(v['days_left']) + ' days left'}\n   → {v['next_action']}"
             for i, v in enumerate(rows, 1)]
    return "Your priorities this week:\n\n" + "\n".join(lines)

def weekly_digest():
    with SessionLocal() as db:
        for user in db.query(User).all():
            send_email(user.email, "📬 Your weekly scholarship digest", digest_for(user))

def start():
    s = BackgroundScheduler()
    s.add_job(deadline_reminders, "cron", hour=8)
    s.add_job(weekly_digest, "cron", day_of_week="mon", hour=9)
    s.start(); return s
