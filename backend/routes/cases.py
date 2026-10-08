from flask import Blueprint, jsonify

from backend.database import collections

bp = Blueprint("cases", __name__, url_prefix="/api/cases")


@bp.get("")
def list_cases():
    cases, _ = collections()
    projection = {"solution": 0, "_id": 0, "suspects.statement": 0, "suspects.motive": 0}
    return jsonify(list(cases.find({}, projection).sort("caseId", 1)))


@bp.get("/<case_id>")
def get_case(case_id):
    cases, _ = collections()
    case = cases.find_one({"caseId": case_id.upper()}, {"solution": 0, "_id": 0})
    if not case:
        return jsonify(error="Case not found."), 404
    return jsonify(case)
