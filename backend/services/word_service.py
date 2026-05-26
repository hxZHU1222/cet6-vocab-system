from __future__ import annotations
import csv, io, random
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import func, or_, select
from ..extensions import db
from ..models import Word, WordProgress, DailyTask, DailyTaskItem, StudyLog
from .p10_state_service import ensure_word_progress, apply_word_grade, apply_word_dictation_result


def _clean(v) -> str:
    return str(v or "").strip()


def import_words_from_csv(file_or_path) -> dict:
    """导入词库 CSV：word, phonetic, meaning_cn, example_en, example_cn, tag, source_order。"""
    if isinstance(file_or_path, (str, Path)):
        raw = Path(file_or_path).read_text(encoding="utf-8-sig")
    else:
        data = file_or_path.read()
        raw = data.decode("utf-8-sig") if isinstance(data, bytes) else data
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or "word" not in reader.fieldnames:
        raise ValueError("CSV 至少需要 word 字段。")
    inserted = updated = skipped = 0
    errors = []
    for idx, row in enumerate(reader, start=2):
        word_text = _clean(row.get("word"))
        if not word_text:
            skipped += 1
            errors.append(f"第 {idx} 行缺少 word")
            continue
        word = Word.query.filter(func.lower(Word.word) == word_text.lower()).first()
        if not word:
            word = Word(word=word_text)
            db.session.add(word)
            inserted += 1
        else:
            updated += 1
        word.phonetic = _clean(row.get("phonetic"))
        word.meaning_cn = _clean(row.get("meaning_cn")) or _clean(row.get("meaning"))
        word.example_en = _clean(row.get("example_en"))
        word.example_cn = _clean(row.get("example_cn"))
        word.tag = _clean(row.get("tag")) or "CET6"
        try:
            word.source_order = int(_clean(row.get("source_order")) or 0)
        except ValueError:
            word.source_order = 0
    db.session.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors[:20]}


def serialize_word(word: Word) -> dict:
    p = WordProgress.query.filter_by(word_id=word.id).first()
    return {
        "id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "meaning_cn": word.meaning_cn,
        "example_en": word.example_en,
        "example_cn": word.example_cn,
        "tag": word.tag,
        "source_order": word.source_order,
        "progress": {
            "familiarity": p.familiarity if p else None,
            "seen_count": p.seen_count if p else 0,
            "correct_count": p.correct_count if p else 0,
            "dictation_wrong_count": p.dictation_wrong_count if p else 0,
            "correct_streak": p.correct_streak if p else 0,
            "active_weak": bool(p.active_weak) if p else False,
            "active_wrong": bool(p.active_wrong) if p else False,
            "is_mastered": bool(p.is_mastered) if p else False,
            "next_review_date": p.next_review_date.isoformat() if p and p.next_review_date else None,
        }
    }


def get_or_create_today_task(new_target: int = 100, dictation_target: int = 20, review_limit: int = 80) -> DailyTask:
    today = date.today()
    task = DailyTask.query.filter_by(task_date=today).first()
    if task:
        update_daily_task_progress(task.id)
        return task
    task = DailyTask(task_date=today, new_target_count=new_target, dictation_target_count=dictation_target)
    db.session.add(task)
    db.session.flush()

    # 到期复习：明确排除熟词。
    review_rows = WordProgress.query.join(Word).filter(
        WordProgress.is_mastered.is_(False),
        WordProgress.familiarity != 3,
        WordProgress.next_review_date.isnot(None),
        WordProgress.next_review_date <= today,
    ).order_by(WordProgress.next_review_date.asc(), Word.source_order.asc(), Word.id.asc()).limit(review_limit).all()
    for p in review_rows:
        db.session.add(DailyTaskItem(daily_task_id=task.id, word_id=p.word_id, item_type="review"))

    # 新词：没有进度或 seen_count=0 的词。
    sub_seen = select(WordProgress.word_id).filter(WordProgress.seen_count > 0)
    new_words = Word.query.filter(~Word.id.in_(sub_seen)).order_by(Word.source_order.asc(), Word.id.asc()).limit(new_target).all()
    for w in new_words:
        exists = DailyTaskItem.query.filter_by(daily_task_id=task.id, word_id=w.id).first()
        if not exists:
            db.session.add(DailyTaskItem(daily_task_id=task.id, word_id=w.id, item_type="new"))

    # 默写候选初始池：活跃错词/弱词优先；今日新词学习后也会动态加入候选，不强制固定死。
    dict_words = pick_dictation_words(mode="today", limit=dictation_target, exclude_today_correct=True)
    for w in dict_words:
        exists = DailyTaskItem.query.filter_by(daily_task_id=task.id, word_id=w.id, item_type="dictation").first()
        if not exists:
            db.session.add(DailyTaskItem(daily_task_id=task.id, word_id=w.id, item_type="dictation"))
    db.session.commit()
    update_daily_task_progress(task.id)
    return task


