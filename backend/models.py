from __future__ import annotations
from datetime import datetime, date
from .extensions import db

class Word(db.Model):
    __tablename__ = "words"
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(128), unique=True, nullable=False, index=True)
    phonetic = db.Column(db.String(128), default="")
    meaning_cn = db.Column(db.Text, default="")
    example_en = db.Column(db.Text, default="")
    example_cn = db.Column(db.Text, default="")
    tag = db.Column(db.String(64), default="CET6")
    source_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WordProgress(db.Model):
    """P10.2 词汇状态模型。熟悉度、弱词、错词、复习计划分离。"""
    __tablename__ = "word_progress"
    id = db.Column(db.Integer, primary_key=True)
    word_id = db.Column(db.Integer, db.ForeignKey("words.id"), unique=True, nullable=False, index=True)
    familiarity = db.Column(db.Integer, default=0)  # 0 不认识 / 1 眼熟 / 2 认识 / 3 熟了
    seen_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)  # 历史兼容字段
    dictation_wrong_count = db.Column(db.Integer, default=0)
    correct_streak = db.Column(db.Integer, default=0)
    active_weak = db.Column(db.Boolean, default=False)   # 主观弱词：不认识/眼熟
    active_wrong = db.Column(db.Boolean, default=False)  # 客观错词：默写错误
    last_seen_at = db.Column(db.DateTime)
    last_wrong_at = db.Column(db.DateTime)
    last_wrong_answer = db.Column(db.String(255), default="")
    next_review_date = db.Column(db.Date)
    is_mastered = db.Column(db.Boolean, default=False)
    mastered_at = db.Column(db.DateTime)
    word = db.relationship("Word")

class DailyTask(db.Model):
    __tablename__ = "daily_tasks"
    id = db.Column(db.Integer, primary_key=True)
    task_date = db.Column(db.Date, default=date.today, unique=True, index=True)
    new_target_count = db.Column(db.Integer, default=100)
    review_target_count = db.Column(db.Integer, default=0)
    dictation_target_count = db.Column(db.Integer, default=20)
    new_done_count = db.Column(db.Integer, default=0)
    review_done_count = db.Column(db.Integer, default=0)
    dictation_done_count = db.Column(db.Integer, default=0)
    completion_rate = db.Column(db.Float, default=0.0)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class DailyTaskItem(db.Model):
    __tablename__ = "daily_task_items"
    id = db.Column(db.Integer, primary_key=True)
    daily_task_id = db.Column(db.Integer, db.ForeignKey("daily_tasks.id"), nullable=False, index=True)
    word_id = db.Column(db.Integer, db.ForeignKey("words.id"), nullable=False, index=True)
    item_type = db.Column(db.String(32), nullable=False)  # new / review / dictation
    status = db.Column(db.String(32), default="pending")
    round1_done = db.Column(db.Boolean, default=False)
    dictation_done = db.Column(db.Boolean, default=False)
    dictation_correct = db.Column(db.Boolean, default=False)
    user_grade = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    word = db.relationship("Word")

class StudyLog(db.Model):
    __tablename__ = "study_logs"
    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(32), default="word")  # word / sentence_pattern
    target_id = db.Column(db.Integer, nullable=False, index=True)
    action_type = db.Column(db.String(32), nullable=False)
    result = db.Column(db.String(32), default="")
    user_answer = db.Column(db.Text, default="")
    source = db.Column(db.String(64), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class SentencePattern(db.Model):
    __tablename__ = "sentence_patterns"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False, index=True)
    category = db.Column(db.String(64), nullable=False, index=True)
    pattern_en = db.Column(db.Text, nullable=False)
    pattern_cn = db.Column(db.Text, default="")
    example_en = db.Column(db.Text, default="")
    example_cn = db.Column(db.Text, default="")
    slots = db.Column(db.Text, default="")
    usage_note = db.Column(db.Text, default="")
    difficulty = db.Column(db.Integer, default=2)
    tag = db.Column(db.String(64), default="CET6-Writing")
    source = db.Column(db.String(128), default="P10")
    source_order = db.Column(db.Integer, default=0, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.relationship("SentencePatternProgress", back_populates="pattern", uselist=False, cascade="all, delete-orphan")

class SentencePatternProgress(db.Model):
    __tablename__ = "sentence_pattern_progress"
    id = db.Column(db.Integer, primary_key=True)
    pattern_id = db.Column(db.Integer, db.ForeignKey("sentence_patterns.id"), unique=True, nullable=False, index=True)
    familiarity = db.Column(db.Integer, default=0)  # 0 不会 / 1 眼熟 / 2 会套用 / 3 熟了
    seen_count = db.Column(db.Integer, default=0)
    recite_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    wrong_count = db.Column(db.Integer, default=0)
    last_seen_at = db.Column(db.DateTime)
    last_wrong_at = db.Column(db.DateTime)
    next_review_date = db.Column(db.Date)
    is_mastered = db.Column(db.Boolean, default=False)
    mastered_at = db.Column(db.DateTime)
    pattern = db.relationship("SentencePattern", back_populates="progress")

class DailyPatternTask(db.Model):
    __tablename__ = "daily_pattern_tasks"
    id = db.Column(db.Integer, primary_key=True)
    task_date = db.Column(db.Date, default=date.today, unique=True, index=True)
    new_target_count = db.Column(db.Integer, default=5)
    review_target_count = db.Column(db.Integer, default=5)
    new_done_count = db.Column(db.Integer, default=0)
    review_done_count = db.Column(db.Integer, default=0)
    completion_rate = db.Column(db.Float, default=0.0)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class DailyPatternTaskItem(db.Model):
    __tablename__ = "daily_pattern_task_items"
    id = db.Column(db.Integer, primary_key=True)
    daily_task_id = db.Column(db.Integer, db.ForeignKey("daily_pattern_tasks.id"), nullable=False, index=True)
    pattern_id = db.Column(db.Integer, db.ForeignKey("sentence_patterns.id"), nullable=False, index=True)
    item_type = db.Column(db.String(32), nullable=False)  # new / review
    status = db.Column(db.String(32), default="pending")
    user_grade = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
