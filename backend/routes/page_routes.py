from __future__ import annotations
from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/")
def index():
    return render_template("index.html")

@pages_bp.route("/study")
def study():
    return render_template("study.html")

@pages_bp.route("/dictation")
def dictation():
    return render_template("dictation.html")

@pages_bp.route("/words/import")
def words_import():
    return render_template("word_import.html")

@pages_bp.route("/patterns")
def patterns():
    return render_template("sentence_patterns.html")

@pages_bp.route("/patterns/study")
def patterns_study():
    return render_template("sentence_study.html")

@pages_bp.route("/patterns/import")
def patterns_import():
    return render_template("sentence_import.html")

@pages_bp.route("/stats")
def stats():
    return render_template("stats.html")
