"""Upsert four demo events while retaining existing registrations."""
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from backend.db import client, create_indexes, events, registrations

SAMPLE_EVENTS = [
    {
        "_id": ObjectId("670000000000000000000001"),
        "title": "Python for Everyone",
        "description": "A friendly hands-on introduction to Python with short coding activities.",
        "days": 4,
        "venue": "Innovation Lab, Block A",
        "totalSeats": 36,
    },
    {
        "_id": ObjectId("670000000000000000000002"),
        "title": "Campus Startup Showcase",
        "description": "Meet student founders, see early products, and share feedback.",
        "days": 8,
        "venue": "Main Auditorium",
        "totalSeats": 120,
    },
    {
        "_id": ObjectId("670000000000000000000003"),
        "title": "Designing for the Web",
        "description": "A practical workshop on accessible layouts, visual hierarchy, and prototyping.",
        "days": 12,
        "venue": "Digital Media Studio",
        "totalSeats": 28,
    },
    {
        "_id": ObjectId("670000000000000000000004"),
        "title": "Student Research Forum",
        "description": "Lightning talks and discussion across computing, science, and the humanities.",
        "days": 18,
        "venue": "Seminar Hall 2",
        "totalSeats": 80,
    },
]


def seed() -> None:
    create_indexes()
    now = datetime.now(timezone.utc)
    for sample in SAMPLE_EVENTS:
        registration_count = registrations.count_documents({"eventId": sample["_id"]})
        capacity = max(sample["totalSeats"], registration_count)
        document = {
            "_id": sample["_id"],
            "title": sample["title"],
            "description": sample["description"],
            "date": now + timedelta(days=sample["days"]),
            "venue": sample["venue"],
            "totalSeats": capacity,
            "availableSeats": capacity - registration_count,
            "createdAt": now,
        }
        events.replace_one({"_id": sample["_id"]}, document, upsert=True)
        print(f"Seeded: {document['title']} ({registration_count} existing registrations kept)")
    print("Seed complete. Existing registration documents were preserved.")


if __name__ == "__main__":
    try:
        client.admin.command("ping")
        seed()
    except Exception as exc:
        raise SystemExit(f"Could not seed MongoDB: {exc}")
