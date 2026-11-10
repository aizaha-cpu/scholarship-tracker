"""The 'extra' feature: explainable Fit Score + Readiness-weighted priority."""
import datetime as dt

def fit_score(user, req: dict):
    """Returns (score 0-100, reasons). Unknown requirements don't penalise, but are noted."""
    score, reasons = 0, []
    def check(points, ok, yes, no):
        nonlocal score
        if ok is None: score += points; reasons.append(no)
        elif ok: score += points; reasons.append("✓ " + yes)
        else: reasons.append("✗ " + no)
    levels = req.get("degree_levels") or []
    check(25, None if not levels else (user.degree_level.lower() in levels or not user.degree_level),
          "Degree level matches", f"Requires {'/'.join(levels)}" if levels else "Degree level not specified")
    fields = [f.lower() for f in req.get("fields") or []]
    check(25, None if not fields else any(user.field.lower() in f or f in user.field.lower() for f in fields) if user.field else True,
          "Field of study matches", f"Open to: {', '.join(fields)}" if fields else "Field not specified")
    countries = [c.lower() for c in req.get("countries") or []]
    check(20, None if not countries else (user.country.lower() in countries or not user.country),
          "Nationality eligible", f"Limited to: {', '.join(countries)}" if countries else "Nationality not restricted")
    mg = req.get("min_gpa")
    check(30, None if mg is None else (user.gpa is None or user.gpa >= mg),
          f"GPA meets {mg}", f"Needs GPA {mg}" + (f" (you have {user.gpa})" if user.gpa else "") if mg else "No GPA minimum stated")
    return score, reasons

def readiness(opp):
    return round(sum(i.done for i in opp.items) / len(opp.items), 2) if opp.items else 0.0

def opp_view(opp, user):
    score, reasons = fit_score(user, opp.requirements or {})
    today = dt.date.today()
    days = (opp.deadline - today).days if opp.deadline else None
    ready = readiness(opp)
    urgency = 0.3 if days is None else max(0.0, 1 - days / 30) if days >= 0 else 0.0
    priority = round(100 * (0.5 * score / 100 + 0.5 * urgency) * (1 - 0.3 * ready))
    pending = next((i.name for i in opp.items if not i.done), None)
    return {"id": opp.id, "title": opp.title, "organization": opp.organization,
            "deadline": opp.deadline, "days_left": days, "status": opp.status,
            "fit_score": score, "fit_reasons": reasons, "readiness": ready, "priority": priority,
            "next_action": (f"Prepare: {pending}" if pending else "Submit your application") if opp.status == "saved" else None,
            "checklist": [{"id": i.id, "name": i.name, "done": i.done} for i in opp.items]}

def dashboard(user):
    views = [opp_view(o, user) for o in user.opportunities if o.status == "saved" and (o.deadline is None or o.deadline >= dt.date.today())]
    return sorted(views, key=lambda v: -v["priority"])
