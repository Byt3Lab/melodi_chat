import os
import json
from pathlib import Path

from core import get_prefix_table
from core.db.base_module_tables import BaseModuleTables

MODULE_NAME = "melodi_chat"
PREFIX_TABLE = get_prefix_table(MODULE_NAME)


class ChatTables(BaseModuleTables):
    """Tables SQL pour le module de messagerie (déprécié, données déportées sur melodi_chat_server)."""
    CONVERSATIONS = f"{PREFIX_TABLE}conversations"
    MESSAGES = f"{PREFIX_TABLE}messages"


SETTINGS_FILE = Path(__file__).parent / "chat_settings.json"

DEFAULT_SERVER_URL = os.environ.get("MELODI_CHAT_SERVER_URL", "http://127.0.0.1:7070")
DEFAULT_SERVER_SECRET = os.environ.get("MELODI_CHAT_SERVER_SECRET", "melodi_chat_secret_789")


def get_chat_settings() -> dict:
    defaults = {
        "server_url": DEFAULT_SERVER_URL,
        "secret": DEFAULT_SERVER_SECRET,
        "scale_mode": "autonome",
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_password": "",
        "db_type": "sqlite",
        "db_name": "chat.db",
        "db_host": "127.0.0.1",
        "db_port": 5450,
        "db_user": "melodi",
        "db_password": "root",
        "db_custom_url": "",
    }
    if SETTINGS_FILE.is_file():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def build_db_url(settings: dict) -> str:
    """Construit l'URL SQLAlchemy asynchrone pour melodi_chat_server selon les réglages."""
    db_type = settings.get("db_type", "sqlite")
    if db_type == "sqlite":
        name = settings.get("db_name") or "chat.db"
        return f"sqlite+aiosqlite:///{name}"
    elif db_type == "postgresql":
        host = settings.get("db_host") or "127.0.0.1"
        port = settings.get("db_port") or 5450
        dbname = settings.get("db_name") or "melodi"
        user = settings.get("db_user") or "melodi"
        pwd = settings.get("db_password") or ""
        auth = f"{user}:{pwd}@" if user or pwd else ""
        return f"postgresql+asyncpg://{auth}{host}:{port}/{dbname}"
    elif db_type == "custom":
        return (settings.get("db_custom_url") or "").strip()
    return "sqlite+aiosqlite:///chat.db"


def save_chat_settings(new_settings: dict) -> dict:
    current = get_chat_settings()
    current.update(new_settings)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[melodi_chat] Erreur sauvegarde settings: {e}")
    return current