def update_daily_task_progress(task_id: int) -> DailyTask:
    task = DailyTask.query.get(task_id)
    if not task:
        raise ValueError("daily task not found")
    items = DailyTaskItem.query.filter_by(daily_task_id=task.id).all()
    new_total = len([i for i in items if i.item_type == "new"])
    review_total = len([i for i in items if i.item_type == "review"])
    dict_total = max(task.dictation_target_count or 20, len([i for i in items if i.item_type == "dictation"]))
    new_done = len([i for i in items if i.item_type == "new" and i.status == "done"])
    review_done = len([i for i in items if i.item_type == "review" and i.status == "done"])
    dict_done = len([i for i in items if i.item_type == "dictation" and i.dictation_done])
    task.new_done_count = new_done
    task.review_done_count = review_done
    task.dictation_done_count = dict_done
    task.review_target_count = review_total
    parts = []
    if new_total:
        parts.append(new_done / new_total)
    if review_total:
        parts.append(review_done / review_total)
    parts.append(min(dict_done / max(task.dictation_target_count or 20, 1), 1.0))
    task.completion_rate = round(sum(parts) / len(parts) * 100, 1) if parts else 0.0
    task.is_completed = (new_total == 0 or new_done >= new_total) and (review_total == 0 or review_done >= review_total) and dict_done >= (task.dictation_target_count or 20)
    if task.is_completed and not task.completed_at:
        task.completed_at = datetime.utcnow()
    db.session.commit()
    return task


def mark_today_word_done(word_id: int, item_types=("new", "review"), grade=None):
    task = DailyTask.query.filter_by(task_date=date.today()).first()
    if not task:
        return
    items = DailyTaskItem.query.filter(
        DailyTaskItem.daily_task_id == task.id,
        DailyTaskItem.word_id == word_id,
        DailyTaskItem.item_type.in_(list(item_types)),
    ).all()
    for item in items:
        item.status = "done"
        item.round1_done = True
        if grade is not None:
            item.user_grade = grade
    db.session.commit()
    update_daily_task_progress(task.id)


def grade_word_and_mark(word_id: int, grade: int, source: str = "study") -> WordProgress:
    progress = apply_word_grade(word_id, grade, source)
    mark_today_word_done(word_id, ("new", "review"), grade)
    return progress


