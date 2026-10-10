from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from backend.auth import (
    hash_password,
    issue_admin_token,
    issue_student_token,
    public_student,
    require_admin,
    require_student,
    verify_password,
)
from backend.db import events, registrations, students
from backend.models import AdminLogin, StudentLogin, StudentSignup, mongo_json

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/login")
def admin_login(payload: AdminLogin):
    return {"token": issue_admin_token(payload.password), "tokenType": "X-Admin-Token"}


@router.post("/student/signup", status_code=201)
def student_signup(payload: StudentSignup):
    document = payload.model_dump(exclude={"password"})
    document["passwordHash"] = hash_password(payload.password)
    document["createdAt"] = datetime.now(timezone.utc)
    try:
        students.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="That email or USN already has an account")
    return {"token": issue_student_token(document["email"]), "student": public_student(document)}


@router.post("/student/login")
def student_login(payload: StudentLogin):
    student = students.find_one({"email": str(payload.email).lower()})
    if not student or not verify_password(payload.password, student.get("passwordHash", "")):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return {
        "token": issue_student_token(student["email"]),
        "student": public_student(student),
    }


@router.get("/student/me")
def student_me(student: dict = Depends(require_student)):
    return public_student(student)


@router.get("/admin/db-view", dependencies=[Depends(require_admin)])
def database_view():
    return {
        "events": [mongo_json(item) for item in events.find().sort("date", 1)],
        "registrations": [
            mongo_json(item) for item in registrations.find().sort("registeredAt", -1)
        ],
        "students": [public_student(item) for item in students.find().sort("createdAt", -1)],
    }
