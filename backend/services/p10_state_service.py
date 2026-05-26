from __future__ import annotations
from datetime import datetime, date, timedelta
from ..extensions import db
from ..models import WordProgress, StudyLog


def ensure_word_progress(word_id: int) -> WordProgress:
    progress = WordProgress.query.filter_by(word_id=word_id).first()
    if not progress:
        progress = WordProgress(word_id=word_id)
        db.session.add(progress)
        db.session.flush()
    return progress


def apply_word_grade(word_id: int, grade: int, source: str = "study") -> WordProgress:
    """四按钮规则：不认识/眼熟=弱词；熟了=退出每日强制复习。"""
    if grade not in (0, 1, 2, 3):
        raise ValueError("grade must be 0, 1, 2 or 3")
    now = datetime.utcnow()
    progress = ensure_word_progress(word_id)
    progress.familiarity = grade
    progress.seen_count = (progress.seen_count or 0) + 1
    progress.last_seen_at = now
    if grade in (0, 1):
        progress.is_mastered = False
        progress.mastered_at = None
        progress.active_weak = True
        progress.next_review_date = date.today() + timedelta(days=1)
        result = "weak"
    elif grade == 2:
        progress.is_mastered = False
        progress.mastered_at = None
        progress.active_weak = False
        progress.next_review_date = date.today() + timedelta(days=3)
        result = "recognized"
    else:
        progress.is_mastered = True
        progress.mastered_at = now
        progress.active_weak = False
        progress.active_wrong = False
        progress.next_review_date = None
        result = "mastered"
    db.session.add(StudyLog(
        target_type="word",
        target_id=word_id,
        action_type="grade",
        result=str(grade),
        source=source,
    ))
    db.session.commit()
    return progress


def apply_word_dictation_result(word_id: int, is_correct: bool, user_answer: str = "", source: str = "dictation") -> WordProgress:
    """默写错误才进入 active_wrong；连续正确 2 次退出活跃错词。"""
    now = datetime.utcnow()
    progress = ensure_word_progress(word_id)
    progress.last_seen_at = now
    if is_correct:
        progress.correct_count = (progress.correct_count or 0) + 1
        progress.correct_streak = (progress.correct_streak or 0) + 1
        if progress.correct_streak >= 2:
            progress.active_wrong = False
        result = "correct"
    else:
        progress.wrong_count = (progress.wrong_count or 0) + 1
        progress.dictation_wrong_count = (progress.dictation_wrong_count or 0) + 1
        progress.correct_streak = 0
        progress.active_wrong = True
        progress.active_weak = True
        progress.familiarity = min(progress.familiarity or 0, 1)
        progress.is_mastered = False
        progress.mastered_at = None
        progress.last_wrong_at = now
        progress.last_wrong_answer = (user_answer or "")[:255]
        progress.next_review_date = date.today() + timedelta(days=1)
        result = "wrong"
    db.session.add(StudyLog(
        target_type="word",
        target_id=word_id,
        action_type="dictation",
        result=result,
        user_answer=user_answer or "",
        source=source,
    ))
    db.session.commit()
    return progress