def pick_study_words(mode: str = "today_new", limit: int = 100) -> list[Word]:
    limit = max(1, min(int(limit or 100), 300))
    today_task = get_or_create_today_task()
    q = Word.query
    if mode == "today_review":
        ids = [i.word_id for i in DailyTaskItem.query.filter_by(daily_task_id=today_task.id, item_type="review").filter(DailyTaskItem.status != "done").all()]
        return Word.query.filter(Word.id.in_(ids or [0])).order_by(Word.source_order.asc(), Word.id.asc()).limit(limit).all()
    if mode == "weak":
        return Word.query.join(WordProgress).filter(WordProgress.active_weak.is_(True), WordProgress.is_mastered.is_(False)).order_by(WordProgress.last_seen_at.asc()).limit(limit).all()
    if mode == "wrong":
        return Word.query.join(WordProgress).filter(WordProgress.active_wrong.is_(True), WordProgress.is_mastered.is_(False)).order_by(WordProgress.last_wrong_at.desc()).limit(limit).all()
    if mode == "mastered":
        return Word.query.join(WordProgress).filter(WordProgress.is_mastered.is_(True)).order_by(func.random()).limit(limit).all()
    if mode == "random":
        return Word.query.order_by(func.random()).limit(limit).all()
    if mode == "preview":
        sub_seen = select(WordProgress.word_id).filter(WordProgress.seen_count > 0)
        return Word.query.filter(~Word.id.in_(sub_seen)).order_by(Word.source_order.asc(), Word.id.asc()).limit(limit).all()
    # today_new 默认：只取今日未完成新词；100 个完成后不阻止自由练习，前端给入口。
    ids = [i.word_id for i in DailyTaskItem.query.filter_by(daily_task_id=today_task.id, item_type="new").filter(DailyTaskItem.status != "done").all()]
    return Word.query.filter(Word.id.in_(ids or [0])).order_by(Word.source_order.asc(), Word.id.asc()).limit(limit).all()


def pick_dictation_words(mode: str = "today", limit: int = 20, exclude_today_correct: bool = True) -> list[Word]:
    limit = max(1, min(int(limit or 20), 100))
    q = Word.query.outerjoin(WordProgress)
    q = q.filter(or_(WordProgress.is_mastered.is_(False), WordProgress.id.is_(None)))
    if exclude_today_correct:
        today_start = datetime.combine(date.today(), datetime.min.time())
        correct_ids = select(StudyLog.target_id).filter(
            StudyLog.target_type == "word",
            StudyLog.action_type == "dictation",
            StudyLog.result == "correct",
            StudyLog.created_at >= today_start,
        )
        q = q.filter(~Word.id.in_(correct_ids))
    if mode == "wrong":
        q = q.filter(WordProgress.active_wrong.is_(True)).order_by(WordProgress.last_wrong_at.desc(), WordProgress.dictation_wrong_count.desc())
    elif mode == "weak":
        q = q.filter(WordProgress.active_weak.is_(True)).order_by(WordProgress.last_seen_at.asc())
    elif mode == "learned":
        q = q.filter(WordProgress.seen_count > 0).order_by(func.random())
    elif mode == "random":
        q = q.order_by(func.random())
    else:
        # 今日最低默写：A 今日弱词/B活跃错词/C今日新词未默写，排除熟词和今日已正确。
        today_task = DailyTask.query.filter_by(task_date=date.today()).first()
        candidates = []
        if today_task:
            today_ids = [i.word_id for i in DailyTaskItem.query.filter_by(daily_task_id=today_task.id).all()]
            if today_ids:
                candidates = Word.query.outerjoin(WordProgress).filter(
                    Word.id.in_(today_ids),
                    or_(WordProgress.active_weak.is_(True), WordProgress.active_wrong.is_(True), WordProgress.id.is_(None), WordProgress.is_mastered.is_(False)),
                    or_(WordProgress.is_mastered.is_(False), WordProgress.id.is_(None)),
                ).order_by(WordProgress.active_wrong.desc(), WordProgress.active_weak.desc(), Word.source_order.asc()).limit(limit).all()
        if len(candidates) >= limit:
            return candidates[:limit]
        existing = {w.id for w in candidates}
        more = q.filter(or_(WordProgress.active_wrong.is_(True), WordProgress.active_weak.is_(True))).filter(~Word.id.in_(existing or [0])).order_by(WordProgress.active_wrong.desc(), WordProgress.active_weak.desc(), WordProgress.last_wrong_at.desc()).limit(limit - len(candidates)).all()
        return candidates + more
    return q.limit(limit).all()


