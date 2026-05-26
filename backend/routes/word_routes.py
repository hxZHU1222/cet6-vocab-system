from __future__ import annotations
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request
from ..models import Word
from ..services.word_service import (
    get_or_create_today_task,
    grade_word_and_mark,
    import_words_from_csv,
    pick_dictation_words,
    pick_study_words,
    serialize_word,
    submit_dictation,
    today_word_dashboard,
    word_stats,
)

word_bp = Blueprint("words", __name__, url_prefix="/api/words")

@word_bp.get("/stats")
def stats():
    return jsonify(word_stats())

@word_bp.get("/today")
def today():
    return jsonify(today_word_dashboard(
        new_target=current_app.config.get("DAILY_NEW_WORDS", 100),
        dictation_target=current_app.config.get("DAILY_DICTATION_WORDS", 20),
        review_limit=current_app.config.get("DAILY_REVIEW_WORD_LIMIT", 80),
    ))

@word_bp.post("/today/generate")
def generate_today():
    task = get_or_create_today_task(
        new_target=current_app.config.get("DAILY_NEW_WORDS", 100),
        dictation_target=current_app.config.get("DAILY_DICTATION_WORDS", 20),
        review_limit=current_app.config.get("DAILY_REVIEW_WORD_LIMIT", 80),
    )
    return jsonify({"ok": True, "task_id": task.id, "today": word_stats().get("today")})

@word_bp.get("/study")
def study_words():
    mode = request.args.get("mode", "today_new")
    limit = int(request.args.get("limit", "100"))
    words = pick_study_words(mode=mode, limit=limit)
    return jsonify({"mode": mode, "items": [serialize_word(w) for w in words]})

@word_bp.post("/grade")
def grade_word():
    payload = request.get_json(silent=True) or {}
    progress = grade_word_and_mark(int(payload["word_id"]), int(payload["grade"]), payload.get("source", "study"))
    return jsonify({
        "ok": True,
        "word_id": progress.word_id,
        "familiarity": progress.familiarity,
        "active_weak": progress.active_weak,
        "active_wrong": progress.active_wrong,
        "is_mastered": progress.is_mastered,
        "next_review_date": progress.next_review_date.isoformat() if progress.next_review_date else None,
    })

@word_bp.get("/dictation-session")
def dictation_session():
    mode = request.args.get("mode", "today")
    limit = int(request.args.get("limit", current_app.config.get("DAILY_DICTATION_WORDS", 20)))
    words = pick_dictation_words(mode=mode, limit=limit)
    return jsonify({"mode": mode, "items": [serialize_word(w) for w in words]})

@word_bp.post("/dictation-submit")
def dictation_submit():
    payload = request.get_json(silent=True) or {}
    result = submit_dictation(int(payload["word_id"]), payload.get("answer", ""), payload.get("source", "dictation"))
    return jsonify(result)

@word_bp.get("")
def list_words():
    q = (request.args.get("q") or "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 50)), 1), 100)
    query = Word.query
    if q:
        like = f"%{q}%"
        query = query.filter((Word.word.like(like)) | (Word.meaning_cn.like(like)))
    pagination = query.order_by(Word.source_order.asc(), Word.id.asc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"items": [serialize_word(w) for w in pagination.items], "page": page, "pages": pagination.pages, "total": pagination.total})

@word_bp.post("/import")
def import_words():
    file = request.files.get("file")
    if not file:
        return jsonify({"ok": False, "error": "请上传词库 CSV，至少包含 word 字段。"}), 400
    result = import_words_from_csv(file)
    result["ok"] = True
    return jsonify(result)
