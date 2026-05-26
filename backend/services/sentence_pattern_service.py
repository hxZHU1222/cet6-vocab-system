from __future__ import annotations
import csv
import io
from datetime import datetime, date, timedelta
from pathlib import Path
from sqlalchemy import func, or_
from ..extensions import db
from ..models import SentencePattern, SentencePatternProgress, StudyLog, DailyPatternTask, DailyPatternTaskItem


def _clean(value: object) -> str:
    return str(value or "").strip()


def import_sentence_patterns_from_csv(file_or_path) -> dict:
    """导入 P10 句型 CSV。重复依据 pattern_en 去重，已有则更新。"""
    if isinstance(file_or_path, (str, Path)):
        raw = Path(file_or_path).read_text(encoding="utf-8-sig")
    else:
        data = file_or_path.read()
        raw = data.decode("utf-8-sig") if isinstance(data, bytes) else data
    reader = csv.DictReader(io.StringIO(raw))
    required = {"title", "category", "pattern_en"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"CSV 缺少必要字段：{', '.join(sorted(missing))}")
    inserted = updated = skipped = 0
    errors = []
    for idx, row in enumerate(reader, start=2):
        title = _clean(row.get("title"))
        category = _clean(row.get("category"))
        pattern_en = _clean(row.get("pattern_en"))
        if not title or not category or not pattern_en:
            skipped += 1
            errors.append(f"第 {idx} 行缺少 title/category/pattern_en")
            continue
        pattern = SentencePattern.query.filter(func.lower(SentencePattern.pattern_en) == pattern_en.lower()).first()
        if not pattern:
            pattern = SentencePattern(pattern_en=pattern_en)
            db.session.add(pattern)
            inserted += 1
        else:
            updated += 1
        pattern.title = title
        pattern.category = category
        pattern.pattern_cn = _clean(row.get("pattern_cn"))
        pattern.example_en = _clean(row.get("example_en"))
        pattern.example_cn = _clean(row.get("example_cn"))
        pattern.slots = _clean(row.get("slots"))
        pattern.usage_note = _clean(row.get("usage_note"))
        try:
            pattern.difficulty = int(_clean(row.get("difficulty")) or 2)
        except ValueError:
            pattern.difficulty = 2
        pattern.tag = _clean(row.get("tag")) or "CET6-Writing"
        pattern.source = _clean(row.get("source")) or "P10"
        try:
            pattern.source_order = int(_clean(row.get("source_order")) or 0)
        except ValueError:
            pattern.source_order = 0
    db.session.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors[:20]}


def ensure_sentence_progress(pattern_id: int) -> SentencePatternProgress:
    progress = SentencePatternProgress.query.filter_by(pattern_id=pattern_id).first()
    if not progress:
        progress = SentencePatternProgress(pattern_id=pattern_id)
        db.session.add(progress)
        db.session.flush()
    return progress


def update_today_pattern_task_progress(task_id: int) -> DailyPatternTask:
    task = DailyPatternTask.query.get(task_id)
    if not task:
        raise ValueError("pattern task not found")
    items = DailyPatternTaskItem.query.filter_by(daily_task_id=task.id).all()
    new_total = len([i for i in items if i.item_type == "new"])
    review_total = len([i for i in items if i.item_type == "review"])
    new_done = len([i for i in items if i.item_type == "new" and i.status == "done"])
    review_done = len([i for i in items if i.item_type == "review" and i.status == "done"])
    task.new_done_count = new_done
    task.review_done_count = review_done
    parts = []
    if new_total:
        parts.append(new_done / new_total)
    if review_total:
        parts.append(review_done / review_total)
    task.completion_rate = round(sum(parts) / len(parts) * 100, 1) if parts else 0.0
    task.is_completed = (new_total == 0 or new_done >= new_total) and (review_total == 0 or review_done >= review_total)
    if task.is_completed and not task.completed_at:
        task.completed_at = datetime.utcnow()
    db.session.commit()
    return task


def mark_today_pattern_done(pattern_id: int, grade: int | None = None):
    task = DailyPatternTask.query.filter_by(task_date=date.today()).first()
    if not task:
        return
    items = DailyPatternTaskItem.query.filter_by(daily_task_id=task.id, pattern_id=pattern_id).all()
    for item in items:
        item.status = "done"
        if grade is not None:
            item.user_grade = grade
    db.session.commit()
    update_today_pattern_task_progress(task.id)


def grade_sentence_pattern(pattern_id: int, grade: int, source: str = "pattern_study") -> SentencePatternProgress:
    """句型四级熟悉度：0 不会 / 1 眼熟 / 2 会套用 / 3 熟了。P10.2 不做句型默写。"""
    if grade not in (0, 1, 2, 3):
        raise ValueError("grade must be 0, 1, 2 or 3")
    now = datetime.utcnow()
    progress = ensure_sentence_progress(pattern_id)
    progress.familiarity = grade
    progress.seen_count += 1
    progress.last_seen_at = now
    if grade in (0, 1):
        progress.is_mastered = False
        progress.mastered_at = None
        progress.next_review_date = date.today() + timedelta(days=1)
    elif grade == 2:
        progress.is_mastered = False
        progress.mastered_at = None
        progress.next_review_date = date.today() + timedelta(days=3)
    else:
        progress.is_mastered = True
        progress.mastered_at = now
        progress.next_review_date = None
    db.session.add(StudyLog(target_type="sentence_pattern", target_id=pattern_id, action_type="grade", result=str(grade), source=source))
    db.session.commit()
    mark_today_pattern_done(pattern_id, grade)
    return progress