def submit_dictation(word_id: int, answer: str, source: str = "dictation") -> dict:
    word = Word.query.get_or_404(word_id)
    normalized = (answer or "").strip().lower()
    correct = word.word.strip().lower()
    is_correct = normalized == correct
    progress = apply_word_dictation_result(word_id, is_correct, answer, source)
    task = DailyTask.query.filter_by(task_date=date.today()).first()
    if task:
        item = DailyTaskItem.query.filter_by(daily_task_id=task.id, word_id=word_id, item_type="dictation").first()
        if not item:
            item = DailyTaskItem(daily_task_id=task.id, word_id=word_id, item_type="dictation")
            db.session.add(item)
        item.status = "done"
        item.dictation_done = True
        item.dictation_correct = is_correct
        db.session.commit()
        update_daily_task_progress(task.id)
    return {
        "ok": True,
        "word": serialize_word(word),
        "is_correct": is_correct,
        "correct_answer": word.word,
        "user_answer": answer,
        "active_wrong": progress.active_wrong,
        "correct_streak": progress.correct_streak,
    }


def word_stats() -> dict:
    total = Word.query.count()
    seen = WordProgress.query.filter(WordProgress.seen_count > 0).count()
    unlearned = max(total - seen, 0)
    mastered = WordProgress.query.filter_by(is_mastered=True).count()
    weak = WordProgress.query.filter(
        WordProgress.seen_count > 0,
        WordProgress.is_mastered.is_(False),
        or_(WordProgress.active_weak.is_(True), WordProgress.familiarity.in_([0, 1])),
    ).count()
    semi = WordProgress.query.filter(
        WordProgress.seen_count > 0,
        WordProgress.is_mastered.is_(False),
        WordProgress.familiarity == 2,
    ).count()
    active_wrong = WordProgress.query.filter(
        WordProgress.active_wrong.is_(True),
        WordProgress.is_mastered.is_(False),
    ).count()
    due_review = WordProgress.query.filter(
        WordProgress.is_mastered.is_(False),
        WordProgress.next_review_date.isnot(None),
        WordProgress.next_review_date <= date.today(),
    ).count()
    fam_rows = db.session.query(WordProgress.familiarity, func.count(WordProgress.id)).filter(
        WordProgress.seen_count > 0
    ).group_by(WordProgress.familiarity).all()
    fam = {str(k): v for k, v in fam_rows}
    task = DailyTask.query.filter_by(task_date=date.today()).first()
    today = None
    if task:
        update_daily_task_progress(task.id)
        new_total = DailyTaskItem.query.filter_by(daily_task_id=task.id, item_type="new").count()
        review_total = DailyTaskItem.query.filter_by(daily_task_id=task.id, item_type="review").count()
        today = {
            "task_date": task.task_date.isoformat(),
            "new_done": task.new_done_count,
            "new_total": new_total,
            "review_done": task.review_done_count,
            "review_total": review_total,
            "dictation_done": task.dictation_done_count,
            "dictation_target": task.dictation_target_count,
            "completion_rate": task.completion_rate,
            "is_completed": task.is_completed,
        }
    return {
        "total": total,
        "seen": seen,
        "learned": seen,
        "unlearned": unlearned,
        "mastered": mastered,
        "weak": weak,
        "semi": semi,
        "active_wrong": active_wrong,
        "due_review": due_review,
        "familiarity": fam,
        "distribution": {
            "unlearned": unlearned,
            "weak": weak,
            "semi": semi,
            "mastered": mastered,
        },
        "today": today,
    }


def today_word_dashboard(new_target=100, dictation_target=20, review_limit=80) -> dict:
    task = get_or_create_today_task(new_target, dictation_target, review_limit)
    stats = word_stats()
    return stats["today"] or {}
