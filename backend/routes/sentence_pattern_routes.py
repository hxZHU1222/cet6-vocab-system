from __future__ import annotations
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request
from ..services.sentence_pattern_service import (
    get_or_create_today_pattern_task,
    grade_sentence_pattern,
    import_sentence_patterns_from_csv,
    pick_study_patterns,
    sentence_pattern_query,
    sentence_stats,
    serialize_pattern,
)
from ..models import SentencePattern, DailyPatternTaskItem

sentence_bp = Blueprint("sentence_patterns", __name__, url_prefix="/api/sentence-patterns")

@sentence_bp.get("")
def list_patterns():
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 30)), 1), 100)
    pagination = sentence_pattern_query(category=category, q=q, status=status).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [serialize_pattern(p) for p in pagination.items],
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    })

@sentence_bp.get("/categories")
def categories():
    stats = sentence_stats()
    return jsonify(stats["categories"])

@sentence_bp.get("/stats")
def stats():
    return jsonify(sentence_stats())

@sentence_bp.get("/study")
def study_session():
    mode = request.args.get("mode", "new")
    limit = int(request.args.get("limit", current_app.config.get("DAILY_NEW_PATTERNS", 5)))
    items = pick_study_patterns(mode=mode, limit=limit)
    return jsonify({"mode": mode, "items": [serialize_pattern(p) for p in items]})

@sentence_bp.post("/grade")
def grade():
    payload = request.get_json(silent=True) or {}
    pattern_id = int(payload.get("pattern_id"))
    grade_value = int(payload.get("grade"))
    source = payload.get("source", "pattern_study")
    progress = grade_sentence_pattern(pattern_id, grade_value, source=source)
    return jsonify({
        "ok": True,
        "pattern_id": pattern_id,
        "familiarity": progress.familiarity,
        "seen_count": progress.seen_count,
        "is_mastered": progress.is_mastered,
        "next_review_date": progress.next_review_date.isoformat() if progress.next_review_date else None,
    })

@sentence_bp.post("/import")
def import_patterns():
    file = request.files.get("file")
    if not file:
        return jsonify({"ok": False, "error": "请上传 CSV 文件，字段需包含 title/category/pattern_en。"}), 400
    result = import_sentence_patterns_from_csv(file)
    result["ok"] = True
    return jsonify(result)

@sentence_bp.post("/default-import")
def default_import():
    path = Path(current_app.root_path).parent / "data" / "cet6_sentence_patterns_import.csv"
    result = import_sentence_patterns_from_csv(path)
    result["ok"] = True
    return jsonify(result)

@sentence_bp.get("/today")
def today_patterns():
    task = get_or_create_today_pattern_task(
        new_target=current_app.config.get("DAILY_NEW_PATTERNS", 5),
        review_target=current_app.config.get("DAILY_REVIEW_PATTERNS", 5),
    )
    items = DailyPatternTaskItem.query.filter_by(daily_task_id=task.id).all()
    pattern_map = {p.id: p for p in SentencePattern.query.filter(SentencePattern.id.in_([i.pattern_id for i in items] or [0])).all()}
    return jsonify({
        "task_date": task.task_date.isoformat(),
        "new_target_count": task.new_target_count,
        "review_target_count": task.review_target_count,
        "items": [{
            "item_type": item.item_type,
            "status": item.status,
            "pattern": serialize_pattern(pattern_map[item.pattern_id]) if item.pattern_id in pattern_map else None,
        } for item in items]
    })
