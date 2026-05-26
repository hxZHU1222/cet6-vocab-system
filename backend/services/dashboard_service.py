from __future__ import annotations
from flask import current_app
from ..services.word_service import today_word_dashboard, word_stats
from ..services.sentence_pattern_service import get_or_create_today_pattern_task, sentence_stats
from ..models import DailyPatternTaskItem


def merged_dashboard() -> dict:
    word_today = today_word_dashboard(
        new_target=current_app.config.get("DAILY_NEW_WORDS", 100),
        dictation_target=current_app.config.get("DAILY_DICTATION_WORDS", 20),
        review_limit=current_app.config.get("DAILY_REVIEW_WORD_LIMIT", 80),
    )
    pattern_task = get_or_create_today_pattern_task(
        new_target=current_app.config.get("DAILY_NEW_PATTERNS", 5),
        review_target=current_app.config.get("DAILY_REVIEW_PATTERNS", 5),
    )
    new_total = DailyPatternTaskItem.query.filter_by(daily_task_id=pattern_task.id, item_type="new").count()
    review_total = DailyPatternTaskItem.query.filter_by(daily_task_id=pattern_task.id, item_type="review").count()
    pattern_today = {
        "task_date": pattern_task.task_date.isoformat(),
        "new_done": pattern_task.new_done_count,
        "new_total": new_total,
        "review_done": pattern_task.review_done_count,
        "review_total": review_total,
        "completion_rate": pattern_task.completion_rate,
        "is_completed": pattern_task.is_completed,
    }
    return {
        "word": {"today": word_today, "stats": word_stats()},
        "patterns": {"today": pattern_today, "stats": sentence_stats()},
    }
