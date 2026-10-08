"""Insert or refresh the three built-in cases without touching investigations."""
from datetime import datetime, timezone

from pymongo import ASCENDING

from backend.database import collections, mongo
from backend.seed_data import CASES


def seed():
    cases, investigations = collections()
    for case in CASES:
        cases.replace_one({"caseId": case["caseId"]}, case, upsert=True)
    cases.create_index([("caseId", ASCENDING)], unique=True)
    investigations.create_index([("investigationId", ASCENDING)], unique=True)
    investigations.create_index([("caseId", ASCENDING)])
    print("Seeded CASE001, CASE002, CASE003 into mystery_case_solver.cases")
    print("Indexes created; existing investigations were preserved.")


if __name__ == "__main__":
    from flask import Flask
    from backend.database import init_database

    app = Flask(__name__)
    init_database(app)
    with app.app_context():
        try:
            mongo.cx.admin.command("ping")
            print("Connected to MongoDB")
            seed()
        except Exception as exc:
            raise SystemExit(f"Could not connect to MongoDB: {exc}")
