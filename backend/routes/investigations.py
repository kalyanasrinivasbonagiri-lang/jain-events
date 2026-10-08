from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from flask import Blueprint, jsonify, request
from pymongo import ReturnDocument

from backend.database import collections

bp = Blueprint("investigations", __name__, url_prefix="/api/investigations")


def now():
    return datetime.now(timezone.utc)


def get_investigation(identifier):
    _, investigations = collections()
    query = {"investigationId": identifier}
    if ObjectId.is_valid(identifier):
        query = {"$or": [query, {"_id": ObjectId(identifier)}]}
    return investigations.find_one(query)


def response_document(doc):
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


@bp.post("")
def create_investigation():
    data = request.get_json(silent=True) or {}
    case_id = str(data.get("caseId", "")).upper()
    cases, investigations = collections()
    case = cases.find_one({"caseId": case_id})
    if not case:
        return jsonify(error="Choose a valid case."), 400
    doc = {"investigationId": str(uuid4()), "caseId": case_id, "createdAt": now(), "updatedAt": now(),
           "discoveredEvidence": [], "importantEvidence": [], "boardEvidence": [], "connections": [], "notes": [],
           "theory": {"culprit": "", "motive": "", "method": "", "supportingEvidence": []},
           "accusation": None, "result": None}
    investigations.insert_one(doc)
    return jsonify(response_document(doc)), 201


@bp.get("/<identifier>")
def get_investigation_route(identifier):
    doc = get_investigation(identifier)
    if not doc:
        return jsonify(error="Investigation not found."), 404
    return jsonify(response_document(doc))


@bp.get("/<identifier>/solution")
def get_solution(identifier):
    inv = get_investigation(identifier)
    if not inv:
        return jsonify(error="Investigation not found."), 404
    if not inv.get("accusation"):
        return jsonify(error="Submit an accusation before viewing the solution."), 403
    cases, _ = collections()
    case = cases.find_one({"caseId": inv["caseId"]})
    return jsonify(solution=case["solution"], result=inv["result"], caseTitle=case["title"])


@bp.patch("/<identifier>/evidence/<evidence_id>")
def update_evidence(identifier, evidence_id):
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    cases, investigations = collections()
    inv = get_investigation(identifier)
    if not inv:
        return jsonify(error="Investigation not found."), 404
    case = cases.find_one({"caseId": inv["caseId"]})
    if not any(item["id"] == evidence_id for item in case.get("evidence", [])):
        return jsonify(error="Evidence not found in this case."), 404
    updates = {"updatedAt": now()}
    if action == "investigate":
        investigations.update_one({"_id": inv["_id"]}, {"$addToSet": {"discoveredEvidence": evidence_id}, "$set": updates})
    elif action == "important":
        investigations.update_one({"_id": inv["_id"]}, {"$addToSet": {"discoveredEvidence": evidence_id, "importantEvidence": evidence_id}, "$set": updates})
    elif action == "board":
        investigations.update_one({"_id": inv["_id"]}, {"$addToSet": {"discoveredEvidence": evidence_id, "boardEvidence": evidence_id}, "$set": updates})
    else:
        return jsonify(error="Choose investigate, important, or board."), 400
    return jsonify(response_document(get_investigation(identifier)))


@bp.post("/<identifier>/notes")
def add_note(identifier):
    data = request.get_json(silent=True) or {}
    content = str(data.get("content", "")).strip()
    if not content or len(content) > 1000:
        return jsonify(error="A note is required (up to 1000 characters)."), 400
    _, investigations = collections()
    inv = get_investigation(identifier)
    if not inv:
        return jsonify(error="Investigation not found."), 404
    note = {"noteId": str(uuid4()), "content": content, "createdAt": now()}
    investigations.update_one({"_id": inv["_id"]}, {"$push": {"notes": note}, "$set": {"updatedAt": now()}})
    return jsonify(note), 201


