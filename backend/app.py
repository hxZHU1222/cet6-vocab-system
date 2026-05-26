from __future__ import annotations
from pathlib import Path
import click
from flask import Flask, current_app, jsonify, redirect, request, session, url_for
from .config import Config
from .extensions import db
from .routes.auth_routes import auth_bp
from .routes.page_routes import pages_bp
from .routes.sentence_pattern_routes import sentence_bp
from .routes.study_routes import study_bp
from .routes.word_routes import word_bp
from .routes.dashboard_routes import dashboard_bp
from .services.sentence_pattern_service import import_sentence_patterns_from_csv
from .services.word_service import import_words_from_csv
from .services.schema_service import upgrade_schema
from .services.maintenance_service import reset_word_learning_records, reset_all_learning_records, export_words_to_csv
from .services.learning_snapshot_service import export_learning_snapshot, import_learning_snapshot, learning_status


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    (Path(app.root_path).parent / "instance").mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(sentence_bp)
    app.register_blueprint(word_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(study_bp)  # 兼容旧接口 /api/study/*

    @app.before_request
    def require_login():
        if not current_app.config.get("AUTH_ENABLED", True):
            return None
        public_endpoints = {"auth.login", "static", "health"}
        if request.endpoint in public_endpoints or (request.endpoint or "").startswith("static"):
            return None
        if session.get("authenticated"):
            return None
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "未登录"}), 401
        return redirect(url_for("auth.login", next=request.full_path))


    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": exc.description, "status_code": exc.code}), exc.code
            return exc
        current_app.logger.exception("Unhandled exception: %s", exc)
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "服务器内部错误。请查看 Flask 终端日志。", "detail": str(exc)}), 500
        raise exc

    @app.get("/health")
    def health():
        try:
            db.session.execute(db.text("SELECT 1"))
            database = "ok"
        except Exception as exc:
            database = f"error: {exc}"
        return jsonify({
            "status": "ok" if database == "ok" else "degraded",
            "database": database,
            "auth_enabled": current_app.config.get("AUTH_ENABLED", True),
            "module": "P10.2.6 progress persistence + interaction/stats fix",
        })

    @app.cli.command("init-db")
    def init_db_command():
        """Create or upgrade all tables."""
        result = upgrade_schema()
        print("数据库表已初始化/升级。", result)

    @app.cli.command("upgrade-db")
    def upgrade_db_command():
        """Patch existing database columns for P10.2."""
        result = upgrade_schema()
        print("数据库结构升级完成：", result)

    @app.cli.command("import-sample-words")
    def import_sample_words_command():
        """Import bundled small sample word CSV for local smoke test."""
        upgrade_schema()
        path = Path(app.root_path).parent / "data" / "cet6_words_sample.csv"
        result = import_words_from_csv(path)
        print(result)

    @app.cli.command("import-default-words")
    def import_default_words_command():
        """Import the full default CET-6 word CSV if data/cet6_words.csv exists."""
        upgrade_schema()
        path = Path(app.root_path).parent / "data" / "cet6_words.csv"
        if not path.exists():
            print({
                "ok": False,
                "error": "data/cet6_words.csv 不存在。服务器旧库里有词时，请先运行 export-words 导出，或把你的完整词库 CSV 放到 data/cet6_words.csv。",
                "expected_path": str(path),
            })
            return
        result = import_words_from_csv(path)
        print(result)

    @app.cli.command("import-default-sentence-patterns")
    def import_default_sentence_patterns_command():
        """Import bundled P10 sentence pattern CSV."""
        upgrade_schema()
        path = Path(app.root_path).parent / "data" / "cet6_sentence_patterns_import.csv"
        result = import_sentence_patterns_from_csv(path)
        print(result)


    @app.cli.command("reset-word-learning")
    def reset_word_learning_command():
        """Delete old word progress/tasks/logs, but keep the word library."""
        upgrade_schema()
        result = reset_word_learning_records()
        print("词汇学习记录已清空；词库已保留：", result)

    @app.cli.command("reset-all-learning")
    def reset_all_learning_command():
        """Delete all progress/tasks/logs, but keep words and sentence patterns."""
        upgrade_schema()
        result = reset_all_learning_records()
        print("全部学习记录已清空；词库和句型库已保留：", result)

    @app.cli.command("export-words")
    def export_words_command():
        """Export current word library to exports/cet6_words_export_*.csv."""
        upgrade_schema()
        result = export_words_to_csv()
        print("词库已导出：", result)


    @app.cli.command("export-learning-snapshot")
    def export_learning_snapshot_command():
        """Export learning progress/tasks/logs to exports/learning_snapshot_*.zip."""
        upgrade_schema()
        result = export_learning_snapshot()
        print("学习快照已导出：", result)

    @app.cli.command("import-learning-snapshot")
    @click.argument("snapshot_path")
    def import_learning_snapshot_command(snapshot_path):
        """Import learning progress/tasks/logs from a snapshot zip."""
        upgrade_schema()
        result = import_learning_snapshot(snapshot_path)
        print("学习快照已恢复：", result)

    @app.cli.command("learning-status")
    def learning_status_command():
        """Print P10.2.6 learning progress status."""
        upgrade_schema()
        print(learning_status())

    @app.cli.command("p10-status")
    def p10_status_command():
        from .services.dashboard_service import merged_dashboard
        upgrade_schema()
        print(merged_dashboard())

    @app.cli.command("library-status")
    def library_status_command():
        """Print library counts without resetting learning records."""
        from .models import Word, SentencePattern, WordProgress, StudyLog
        upgrade_schema()
        print({
            "words": Word.query.count(),
            "sentence_patterns": SentencePattern.query.count(),
            "word_progress_records": WordProgress.query.count(),
            "study_logs": StudyLog.query.count(),
        })

    return app
