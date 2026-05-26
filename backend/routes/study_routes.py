from __future__ import annotations
from flask import Blueprint, jsonify, request
from ..services.p10_state_service import apply_word_grade, apply_word_dictation_result

study_bp = Blueprint("study_api", __name__, url_prefix="/api/study")

@study_bp.post("/grade")
def grade_word():
    payload = request.get_json(silent=True) or {}
    progress = apply_word_grade(int(payload["word_id"]), int(payload["grade"]), payload.get("source", "study"))
    return jsonify({
        "ok": True,
        "word_id": progress.word_id,
        "familiarity": progress.familiarity,
        "active_weak": progress.active_weak,
        "active_wrong": progress.active_wrong,
        "is_mastered": progress.is_mastered,
        "next_review_date": progress.next_review_date.isoformat() if progress.next_review_date else None,
    })

@study_bp.post("/dictation-result")
def word_dictation_result():
    payload = request.get_json(silent=True) or {}
    progress = apply_word_dictation_result(
        int(payload["word_id"]),
        bool(payload["is_correct"]),
        payload.get("user_answer", ""),
        payload.get("source", "dictation"),
    )
    return jsonify({
        "ok": True,
        "word_id": progress.word_id,
        "correct_streak": progress.correct_streak,
        "active_wrong": progress.active_wrong,
        "dictation_wrong_count": progress.dictation_wrong_count,
    })
