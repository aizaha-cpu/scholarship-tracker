import os, hashlib, hmac, secrets, datetime as dt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .models import get_db, User

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
bearer = HTTPBearer()

def _hash(p, salt): return hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 200_000).hex()
def hash_pw(p):
    salt = secrets.token_hex(16); return f"{salt}${_hash(p, salt)}"
def verify_pw(p, stored):
    salt, h = stored.split("$"); return hmac.compare_digest(_hash(p, salt), h)

def make_token(uid: int):
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24)
    return jwt.encode({"sub": str(uid), "exp": exp}, SECRET, algorithm="HS256")

def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try:
        uid = int(jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, uid)
    if not user: raise HTTPException(401, "User not found")
    return user
