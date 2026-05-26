from __future__ import annotations
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_INSTANCE_DIR = BASE_DIR / "instance"
PROJECT_INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(BASE_DIR / "backend" / ".env")

def _normalize_database_url(raw: str | None) -> str:
    """Normalize local sqlite URLs so Windows/PowerShell runs do not depend on cwd.

    The old .env.example used DATABASE_URL=sqlite:///instance/cet6_vocab.db.
    SQLAlchemy treats that as a relative path; if the empty instance folder was
    not included in the ZIP, sqlite raised: unable to open database file.
    Here we resolve relative sqlite paths against the project root.
    """
    if not raw:
        return f"sqlite:///{(PROJECT_INSTANCE_DIR / 'cet6_vocab.db').as_posix()}"
    if raw.startswith("sqlite:///") and not raw.startswith("sqlite:////"):
        path_part = raw[len("sqlite:///"):]
        # Keep absolute Windows paths such as C:/... or C:\...
        is_windows_abs = len(path_part) >= 3 and path_part[1] == ":" and path_part[2] in {"/", "\\"}
        p = Path(path_part)
        if not p.is_absolute() and not is_windows_abs:
            resolved = (BASE_DIR / p).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{resolved.as_posix()}"
    return raw

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    APP_PASSWORD = os.getenv("APP_PASSWORD", "cet6-local")
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Shanghai")
    DAILY_NEW_WORDS = int(os.getenv("DAILY_NEW_WORDS", "100"))
    DAILY_DICTATION_WORDS = int(os.getenv("DAILY_DICTATION_WORDS", "20"))
    DAILY_REVIEW_WORD_LIMIT = int(os.getenv("DAILY_REVIEW_WORD_LIMIT", "80"))
    DAILY_NEW_PATTERNS = int(os.getenv("DAILY_NEW_PATTERNS", "5"))
    DAILY_REVIEW_PATTERNS = int(os.getenv("DAILY_REVIEW_PATTERNS", "5"))
    PERMANENT_SESSION_LIFETIME = timedelta(days=90)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    STATIC_VERSION = "p10_2_6"
