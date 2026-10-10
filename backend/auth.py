import os
import secrets
import time
import hashlib
import hmac

from dotenv import load_dotenv
from fastapi import Header, HTTPException

from backend.db import students
from backend.models import mongo_json

load_dotenv()
_tokens: dict[str, float] = {}
_student_tokens: dict[str, tuple[str, float]] = {}
TOKEN_TTL_SECONDS = 12 * 60 * 60
PASSWORD_ITERATIONS = 310_000


def issue_admin_token(password: str) -> str:
    expected = os.getenv("ADMIN_PASSWORD", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Admin password is not configured")
    if not secrets.compare_digest(password, expected):
        raise HTTPException(status_code=401, detail="Incorrect admin password")
    token = secrets.token_urlsafe(32)
    _tokens[token] = time.time() + TOKEN_TTL_SECONDS
    return token


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token:
        raise HTTPException(status_code=401, detail="Admin login required")
    expiry = _tokens.get(x_admin_token)
    if not expiry or expiry < time.time():
        _tokens.pop(x_admin_token, None)
        raise HTTPException(status_code=401, detail="Admin token is invalid or expired")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), PASSWORD_ITERATIONS
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def public_student(student: dict) -> dict:
    return mongo_json({key: value for key, value in student.items() if key != "passwordHash"})


def issue_student_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    _student_tokens[token] = (email, time.time() + TOKEN_TTL_SECONDS)
    return token


def require_student(x_student_token: str | None = Header(default=None)) -> dict:
    if not x_student_token:
        raise HTTPException(status_code=401, detail="Student sign-in required")
    session = _student_tokens.get(x_student_token)
    if not session or session[1] < time.time():
        _student_tokens.pop(x_student_token, None)
        raise HTTPException(status_code=401, detail="Student session is invalid or expired")
    student = students.find_one({"email": session[0]})
    if not student:
        _student_tokens.pop(x_student_token, None)
        raise HTTPException(status_code=401, detail="Student account no longer exists")
    return student
