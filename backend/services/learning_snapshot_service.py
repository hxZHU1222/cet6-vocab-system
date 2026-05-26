from __future__ import annotations

import csv
import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from sqlalchemy import inspect, Table, MetaData
from sqlalchemy.sql.sqltypes import Integer, Boolean, Date, DateTime, Float
from ..extensions import db
from ..models import (
    Word,
    WordProgress,
    DailyTask,
    DailyTaskItem,
    StudyLog,
    SentencePattern,
    SentencePatternProgress,
    DailyPatternTask,
    DailyPatternTaskItem,
)

SNAPSHOT_TABLES = [
    "word_progress",
    "daily_tasks",
    "daily_task_items",
    "study_logs",
    "sentence_pattern_progress",
    "daily_pattern_tasks",
    "daily_pattern_task_items",
]

MODEL_MAP = {
    "word_progress": WordProgress,
    "daily_tasks": DailyTask,
    "daily_task_items": DailyTaskItem,
    "study_logs": StudyLog,
    "sentence_pattern_progress": SentencePatternProgress,
    "daily_pattern_tasks": DailyPatternTask,
    "daily_pattern_task_items": DailyPatternTaskItem,
}


def _exports_dir() -> Path:
    root = Path.cwd() / "exports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _coerce_value(value: str, column) -> Any:
    if value == "":
        return None
    typ = column.type
    if isinstance(typ, Integer):
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(typ, Boolean):
        return str(value).lower() in {"1", "true", "yes", "on", "t"}
    if isinstance(typ, Float):
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(typ, DateTime):
        v = value.replace("T", " ")
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            return None
    if isinstance(typ, Date):
        try:
            return date.fromisoformat(value.split(" ")[0])
        except ValueError:
            return None
    return value


def learning_status() -> dict:
    today = date.today()
    word_task = DailyTask.query.filter_by(task_date=today).first()
    pattern_task = DailyPatternTask.query.filter_by(task_date=today).first()
    seen_words = WordProgress.query.filter(WordProgress.seen_count > 0).count()
    return {
        "words": Word.query.count(),
        "seen_words": seen_words,
        "unseen_words": max(Word.query.count() - seen_words, 0),
        "mastered_words": WordProgress.query.filter_by(is_mastered=True).count(),
        "weak_words": WordProgress.query.filter(WordProgress.seen_count > 0, WordProgress.active_weak.is_(True), WordProgress.is_mastered.is_(False)).count(),
        "active_wrong_words": WordProgress.query.filter(WordProgress.active_wrong.is_(True), WordProgress.is_mastered.is_(False)).count(),
        "sentence_patterns": SentencePattern.query.count(),
        "seen_patterns": SentencePatternProgress.query.filter(SentencePatternProgress.seen_count > 0).count(),
        "mastered_patterns": SentencePatternProgress.query.filter_by(is_mastered=True).count(),
        "study_logs": StudyLog.query.count(),
        "today_word": None if not word_task else {
            "date": word_task.task_date.isoformat(),
            "new_done": word_task.new_done_count,
            "new_target": word_task.new_target_count,
            "review_done": word_task.review_done_count,
            "review_target": word_task.review_target_count,
            "dictation_done": word_task.dictation_done_count,
            "dictation_target": word_task.dictation_target_count,
            "completion_rate": word_task.completion_rate,
        },
        "today_pattern": None if not pattern_task else {
            "date": pattern_task.task_date.isoformat(),
            "new_done": pattern_task.new_done_count,
            "new_target": pattern_task.new_target_count,
            "review_done": pattern_task.review_done_count,
            "review_target": pattern_task.review_target_count,
            "completion_rate": pattern_task.completion_rate,
        },
    }


def export_learning_snapshot(output_path: str | Path | None = None) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_path is None:
        output_path = _exports_dir() / f"learning_snapshot_{timestamp}.zip"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "version": "p10_2_6",
            "tables": SNAPSHOT_TABLES,
            "status": learning_status(),
        }
        zf.writestr("library_status.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for table_name in SNAPSHOT_TABLES:
            model = MODEL_MAP[table_name]
            columns = [c.name for c in model.__table__.columns]
            rows = model.query.order_by(model.id.asc()).all()
            temp = output_path.parent / f".{table_name}_{timestamp}.csv"
            with temp.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for row in rows:
                    writer.writerow({col: _stringify(getattr(row, col, None)) for col in columns})
            zf.write(temp, f"{table_name}.csv")
            temp.unlink(missing_ok=True)
    return {"ok": True, "path": str(output_path), "status": learning_status()}


def import_learning_snapshot(zip_path: str | Path) -> dict:
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"snapshot not found: {zip_path}")

    metadata = MetaData()
    metadata.reflect(bind=db.engine)
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    restored = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        # 先清空子表，再清空父表；恢复时按父表到子表。
        delete_order = [
            "daily_task_items",
            "daily_tasks",
            "daily_pattern_task_items",
            "daily_pattern_tasks",
            "word_progress",
            "sentence_pattern_progress",
            "study_logs",
        ]
        for table_name in delete_order:
            if table_name in table_names:
                db.session.execute(metadata.tables[table_name].delete())
        db.session.commit()

        for table_name in SNAPSHOT_TABLES:
            csv_name = f"{table_name}.csv"
            if csv_name not in zf.namelist() or table_name not in table_names:
                restored[table_name] = 0
                continue
            table: Table = metadata.tables[table_name]
            column_map = {c.name: c for c in table.columns}
            raw = zf.read(csv_name).decode("utf-8-sig")
            reader = csv.DictReader(raw.splitlines())
            rows = []
            for row in reader:
                clean = {}
                for key, value in row.items():
                    if key in column_map:
                        clean[key] = _coerce_value(value, column_map[key])
                if clean:
                    rows.append(clean)
            if rows:
                db.session.execute(table.insert(), rows)
            restored[table_name] = len(rows)
        db.session.commit()
    return {"ok": True, "snapshot": str(zip_path), "restored": restored, "status": learning_status()}
