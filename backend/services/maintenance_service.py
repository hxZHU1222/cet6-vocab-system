from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime
from ..extensions import db
from ..models import (
    Word,
    WordProgress,
    DailyTask,
    DailyTaskItem,
    StudyLog,
    SentencePatternProgress,
    DailyPatternTask,
    DailyPatternTaskItem,
)


def _count(model) -> int:
    try:
        return model.query.count()
    except Exception:
        return 0


def reset_word_learning_records() -> dict:
    """Reset word learning progress while keeping the word library itself.

    This is the safe reset for the user's server: it removes old daily tasks,
    word progress, and word study/dictation logs, but keeps all rows in `words`.
    """
    before = {
        "words_kept": _count(Word),
        "word_progress_deleted": _count(WordProgress),
        "daily_task_items_deleted": _count(DailyTaskItem),
        "daily_tasks_deleted": _count(DailyTask),
        "word_logs_deleted": StudyLog.query.filter_by(target_type="word").count(),
    }
    DailyTaskItem.query.delete(synchronize_session=False)
    DailyTask.query.delete(synchronize_session=False)
    WordProgress.query.delete(synchronize_session=False)
    StudyLog.query.filter_by(target_type="word").delete(synchronize_session=False)
    db.session.commit()
    return {"ok": True, "scope": "word_learning_only", **before, "words_after": Word.query.count()}


def reset_all_learning_records() -> dict:
    """Reset all learning progress while keeping word and sentence pattern libraries."""
    before = {
        "words_kept": _count(Word),
        "patterns_kept": 0,
        "word_progress_deleted": _count(WordProgress),
        "daily_task_items_deleted": _count(DailyTaskItem),
        "daily_tasks_deleted": _count(DailyTask),
        "pattern_progress_deleted": _count(SentencePatternProgress),
        "daily_pattern_task_items_deleted": _count(DailyPatternTaskItem),
        "daily_pattern_tasks_deleted": _count(DailyPatternTask),
        "study_logs_deleted": _count(StudyLog),
    }
    try:
        from ..models import SentencePattern
        before["patterns_kept"] = SentencePattern.query.count()
    except Exception:
        before["patterns_kept"] = 0

    DailyTaskItem.query.delete(synchronize_session=False)
    DailyTask.query.delete(synchronize_session=False)
    WordProgress.query.delete(synchronize_session=False)
    DailyPatternTaskItem.query.delete(synchronize_session=False)
    DailyPatternTask.query.delete(synchronize_session=False)
    SentencePatternProgress.query.delete(synchronize_session=False)
    StudyLog.query.delete(synchronize_session=False)
    db.session.commit()
    return {
        "ok": True,
        "scope": "all_learning_records",
        **before,
        "words_after": Word.query.count(),
        "patterns_after": before["patterns_kept"],
    }


def export_words_to_csv(output_path: str | Path | None = None) -> dict:
    """Export the current word library to UTF-8 BOM CSV."""
    if output_path is None:
        output_path = Path("exports") / f"cet6_words_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = Word.query.order_by(Word.source_order.asc(), Word.id.asc()).all()
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["word", "phonetic", "meaning_cn", "example_en", "example_cn", "tag", "source_order"],
        )
        writer.writeheader()
        for w in rows:
            writer.writerow({
                "word": w.word,
                "phonetic": w.phonetic or "",
                "meaning_cn": w.meaning_cn or "",
                "example_en": w.example_en or "",
                "example_cn": w.example_cn or "",
                "tag": w.tag or "CET6",
                "source_order": w.source_order or 0,
            })
    return {"ok": True, "count": len(rows), "path": str(output_path)}
