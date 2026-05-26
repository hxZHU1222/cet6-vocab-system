from __future__ import annotations
from sqlalchemy import inspect, text
from ..extensions import db

# db.create_all 只会建新表，不会给旧表自动补字段；P10.2 用这个做轻量升级。
TYPE_SQL = {
    "int": "INTEGER",
    "str": "VARCHAR(255)",
    "text": "TEXT",
    "bool": "BOOLEAN",
    "float": "FLOAT",
    "date": "DATE",
    "datetime": "DATETIME",
}

MISSING_COLUMNS = {
    "word_progress": {
        "dictation_wrong_count": "int",
        "correct_streak": "int",
        "active_weak": "bool",
        "active_wrong": "bool",
        "last_wrong_at": "datetime",
        "last_wrong_answer": "str",
        "mastered_at": "datetime",
    },
    "daily_tasks": {
        "new_done_count": "int",
        "review_done_count": "int",
        "dictation_done_count": "int",
    },
    "daily_task_items": {
        "round1_done": "bool",
        "dictation_done": "bool",
        "dictation_correct": "bool",
    },
    "study_logs": {
        "target_type": "str",
        "target_id": "int",
        "source": "str",
    },
}

def upgrade_schema() -> dict:
    """Best-effort schema patch for SQLite/MySQL existing installs."""
    db.create_all()
    inspector = inspect(db.engine)
    added = []
    existing_tables = set(inspector.get_table_names())
    for table, cols in MISSING_COLUMNS.items():
        if table not in existing_tables:
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        for col, typ in cols.items():
            if col in existing_cols:
                continue
            ddl_type = TYPE_SQL[typ]
            default = " DEFAULT 0" if typ in {"int", "bool", "float"} else ""
            sql = f"ALTER TABLE {table} ADD COLUMN {col} {ddl_type}{default}"
            db.session.execute(text(sql))
            added.append(f"{table}.{col}")
    # 兼容 P8/P9 旧库：study_logs 可能还保留 word_id，而新版使用 target_type/target_id。
    existing_tables = set(inspector.get_table_names())
    if "study_logs" in existing_tables:
        refreshed_cols = {c["name"] for c in inspect(db.engine).get_columns("study_logs")}
        if "word_id" in refreshed_cols and "target_id" in refreshed_cols:
            try:
                db.session.execute(text("""
                    UPDATE study_logs
                    SET target_type = COALESCE(target_type, 'word'),
                        target_id = word_id
                    WHERE target_id IS NULL
                """))
            except Exception:
                # SQLite/MySQL 旧结构差异较多，这里做 best-effort，不阻塞升级。
                pass
    db.session.commit()
    return {"added_columns": added, "count": len(added)}