@bp.post("/<identifier>/connections")
def add_connection(identifier):
    data = request.get_json(silent=True) or {}
    source, target = data.get("source"), data.get("target")
    kind = data.get("kind", "supports")
    if not source or not target or source == target or kind not in ("supports", "contradicts"):
        return jsonify(error="Provide two different items and a valid relationship."), 400
    _, investigations = collections()
    inv = get_investigation(identifier)
    if not inv:
        return jsonify(error="Investigation not found."), 404
    ids = set(inv.get("boardEvidence", [])) | {e["id"] for e in []}
    # Connections may involve evidence IDs only, keeping the board simple.
    cases, _ = collections()
    case = cases.find_one({"caseId": inv["caseId"]})
    valid = {e["id"] for e in case.get("evidence", [])} | {s["id"] for s in case.get("suspects", [])}
    if source not in valid or target not in valid:
        return jsonify(error="Choose evidence or suspect IDs from this case."), 400
    connection = {"source": source, "target": target, "kind": kind}
    investigations.update_one({"_id": inv["_id"]}, {"$addToSet": {"connections": connection}, "$set": {"updatedAt": now()}})
    return jsonify(response_document(get_investigation(identifier)))


@bp.delete("/<identifier>/connections")
def remove_connection(identifier):
    data = request.get_json(silent=True) or {}
    _, investigations = collections()
    inv = get_investigation(identifier)
    if not inv:
        return jsonify(error="Investigation not found."), 404
    investigations.update_one({"_id": inv["_id"]}, {"$pull": {"connections": {"source": data.get("source"), "target": data.get("target")}}, "$set": {"updatedAt": now()}})
    return jsonify(response_document(get_investigation(identifier)))


@bp.put("/<identifier>/theory")
def save_theory(identifier):
    data = request.get_json(silent=True) or {}
    _, investigations = collections()
    inv = get_investigation(identifier)
    if not inv:
        return jsonify(error="Investigation not found."), 404
    if inv.get("accusation"):
        return jsonify(error="This accusation has already been submitted."), 409
    theory = {"culprit": str(data.get("culprit", "")), "motive": str(data.get("motive", ""))[:500],
              "method": str(data.get("method", ""))[:500], "supportingEvidence": data.get("supportingEvidence", [])}
    investigations.update_one({"_id": inv["_id"]}, {"$set": {"theory": theory, "updatedAt": now()}})
    return jsonify(response_document(get_investigation(identifier)))


@bp.post("/<identifier>/accuse")
def submit_accusation(identifier):
    data = request.get_json(silent=True) or {}
    _, investigations = collections()
    inv = get_investigation(identifier)
    if not inv:
        return jsonify(error="Investigation not found."), 404
    if inv.get("accusation"):
        return jsonify(error="This accusation has already been submitted."), 409
    theory = inv.get("theory", {})
    if not theory.get("culprit") or not theory.get("motive", "").strip() or not theory.get("method", "").strip():
        return jsonify(error="Complete the culprit, motive, and method before submitting."), 400
    cases, _ = collections()
    case = cases.find_one({"caseId": inv["caseId"]})
    if theory["culprit"] not in {s["id"] for s in case.get("suspects", [])}:
        return jsonify(error="Choose a suspect from this case."), 400
    accusation = {**theory, "submittedAt": now()}
    solution = case["solution"]
    culprit_correct = theory["culprit"] == solution["culprit"]
    motive_correct = any(word.lower() in theory["motive"].lower() for word in solution["motive"].split() if len(word) > 4)
    method_correct = any(word.lower() in theory["method"].lower() for word in solution["method"].split() if len(word) > 5)
    correct = culprit_correct and motive_correct and method_correct
    result = {"correct": correct, "culpritCorrect": culprit_correct, "motiveCorrect": motive_correct, "methodCorrect": method_correct, "submittedAt": now()}
    updated = investigations.find_one_and_update({"_id": inv["_id"], "accusation": None}, {"$set": {"accusation": accusation, "result": result, "updatedAt": now()}}, return_document=ReturnDocument.AFTER)
    if not updated:
        return jsonify(error="This accusation has already been submitted."), 409
    result["solution"] = solution
    result["caseTitle"] = case["title"]
    return jsonify(result)
