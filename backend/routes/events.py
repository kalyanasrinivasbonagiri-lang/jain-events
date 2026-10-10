from datetime import datetime, timezone
import re

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import require_admin, require_student
from backend.db import events, registrations, students
from backend.models import EventCreate, EventUpdate, mongo_json

router = APIRouter(prefix="/api", tags=["events and registrations"])


def parse_event_id(event_id: str) -> ObjectId:
    if not ObjectId.is_valid(event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return ObjectId(event_id)


def event_or_404(event_id: ObjectId) -> dict:
    event = events.find_one({"_id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def event_payload(event: dict) -> dict:
    event["registrationCount"] = registrations.count_documents({"eventId": event["_id"]})
    return mongo_json(event)


@router.get("/events")
def list_events(q: str | None = Query(default=None, max_length=120), date: str | None = None):
    query: dict = {}
    if q and q.strip():
        query["$or"] = [
            {"title": {"$regex": re.escape(q.strip()), "$options": "i"}},
            {"description": {"$regex": re.escape(q.strip()), "$options": "i"}},
            {"venue": {"$regex": re.escape(q.strip()), "$options": "i"}},
        ]
    if date:
        try:
            selected_date = datetime.fromisoformat(date).date()
        except ValueError:
            raise HTTPException(status_code=422, detail="Date filter must be YYYY-MM-DD")
        start = datetime.combine(selected_date, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(selected_date, datetime.max.time(), tzinfo=timezone.utc)
        query["date"] = {"$gte": start, "$lte": end}
    return [event_payload(item) for item in events.find(query).sort("date", 1)]


@router.post("/events", status_code=201, dependencies=[Depends(require_admin)])
def create_event(payload: EventCreate):
    document = payload.model_dump()
    document.update(
        availableSeats=payload.totalSeats,
        createdAt=datetime.now(timezone.utc),
    )
    result = events.insert_one(document)
    return event_payload(events.find_one({"_id": result.inserted_id}))


@router.put("/events/{event_id}", dependencies=[Depends(require_admin)])
def update_event(event_id: str, payload: EventUpdate):
    oid = parse_event_id(event_id)
    existing = event_or_404(oid)
    changes = payload.model_dump(exclude_unset=True)
    new_total = changes.get("totalSeats", existing["totalSeats"])
    current_registrations = registrations.count_documents({"eventId": oid})
    if new_total < current_registrations:
        raise HTTPException(
            status_code=400,
            detail=f"totalSeats cannot be below the {current_registrations} current registrations",
        )
    changes["availableSeats"] = new_total - current_registrations
    if changes:
        events.update_one({"_id": oid}, {"$set": changes})
    return event_payload(event_or_404(oid))


@router.delete("/events/{event_id}", status_code=200, dependencies=[Depends(require_admin)])
def delete_event(event_id: str):
    oid = parse_event_id(event_id)
    event_or_404(oid)
    events.delete_one({"_id": oid})
    registrations.delete_many({"eventId": oid})
    return {"message": "Event and its registrations deleted"}


@router.post("/events/{event_id}/register", status_code=201)
def register_for_event(event_id: str, student: dict = Depends(require_student)):
    oid = parse_event_id(event_id)
    event = event_or_404(oid)
    now = datetime.now(timezone.utc)
    if event["date"] <= now:
        raise HTTPException(status_code=400, detail="Registration is closed for past events")

    # Claim a seat atomically so concurrent requests cannot oversell the event.
    updated = events.find_one_and_update(
        {"_id": oid, "availableSeats": {"$gt": 0}, "date": {"$gt": now}},
        {"$inc": {"availableSeats": -1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        current = events.find_one({"_id": oid})
        if not current:
            raise HTTPException(status_code=404, detail="Event not found")
        if current["date"] <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Registration is closed for past events")
        raise HTTPException(status_code=400, detail="Event full")

    registration = {
        "eventId": oid,
        "studentName": student["studentName"],
        "email": student["email"],
        "usn": student["usn"],
        "branch": student["branch"],
        "year": student["year"],
        "registeredAt": datetime.now(timezone.utc),
    }
    try:
        result = registrations.insert_one(registration)
    except DuplicateKeyError:
        events.update_one({"_id": oid}, {"$inc": {"availableSeats": 1}})
        raise HTTPException(status_code=409, detail="This email is already registered for the event")
    except PyMongoError:
        events.update_one({"_id": oid}, {"$inc": {"availableSeats": 1}})
        raise
    registration["_id"] = result.inserted_id
    registration["eventTitle"] = updated["title"]
    return mongo_json(registration)


@router.delete("/events/{event_id}/register")
def cancel_registration(
    event_id: str,
    email: str | None = Query(default=None, min_length=3, max_length=254),
    student: dict = Depends(require_student),
):
    oid = parse_event_id(event_id)
    normalized_email = student["email"]
    if email and email.strip().lower() != normalized_email:
        raise HTTPException(status_code=403, detail="You can only cancel your own registration")
    event = event_or_404(oid)
    deleted = registrations.find_one_and_delete({"eventId": oid, "email": normalized_email})
    if not deleted:
        raise HTTPException(status_code=404, detail="Registration not found")
    events.update_one(
        {"_id": oid, "availableSeats": {"$lt": event["totalSeats"]}},
        {"$inc": {"availableSeats": 1}},
    )
    return {"message": "Registration cancelled", "eventId": event_id}


@router.get("/events/{event_id}/registrations", dependencies=[Depends(require_admin)])
def event_registrations(event_id: str):
    oid = parse_event_id(event_id)
    event = event_or_404(oid)
    return {
        "event": mongo_json(event),
        "registrations": [
            mongo_json(item)
            for item in registrations.find({"eventId": oid}).sort("registeredAt", 1)
        ],
    }


@router.get("/my-registrations")
def my_registrations(student: dict = Depends(require_student)):
    normalized_email = student["email"]
    items = []
    for registration in registrations.find({"email": normalized_email}).sort("registeredAt", -1):
        event = events.find_one({"_id": registration["eventId"]})
        if event:
            item = mongo_json(registration)
            item["event"] = mongo_json(event)
            items.append(item)
    return items


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats():
    rows = []
    for event in events.find().sort("date", 1):
        count = registrations.count_documents({"eventId": event["_id"]})
        rows.append(
            {
                "eventId": str(event["_id"]),
                "title": event["title"],
                "registrations": count,
                "availableSeats": event["availableSeats"],
                "totalSeats": event["totalSeats"],
            }
        )
    return {
        "totalEvents": len(rows),
        "totalRegistrations": sum(item["registrations"] for item in rows),
        "totalStudents": students.count_documents({}),
        "branches": branch_stats(),
        "events": rows,
    }


def branch_stats() -> list[dict]:
    pipeline = [
        {"$group": {"_id": {"$ifNull": ["$branch", "Unspecified"]}, "registrations": {"$sum": 1}}},
        {"$sort": {"registrations": -1}},
    ]
    return [{"branch": row["_id"], "registrations": row["registrations"]} for row in registrations.aggregate(pipeline)]