def sentence_pattern_query(category: str = "", q: str = "", status: str = ""):
    query = SentencePattern.query.outerjoin(SentencePatternProgress)
    if category:
        query = query.filter(SentencePattern.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(SentencePattern.title.like(like), SentencePattern.pattern_en.like(like), SentencePattern.pattern_cn.like(like), SentencePattern.example_en.like(like), SentencePattern.example_cn.like(like)))
    if status == "mastered":
        query = query.filter(SentencePatternProgress.is_mastered.is_(True))
    elif status == "learning":
        query = query.filter(or_(SentencePatternProgress.is_mastered.is_(False), SentencePatternProgress.id.is_(None)))
    elif status == "weak":
        query = query.filter(SentencePatternProgress.familiarity.in_([0, 1]))
    return query.order_by(SentencePattern.source_order.asc(), SentencePattern.id.asc())


def pick_study_patterns(mode: str = "new", limit: int = 5) -> list[SentencePattern]:
    today = date.today()
    limit = max(1, min(int(limit or 5), 50))
    base = SentencePattern.query.outerjoin(SentencePatternProgress)
    if mode == "today_new":
        task = get_or_create_today_pattern_task()
        ids = [i.pattern_id for i in DailyPatternTaskItem.query.filter_by(daily_task_id=task.id, item_type="new").filter(DailyPatternTaskItem.status != "done").all()]
        return SentencePattern.query.filter(SentencePattern.id.in_(ids or [0])).order_by(SentencePattern.source_order.asc()).limit(limit).all()
    if mode == "today_review":
        task = get_or_create_today_pattern_task()
        ids = [i.pattern_id for i in DailyPatternTaskItem.query.filter_by(daily_task_id=task.id, item_type="review").filter(DailyPatternTaskItem.status != "done").all()]
        return SentencePattern.query.filter(SentencePattern.id.in_(ids or [0])).order_by(SentencePattern.source_order.asc()).limit(limit).all()
    if mode == "review":
        base = base.filter(SentencePatternProgress.is_mastered.is_(False), SentencePatternProgress.next_review_date.isnot(None), SentencePatternProgress.next_review_date <= today).order_by(SentencePatternProgress.next_review_date.asc(), SentencePattern.source_order.asc())
    elif mode == "weak":
        base = base.filter(SentencePatternProgress.familiarity.in_([0, 1])).order_by(SentencePatternProgress.last_seen_at.asc())
    elif mode == "all":
        base = base.order_by(func.random())
    else:  # new
        base = base.filter(SentencePatternProgress.id.is_(None)).order_by(SentencePattern.source_order.asc())
    return base.limit(limit).all()


def serialize_pattern(pattern: SentencePattern) -> dict:
    p = pattern.progress
    return {
        "id": pattern.id,
        "title": pattern.title,
        "category": pattern.category,
        "pattern_en": pattern.pattern_en,
        "pattern_cn": pattern.pattern_cn,
        "example_en": pattern.example_en,
        "example_cn": pattern.example_cn,
        "slots": pattern.slots,
        "usage_note": pattern.usage_note,
        "difficulty": pattern.difficulty,
        "tag": pattern.tag,
        "source_order": pattern.source_order,
        "progress": {
            "familiarity": p.familiarity if p else None,
            "seen_count": p.seen_count if p else 0,
            "is_mastered": bool(p.is_mastered) if p else False,
            "next_review_date": p.next_review_date.isoformat() if p and p.next_review_date else None,
        }
    }


def sentence_stats() -> dict:
    total = SentencePattern.query.count()
    mastered = SentencePatternProgress.query.filter_by(is_mastered=True).count()
    seen = SentencePatternProgress.query.count()
    weak = SentencePatternProgress.query.filter(SentencePatternProgress.familiarity.in_([0, 1]), SentencePatternProgress.is_mastered.is_(False)).count()
    due_review = SentencePatternProgress.query.filter(SentencePatternProgress.is_mastered.is_(False), SentencePatternProgress.next_review_date.isnot(None), SentencePatternProgress.next_review_date <= date.today()).count()
    categories = db.session.query(SentencePattern.category, func.count(SentencePattern.id)).group_by(SentencePattern.category).order_by(SentencePattern.category.asc()).all()
    return {
        "total": total,
        "seen": seen,
        "unseen": max(total - seen, 0),
        "mastered": mastered,
        "weak": weak,
        "due_review": due_review,
        "categories": [{"category": c, "count": n} for c, n in categories],
    }


def get_or_create_today_pattern_task(new_target: int = 5, review_target: int = 5) -> DailyPatternTask:
    today = date.today()
    task = DailyPatternTask.query.filter_by(task_date=today).first()
    if task:
        update_today_pattern_task_progress(task.id)
        return task
    task = DailyPatternTask(task_date=today, new_target_count=new_target, review_target_count=review_target)
    db.session.add(task)
    db.session.flush()
    for pattern in pick_study_patterns("review", review_target):
        db.session.add(DailyPatternTaskItem(daily_task_id=task.id, pattern_id=pattern.id, item_type="review"))
    for pattern in pick_study_patterns("new", new_target):
        exists = DailyPatternTaskItem.query.filter_by(daily_task_id=task.id, pattern_id=pattern.id).first()
        if not exists:
            db.session.add(DailyPatternTaskItem(daily_task_id=task.id, pattern_id=pattern.id, item_type="new"))
    db.session.commit()
    update_today_pattern_task_progress(task.id)
    return task
