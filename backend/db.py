import os

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from bson import ObjectId

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/event_portal")
client = MongoClient(MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=5000)
database = client.get_default_database(default="event_portal")
events = database["events"]
registrations = database["registrations"]
students = database["students"]


def create_indexes() -> None:
    events.create_index([("date", ASCENDING)])
    registrations.create_index(
        [("eventId", ASCENDING), ("email", ASCENDING)], unique=True
    )
    registrations.create_index([("email", ASCENDING)])
    registrations.create_index([("eventId", ASCENDING)])
    students.create_index([("email", ASCENDING)], unique=True)
    students.create_index([("usn", ASCENDING)], unique=True)
    registrations.update_many(
        {"branch": {"$exists": False}, "email": {"$exists": True}},
        [{"$set": {"branch": "Not provided", "year": 1, "usn": {"$concat": ["LEGACY-", {"$toString": "$_id"}]}}}],
    )
    for registration in registrations.find({"eventName": {"$exists": False}}, {"eventId": 1}):
        event = events.find_one({"_id": registration["eventId"]}, {"title": 1})
        if event:
            registrations.update_one(
                {"_id": registration["_id"], "eventName": {"$exists": False}},
                {"$set": {"eventName": event["title"]}},
            )
