#!/usr/bin/env python3
# =====================================================================
#   ✦  𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗙𝗜𝗟𝗘 𝗩𝗔𝗨𝗟𝗧  —  TELEGRAM FILE SHARE BOT  ✦
# =====================================================================
#  SETUP
#   1) Configure .env (BOT_TOKEN, ADMIN_IDS, BOT_NAME, DB_PATH=bot_data.db)
#   2) pip install -U -r requirements.txt
#   3) python python.py
# =====================================================================

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import signal
import sqlite3
import sys
import threading
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Register this module as "python" even when executed as "__main__"
# so `import python as bot_core` inside app.py never imports this file twice.
sys.modules.setdefault("python", sys.modules[__name__])

_ROOT_DIR = Path(__file__).resolve().parent


def _load_env_file_fallback(filepath: Path) -> None:
    """Zero-dependency .env / .evn parser so config always loads."""
    if not filepath.exists():
        return
    try:
        for raw_line in filepath.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


try:
    from dotenv import load_dotenv

    if (_ROOT_DIR / ".env").exists():
        load_dotenv(_ROOT_DIR / ".env", override=False)
    if (_ROOT_DIR / ".evn").exists():
        load_dotenv(_ROOT_DIR / ".evn", override=False)
except ImportError:
    _load_env_file_fallback(_ROOT_DIR / ".env")
    _load_env_file_fallback(_ROOT_DIR / ".evn")

try:
    from telegram import (
        BotCommand,
        BotCommandScopeChat,
        ChatAdministratorRights,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        KeyboardButton,
        KeyboardButtonRequestChat,
        ReplyKeyboardMarkup,
        ReplyKeyboardRemove,
        Update,
    )
    from telegram.constants import ParseMode
    from telegram.error import (
        BadRequest,
        Conflict,
        Forbidden,
        InvalidToken,
        NetworkError,
        RetryAfter,
        TelegramError,
        TimedOut,
    )
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        ChatJoinRequestHandler,
        ChatMemberHandler,
        CommandHandler,
        ContextTypes,
        ConversationHandler,
        Defaults,
        MessageHandler,
        filters,
    )

    PTB_AVAILABLE = True
except ImportError:
    PTB_AVAILABLE = False

    class TelegramError(Exception):
        pass

    class Conflict(TelegramError):
        pass

    class BadRequest(TelegramError):
        pass

    class Forbidden(TelegramError):
        pass

    class InvalidToken(TelegramError):
        pass

    class NetworkError(TelegramError):
        pass

    class TimedOut(NetworkError):
        pass

    class RetryAfter(TelegramError):
        def __init__(self, retry_after: float = 5.0):
            super().__init__(f"Flood control exceeded. Retry in {retry_after}s")
            self.retry_after = retry_after

    class ParseMode:
        HTML = "HTML"

    class InlineKeyboardButton:
        def __init__(
            self,
            text: str,
            url: str | None = None,
            callback_data: str | None = None,
            **kwargs: Any,
        ):
            self.text = text
            self.url = url
            self.callback_data = callback_data
            self.api_kwargs = kwargs.get("api_kwargs")

    class InlineKeyboardMarkup:
        def __init__(self, inline_keyboard: list[list[InlineKeyboardButton]]):
            self.inline_keyboard = inline_keyboard

    class KeyboardButton:
        def __init__(self, text: str, request_chat: Any = None):
            self.text = text
            self.request_chat = request_chat

    class KeyboardButtonRequestChat:
        def __init__(self, request_id: int, chat_is_channel: bool, **kwargs: Any):
            self.request_id = request_id
            self.chat_is_channel = chat_is_channel
            self.kwargs = kwargs

    class ChatAdministratorRights:
        def __init__(self, **kwargs: Any):
            self.kwargs = kwargs

    class ReplyKeyboardMarkup:
        def __init__(self, keyboard: Any, **kwargs: Any):
            self.keyboard = keyboard
            self.kwargs = kwargs

    class ReplyKeyboardRemove:
        pass

    class BotCommand:
        def __init__(self, command: str, description: str):
            self.command = command
            self.description = description

    class BotCommandScopeChat:
        def __init__(self, chat_id: int):
            self.chat_id = chat_id

    class Update:
        ALL_TYPES = None

        @staticmethod
        def de_json(data: dict[str, Any], bot: Any) -> Any:
            return data

    class ConversationHandler:
        END = -1

        def __init__(self, **kwargs: Any):
            self.kwargs = kwargs

    class ContextTypes:
        DEFAULT_TYPE = Any

    Application = Any  # type: ignore
    CallbackQueryHandler = CommandHandler = MessageHandler = ChatJoinRequestHandler = ChatMemberHandler = Defaults = filters = Any  # type: ignore

warnings.filterwarnings("ignore", message=".*per_message.*")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Updater").setLevel(logging.CRITICAL)
logging.getLogger("telegram.ext._updater").setLevel(logging.CRITICAL)
logging.getLogger("telegram.ext._utils.networkloop").setLevel(logging.CRITICAL)
logger = logging.getLogger("premium-vault")


# =====================================================================
#  ⚙️ CONFIG (BOT_TOKEN, ADMIN_IDS, BOT_NAME, DB_PATH = bot_data.db)
# =====================================================================
TOKEN_REGEX = re.compile(r"^\d{6,15}:[A-Za-z0-9_-]{30,}$")


def parse_admin_ids(raw: str | list[int] | None) -> list[int]:
    if isinstance(raw, list):
        out: list[int] = []
        for item in raw:
            if isinstance(item, int) or (
                isinstance(item, str) and item.strip().isdigit()
            ):
                val = int(item)
                if val > 0 and val not in out:
                    out.append(val)
        return out
    out = []
    for part in str(raw or "").replace(";", ",").split(","):
        cleaned = part.strip()
        if cleaned.isdigit():
            val = int(cleaned)
            if val > 0 and val not in out:
                out.append(val)
    return out


def validate_bot_token(token: str | None) -> bool:
    t = (token or "").strip()
    if not t:
        return False
    upper = t.upper()
    if any(p in upper for p in ("PASTE", "YOUR_", "ABC...", "EXAMPLE", "PLACEHOLDER")):
        return False
    return bool(TOKEN_REGEX.match(t))


def resolve_db_path(raw_path: str | None) -> str:
    """
    Ensures DB_PATH defaults to 'bot_data.db' and falls back safely to
    local 'bot_data.db' if an unreachable mount path (e.g. /var/data/bot_data.db
    without a mounted Render disk) is provided.
    """
    candidate = (raw_path or "bot_data.db").strip() or "bot_data.db"
    path_obj = Path(candidate)

    if not path_obj.is_absolute():
        target = _ROOT_DIR / path_obj
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            return str(target)
        except OSError:
            return str(_ROOT_DIR / "bot_data.db")

    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if os.access(str(path_obj.parent), os.W_OK):
            return str(path_obj)
    except OSError:
        pass

    fallback = str(_ROOT_DIR / "bot_data.db")
    logger.warning(
        "⚠️ DB_PATH '%s' is not writable on this host; falling back to '%s'",
        candidate,
        fallback,
    )
    return fallback


def resolve_webhook_base_url() -> str:
    """
    Detects if running on a Render Web Service (RENDER_EXTERNAL_URL / RENDER_EXTERNAL_HOSTNAME)
    or custom WEBHOOK_URL. When present, Webhook mode is used so getUpdates Conflict is impossible.
    """
    if os.getenv("USE_POLLING", "").strip().lower() in ("1", "true", "yes"):
        return ""
    for env_key in ("WEBHOOK_URL", "RENDER_EXTERNAL_URL"):
        val = os.getenv(env_key, "").strip().rstrip("/")
        if val.startswith("https://"):
            return val
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip().rstrip("/")
    if host and "." in host:
        return f"https://{host}"
    return ""


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS: list[int] = parse_admin_ids(os.getenv("ADMIN_IDS", "123456789")) or [123456789]
BOT_NAME: str = os.getenv("BOT_NAME", "Premium File Vault").strip() or "Premium File Vault"
RAW_DB_PATH: str = os.getenv("DB_PATH", "bot_data.db").strip() or "bot_data.db"
DB_PATH: str = resolve_db_path(RAW_DB_PATH)

BOT_RUNTIME_STATUS: dict[str, Any] = {
    "mode": "initializing",
    "bot_running": False,
    "bot_username": "",
    "token_valid": validate_bot_token(BOT_TOKEN),
    "ptb_installed": PTB_AVAILABLE,
    "webhook_url": "",
    "conflict_count": 0,
    "last_conflict_at": None,
    "last_error": None,
    "webhook_cleared": False,
    "single_instance_locked": False,
    "started_at": datetime.now(timezone.utc).isoformat(),
}

# Active PTB Application & event loop for webhook delivery
_ACTIVE_PTB_APP: Any = None
_ACTIVE_BOT_LOOP: asyncio.AbstractEventLoop | None = None
_POLLING_COOLDOWN_LOCK = False


def get_active_bot_app() -> tuple[Any, asyncio.AbstractEventLoop | None]:
    return _ACTIVE_PTB_APP, _ACTIVE_BOT_LOOP


def save_env_config(
    bot_token: str | None = None,
    admin_ids: str | list[int] | None = None,
    bot_name: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Updates configuration in memory and writes both .env and .evn."""
    global BOT_TOKEN, ADMIN_IDS, BOT_NAME, RAW_DB_PATH, DB_PATH

    if bot_token is not None:
        BOT_TOKEN = bot_token.strip()
        os.environ["BOT_TOKEN"] = BOT_TOKEN
    if admin_ids is not None:
        parsed_ids = parse_admin_ids(admin_ids)
        if parsed_ids:
            ADMIN_IDS = parsed_ids
            os.environ["ADMIN_IDS"] = ",".join(str(x) for x in ADMIN_IDS)
    if bot_name is not None and bot_name.strip():
        BOT_NAME = bot_name.strip()
        os.environ["BOT_NAME"] = BOT_NAME
    if db_path is not None and db_path.strip():
        RAW_DB_PATH = db_path.strip()
        os.environ["DB_PATH"] = RAW_DB_PATH
        new_resolved = resolve_db_path(RAW_DB_PATH)
        if new_resolved != DB_PATH:
            DB_PATH = new_resolved
            init_db()

    BOT_RUNTIME_STATUS["token_valid"] = validate_bot_token(BOT_TOKEN)

    db_rel = Path(DB_PATH).name if Path(DB_PATH).parent == _ROOT_DIR else DB_PATH
    env_content = (
        f"BOT_TOKEN={BOT_TOKEN or 'YOUR_BOT_TOKEN_HERE'}\n"
        f"ADMIN_IDS={','.join(str(x) for x in ADMIN_IDS) if ADMIN_IDS else '123456789'}\n"
        f"BOT_NAME={BOT_NAME}\n"
        f"DB_PATH={db_rel}\n"
    )
    for fname in (".env", ".evn"):
        try:
            (_ROOT_DIR / fname).write_text(env_content, encoding="utf-8")
        except OSError as e:
            logger.warning("Could not write %s: %s", fname, e)

    return get_config_summary()


def get_config_summary() -> dict[str, Any]:
    masked_token = "Not Set"
    if BOT_TOKEN:
        if validate_bot_token(BOT_TOKEN):
            parts = BOT_TOKEN.split(":", 1)
            masked_token = f"{parts[0]}:{parts[1][:4]}…{parts[1][-4:]}"
        else:
            masked_token = f"{BOT_TOKEN[:14]}… (Placeholder)"
    return {
        "bot_token_masked": masked_token,
        "token_valid": validate_bot_token(BOT_TOKEN),
        "admin_ids": ADMIN_IDS,
        "bot_name": BOT_NAME,
        "db_path": Path(DB_PATH).name if Path(DB_PATH).parent == _ROOT_DIR else DB_PATH,
        "db_full_path": DB_PATH,
        "runtime": BOT_RUNTIME_STATUS,
    }


logger.info(
    "🚀 Config loaded | BOT_NAME: %s | Admin IDs: %s | DB_PATH: %s | Token Valid: %s",
    BOT_NAME,
    ADMIN_IDS,
    DB_PATH,
    validate_bot_token(BOT_TOKEN),
)

# =====================================================================
#  1) ✨ THEME & UI BUILDERS
# =====================================================================
TOP = "✦━━━━━━━━━━━━━━━━━━✦"

FILE_ICONS = {
    "document": "📄",
    "video": "🎬",
    "photo": "🖼️",
    "audio": "🎵",
    "voice": "🎙️",
    "animation": "🎞️",
}

BLUE, GREEN, RED = "primary", "success", "danger"

_SMALL = dict(zip("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"))


def bold(text: str) -> str:
    out = []
    for ch in str(text):
        if "A" <= ch <= "Z":
            out.append(chr(0x1D5D4 + ord(ch) - 65))
        elif "a" <= ch <= "z":
            out.append(chr(0x1D5EE + ord(ch) - 97))
        elif "0" <= ch <= "9":
            out.append(chr(0x1D7EC + ord(ch) - 48))
        else:
            out.append(ch)
    return "".join(out)


def smallcaps(text: str) -> str:
    return "".join(_SMALL.get(ch, ch) for ch in str(text).lower())


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def short(text: Any, limit: int = 30) -> str:
    text_str = str(text or "")
    return text_str if len(text_str) <= limit else text_str[: limit - 1] + "…"


def card(icon: str, title: str, *body: str, footer: str = "") -> str:
    out = [TOP, f"{icon}  {esc(bold(title.upper()))}", TOP]
    if body:
        out += ["", *body]
    if footer:
        out += ["", f"<i>✧ {esc(smallcaps(footer))} ✧</i>"]
    return "\n".join(out)


def progress_bar(done: int, total: int, slots: int = 10) -> str:
    if total <= 0:
        return "▰" * slots
    done = max(0, min(done, total))
    filled = round(done / total * slots)
    if 0 < done < total:
        filled = max(1, min(filled, slots - 1))
    return "▰" * filled + "▱" * (slots - filled)


def btn(
    text: str,
    data: str | None = None,
    url: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    _ = style
    if url:
        return InlineKeyboardButton(text=text, url=url)
    return InlineKeyboardButton(text=text, callback_data=data or "noop")


def kb(
    *rows: list[InlineKeyboardButton] | tuple[InlineKeyboardButton, ...]
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([list(r) for r in rows if r])


def cancel_kb() -> InlineKeyboardMarkup:
    return kb([btn("❌ Cancel", "cancel", style=RED)])


def panel_kb() -> InlineKeyboardMarkup:
    return kb(
        [
            btn("➕ Add Channel", "adm:addch", style=GREEN),
            btn("📢 Channels", "adm:channels", style=BLUE),
        ],
        [
            btn("📤 Upload File", "adm:upload", style=GREEN),
            btn("📂 My Files", "adm:files", style=BLUE),
        ],
        [
            btn("📣 Broadcast", "adm:bcast", style=RED),
            btn("📊 Stats", "adm:stats", style=BLUE),
        ],
    )


def home_kb() -> InlineKeyboardMarkup:
    return kb([btn("🛠 Admin Panel", "adm:home", style=BLUE)])


CANCEL_TEXT = "❌ Cancel"


def select_chat_keyboard() -> ReplyKeyboardMarkup | None:
    try:
        rights = ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=True,
        )
        channel_req = KeyboardButtonRequestChat(
            request_id=1,
            chat_is_channel=True,
            user_administrator_rights=rights,
            bot_administrator_rights=rights,
        )
        group_req = KeyboardButtonRequestChat(
            request_id=2,
            chat_is_channel=False,
            user_administrator_rights=rights,
            bot_administrator_rights=rights,
        )
        return ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton("📢 Select Channel", request_chat=channel_req),
                    KeyboardButton("👥 Select Group", request_chat=group_req),
                ],
                [KeyboardButton(CANCEL_TEXT)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="@username ya -100... ID bhi bhej sakte hain",
        )
    except Exception as e:
        logger.warning("Select-chat keyboard unavailable: %s", e)
        return None


# =====================================================================
#  2) 🗄️ DATABASE (bot_data.db with WAL mode & auto-heal)
# =====================================================================
conn: sqlite3.Connection | None = None
db_lock = threading.RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_db(path: str | None = None) -> sqlite3.Connection:
    target = path or DB_PATH
    c = sqlite3.connect(target, timeout=10.0, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=NORMAL;")
    c.execute("PRAGMA busy_timeout=5000;")
    return c


def init_db(custom_path: str | None = None) -> None:
    """Initializes bot_data.db. If an existing file is corrupt, backs it up and recreates it."""
    global conn, DB_PATH
    if custom_path:
        DB_PATH = resolve_db_path(custom_path)

    with db_lock:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            conn = None

        if os.path.exists(DB_PATH):
            try:
                test = _connect_db(DB_PATH)
                test.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
                test.close()
                conn = _connect_db(DB_PATH)
            except sqlite3.DatabaseError as e:
                logger.error("⚠️ DB corrupt detected (%s) — recreating fresh DB", e)
                backup = f"{DB_PATH}.corrupt.{int(datetime.now().timestamp())}"
                try:
                    os.rename(DB_PATH, backup)
                    logger.info("Old corrupt DB backed up to: %s", backup)
                except OSError:
                    try:
                        os.remove(DB_PATH)
                    except OSError:
                        pass
                conn = _connect_db(DB_PATH)
        else:
            conn = _connect_db(DB_PATH)

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                title TEXT,
                username TEXT,
                invite_link TEXT NOT NULL,
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_name TEXT,
                caption TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL,
                downloads INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                started_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pending (
                user_id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        try:
            conn.execute(
                "ALTER TABLE files ADD COLUMN downloads INTEGER NOT NULL DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()


def ensure_db() -> sqlite3.Connection:
    global conn
    if conn is None:
        init_db()
    assert conn is not None
    return conn


def save_user(user_or_id: Any, first_name: str = "", username: str = "") -> None:
    if hasattr(user_or_id, "id"):
        uid = int(user_or_id.id)
        fname = getattr(user_or_id, "first_name", "") or first_name
        uname = getattr(user_or_id, "username", "") or username
    else:
        uid = int(user_or_id)
        fname = first_name
        uname = username

    with db_lock:
        db = ensure_db()
        db.execute(
            """
            INSERT INTO users (user_id, first_name, username, started_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username
            """,
            (uid, fname or "", uname or "", now_iso()),
        )
        db.commit()


def get_user_ids() -> list[int]:
    with db_lock:
        db = ensure_db()
        return [
            int(r[0])
            for r in db.execute(
                "SELECT user_id FROM users ORDER BY started_at DESC"
            ).fetchall()
        ]


def get_users(limit: int = 50) -> list[sqlite3.Row]:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM users ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()


def save_channel(chat_id: int, title: str, username: str, invite_link: str) -> int:
    with db_lock:
        db = ensure_db()
        db.execute(
            """
            INSERT INTO channels (chat_id, title, username, invite_link, added_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username,
                invite_link = excluded.invite_link
            """,
            (
                int(chat_id),
                title or "",
                (username or "").lstrip("@"),
                invite_link,
                now_iso(),
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT id FROM channels WHERE chat_id = ?", (int(chat_id),)
        ).fetchone()
        return int(row["id"]) if row else 0


def get_channels() -> list[sqlite3.Row]:
    with db_lock:
        db = ensure_db()
        return db.execute("SELECT * FROM channels ORDER BY id ASC").fetchall()


def get_channel_by_id(channel_db_id: int) -> sqlite3.Row | None:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM channels WHERE id = ?", (int(channel_db_id),)
        ).fetchone()


def delete_channel(channel_db_id: int) -> bool:
    with db_lock:
        db = ensure_db()
        cur = db.execute("DELETE FROM channels WHERE id = ?", (int(channel_db_id),))
        db.commit()
        return cur.rowcount > 0


def save_file(
    tg_file_id: str,
    file_type: str,
    file_name: str,
    caption: str,
    created_by: int,
) -> int:
    with db_lock:
        db = ensure_db()
        cur = db.execute(
            """
            INSERT INTO files (tg_file_id, file_type, file_name, caption, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                tg_file_id,
                file_type if file_type in FILE_ICONS else "document",
                file_name or "",
                caption or "",
                int(created_by or (ADMIN_IDS[0] if ADMIN_IDS else 0)),
                now_iso(),
            ),
        )
        db.commit()
        return int(cur.lastrowid)


def get_file(file_db_id: int) -> sqlite3.Row | None:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM files WHERE id = ?", (int(file_db_id),)
        ).fetchone()


def get_files(limit: int = 25) -> list[sqlite3.Row]:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM files ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()


def delete_file(file_db_id: int) -> bool:
    with db_lock:
        db = ensure_db()
        cur = db.execute("DELETE FROM files WHERE id = ?", (int(file_db_id),))
        db.execute("DELETE FROM pending WHERE file_id = ?", (int(file_db_id),))
        db.commit()
        return cur.rowcount > 0


def add_download(file_db_id: int) -> None:
    with db_lock:
        db = ensure_db()
        db.execute(
            "UPDATE files SET downloads = downloads + 1 WHERE id = ?", (int(file_db_id),)
        )
        db.commit()


def save_pending(user_id: int, file_db_id: int) -> None:
    with db_lock:
        db = ensure_db()
        db.execute(
            """
            INSERT INTO pending (user_id, file_id, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                file_id = excluded.file_id,
                created_at = excluded.created_at
            """,
            (int(user_id), int(file_db_id), now_iso()),
        )
        db.commit()


def get_pending(user_id: int) -> sqlite3.Row | None:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM pending WHERE user_id = ?", (int(user_id),)
        ).fetchone()


def delete_pending(user_id: int) -> None:
    with db_lock:
        db = ensure_db()
        db.execute("DELETE FROM pending WHERE user_id = ?", (int(user_id),))
        db.commit()


def get_stats() -> dict[str, int]:
    with db_lock:
        db = ensure_db()
        return {
            "channels": int(db.execute("SELECT COUNT(*) FROM channels").fetchone()[0]),
            "files": int(db.execute("SELECT COUNT(*) FROM files").fetchone()[0]),
            "users": int(db.execute("SELECT COUNT(*) FROM users").fetchone()[0]),
            "downloads": int(
                db.execute("SELECT COALESCE(SUM(downloads), 0) FROM files").fetchone()[0]
            ),
            "pending": int(db.execute("SELECT COUNT(*) FROM pending").fetchone()[0]),
        }


# =====================================================================
#  3) 🧰 HELPERS
# =====================================================================
def is_admin(user_or_id: Any) -> bool:
    uid = getattr(user_or_id, "id", user_or_id)
    try:
        return int(uid) in ADMIN_IDS
    except (TypeError, ValueError):
        return False


async def guard_admin(update: Update) -> bool:
    if is_admin(update.effective_user):
        return True
    if update.callback_query:
        await update.callback_query.answer("⛔ Sirf admin ke liye!", show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text(
            card("⛔", "Access Denied", "◈ Ye option sirf <b>admin</b> ke liye hai.")
        )
    return False


async def reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    markup: Any = None,
):
    return await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=markup,
        disable_web_page_preview=True,
    )


async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    uname = context.application.bot_data.get("bot_username")
    if not uname:
        me = await context.bot.get_me()
        uname = me.username or "PremiumFileVaultBot"
        context.application.bot_data["bot_username"] = uname
        BOT_RUNTIME_STATUS["bot_username"] = uname
    return uname


def file_link(username: str, file_db_id: int) -> str:
    clean_uname = (username or "PremiumFileVaultBot").lstrip("@")
    return f"https://t.me/{clean_uname}?start=file_{int(file_db_id)}"


def parse_chat_identifier(text: str | None) -> int | str | None:
    t = (text or "").strip()
    if not t or " " in t:
        return None
    if t.lstrip("-").isdigit():
        return int(t)
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if t.startswith(prefix):
            tail = t[len(prefix) :].split("/")[0].split("?")[0]
            if not tail or tail.startswith("+") or tail == "joinchat":
                return None
            t = tail
            break
    t = t.lstrip("@")
    if not t or not re.match(r"^[A-Za-z0-9_]{4,64}$", t):
        return None
    return "@" + t


# =====================================================================
#  4) 🔒 FORCE-JOIN + FILE DELIVERY
# =====================================================================
JOINED_STATUSES = ("creator", "administrator", "member")


async def channel_status(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> list[tuple[sqlite3.Row, bool]]:
    result: list[tuple[sqlite3.Row, bool]] = []
    for ch in get_channels():
        joined = True
        try:
            member = await context.bot.get_chat_member(
                chat_id=ch["chat_id"], user_id=user_id
            )
            status = str(member.status)
            joined = status in JOINED_STATUSES or (
                status == "restricted" and bool(getattr(member, "is_member", False))
            )
        except TelegramError as e:
            logger.warning("Membership check failed chat=%s: %s", ch["chat_id"], e)
        result.append((ch, joined))
    return result


def pending_channels(status: list[tuple[sqlite3.Row, bool]]) -> list[sqlite3.Row]:
    return [ch for ch, ok in status if not ok]


def force_sub_text(status: list[tuple[sqlite3.Row, bool]]) -> str:
    total = len(status)
    done = sum(1 for _, ok in status if ok)
    lines = []
    for i, (ch, ok) in enumerate(status, 1):
        mark = "✅" if ok else "❌"
        lines.append(f"{mark} <b>{i}. {esc(ch['title'])}</b>")
    return card(
        "🔒",
        "Access Locked",
        "🎁 Aapki file <b>ready</b> hai!",
        "Bas neeche ke channels join karein 👇",
        "",
        "\n".join(lines),
        "",
        f"📊 <b>Progress</b>   {progress_bar(done, total)}   <b>{done}/{total}</b>",
        "",
        "<blockquote>👆 Join dabayein ➜ <b>Request to Join</b> bhejein ➜ "
        "bot khud approve karega ➜ phir <b>Verify</b> dabayein.</blockquote>",
        footer=BOT_NAME,
    )


def force_sub_keyboard(
    status: list[tuple[sqlite3.Row, bool]], file_db_id: int
) -> InlineKeyboardMarkup:
    rows = [
        [btn(f"📢 Join • {short(ch['title'], 26)}", url=ch["invite_link"], style=BLUE)]
        for ch in pending_channels(status)
    ]
    rows.append([btn("✅ Verify & Get File", f"verify:{file_db_id}", style=GREEN)])
    return kb(*rows)


def build_caption(row: sqlite3.Row | dict[str, Any]) -> str:
    cap = (row["caption"] or "").strip()[:850]
    if cap:
        return f"✦ <b>{esc(cap)}</b>\n\n<i>✧ {esc(smallcaps('via ' + BOT_NAME))} ✧</i>"
    return f"<i>✧ {esc(smallcaps('via ' + BOT_NAME))} ✧</i>"


SEND_METHODS = {
    "document": ("send_document", "document"),
    "video": ("send_video", "video"),
    "photo": ("send_photo", "photo"),
    "audio": ("send_audio", "audio"),
    "voice": ("send_voice", "voice"),
    "animation": ("send_animation", "animation"),
}


async def send_file(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, file_db_id: int
) -> bool:
    row = get_file(file_db_id)
    if not row:
        await context.bot.send_message(
            chat_id,
            card(
                "❌",
                "File Not Found",
                "◈ File delete ho chuki hai ya link purana hai.",
            ),
        )
        return False

    method, arg = SEND_METHODS.get(row["file_type"], SEND_METHODS["document"])
    try:
        await getattr(context.bot, method)(
            chat_id=chat_id,
            caption=build_caption(row),
            **{arg: row["tg_file_id"]},
        )
        add_download(file_db_id)
        delete_pending(chat_id)
        return True
    except TelegramError as e:
        logger.exception("File send failed: %s", e)
        await context.bot.send_message(
            chat_id,
            card(
                "❌",
                "Send Failed",
                "◈ File bhejne me error aayi.",
                f"<code>{esc(str(e))}</code>",
            ),
        )
        return False


# =====================================================================
#  5) 🎯 COMMAND HANDLERS
# =====================================================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user:
        save_user(update.effective_user)
    args = context.args or []

    if args and args[0].startswith("file_"):
        try:
            file_db_id = int(args[0][5:])
        except ValueError:
            await reply(update, context, card("❌", "Bad Link", "◈ Invalid file link."))
            return ConversationHandler.END

        row = get_file(file_db_id)
        if not row:
            await reply(
                update,
                context,
                card("❌", "File Not Found", "◈ File delete ho chuki hai."),
            )
            return ConversationHandler.END

        save_pending(update.effective_user.id, file_db_id)
        status = await channel_status(context, update.effective_user.id)
        pending = pending_channels(status)

        if pending:
            await reply(
                update,
                context,
                force_sub_text(status),
                markup=force_sub_keyboard(status, file_db_id),
            )
        else:
            await reply(
                update,
                context,
                card("✅", "Sending File", "◈ File bheji ja rahi hai…"),
            )
            await send_file(context, update.effective_chat.id, file_db_id)
        return ConversationHandler.END

    if is_admin(update.effective_user):
        text = card(
            "🎁",
            f"Welcome to {BOT_NAME}",
            f"👤 <b>{esc(update.effective_user.first_name or 'Admin')}</b>",
            "",
            "◈ Aap <b>admin</b> hain. Neeche se option chunein 👇",
            footer=BOT_NAME,
        )
        await reply(update, context, text, markup=panel_kb())
    else:
        text = card(
            "🎁",
            f"Welcome to {BOT_NAME}",
            f"👤 <b>{esc(update.effective_user.first_name or 'User')}</b>",
            "",
            "◈ File receive karne ke liye <b>share link</b> open karein.",
            footer=BOT_NAME,
        )
        await reply(update, context, text)
    return ConversationHandler.END


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user:
        save_user(update.effective_user)
    text = card(
        "ℹ️",
        "Help & Commands",
        "<b>📢 Add Channel</b> — /addchannel",
        "<b>📤 Upload File</b> — /upload",
        "<b>📣 Broadcast</b> — /broadcast",
        "<b>🛠 Admin Panel</b> — /admin",
        "<b>❌ Cancel Action</b> — /cancel",
        "",
        "<i>Shareable File Link Format:</i>",
        "<code>https://t.me/&lt;bot&gt;?start=file_&lt;id&gt;</code>",
        footer=BOT_NAME,
    )
    markup = panel_kb() if is_admin(update.effective_user) else None
    await reply(update, context, text, markup=markup)
    return ConversationHandler.END


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    await reply(
        update,
        context,
        card(
            "🛠",
            "Admin Panel",
            "◈ Welcome back! Neeche se action chunein:",
            footer=BOT_NAME,
        ),
        markup=panel_kb(),
    )
    return ConversationHandler.END


# =====================================================================
#  6) 🛠 ADMIN CALLBACK ROUTER
# =====================================================================
async def adm_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    if not q:
        return ConversationHandler.END
    if not await guard_admin(update):
        return ConversationHandler.END
    await q.answer()

    data = q.data or ""
    if data == "adm:home":
        try:
            await q.edit_message_text(
                card("🛠", "Admin Panel", "◈ Welcome back!", footer=BOT_NAME),
                reply_markup=panel_kb(),
            )
        except BadRequest:
            pass

    elif data == "adm:stats":
        s = get_stats()
        text = card(
            "📊",
            "Bot Statistics",
            f"📢 <b>Channels:</b>  {s['channels']}",
            f"📂 <b>Files:</b>  {s['files']}",
            f"👥 <b>Users:</b>  {s['users']}",
            f"⬇️ <b>Downloads:</b>  {s['downloads']}",
            f"⏳ <b>Pending Verifications:</b>  {s['pending']}",
            footer=BOT_NAME,
        )
        try:
            await q.edit_message_text(
                text,
                reply_markup=kb(
                    [
                        btn("🔄 Refresh", "adm:stats", style=GREEN),
                        btn("🛠 Back", "adm:home", style=BLUE),
                    ]
                ),
            )
        except BadRequest:
            pass

    elif data == "adm:channels":
        await list_channels_cb(update, context)

    elif data == "adm:files":
        await my_files_cb(update, context)

    return ConversationHandler.END


async def list_channels_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    channels = get_channels()

    if not channels:
        try:
            await q.edit_message_text(
                card("📢", "Channels", "◈ Abhi koi force-join channel add nahi hua."),
                reply_markup=kb(
                    [btn("➕ Add Channel", "adm:addch", style=GREEN)],
                    [btn("🛠 Back", "adm:home", style=BLUE)],
                ),
            )
        except BadRequest:
            pass
        return

    lines = []
    for ch in channels:
        uname = f"@{ch['username']}" if ch["username"] else "🔒 Private"
        lines.append(
            f"• <b>#{ch['id']} {esc(ch['title'])}</b> ({uname})\n"
            f"  🔗 <a href='{esc(ch['invite_link'])}'>Invite Link</a>"
        )

    text = card(
        "📢",
        "Force-Join Channels",
        f"<b>Total:</b> {len(channels)}",
        "",
        "\n".join(lines),
        footer=BOT_NAME,
    )
    del_btns = [
        btn(f"🗑 #{ch['id']}", f"delch:{ch['id']}", style=RED) for ch in channels
    ]
    rows = [del_btns[i : i + 4] for i in range(0, len(del_btns), 4)]
    rows.append(
        [
            btn("➕ Add Channel", "adm:addch", style=GREEN),
            btn("🛠 Back", "adm:home", style=BLUE),
        ]
    )
    try:
        await q.edit_message_text(
            text,
            reply_markup=kb(*rows),
            disable_web_page_preview=True,
        )
    except BadRequest:
        pass


async def my_files_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    files = get_files(limit=15)

    if not files:
        try:
            await q.edit_message_text(
                card("📂", "My Files", "◈ Abhi tak koi file upload nahi hui."),
                reply_markup=kb(
                    [btn("📤 Upload File", "adm:upload", style=GREEN)],
                    [btn("🛠 Back", "adm:home", style=BLUE)],
                ),
            )
        except BadRequest:
            pass
        return

    username = await get_bot_username(context)
    lines = []
    for f in files:
        icon = FILE_ICONS.get(f["file_type"], "📄")
        name = short(f["file_name"] or f"file #{f['id']}", 28)
        link = file_link(username, f["id"])
        lines.append(
            f"{icon} <b>#{f['id']}</b>  {esc(name)}  (⬇️ {f['downloads']})\n"
            f"   <code>{esc(link)}</code>"
        )

    text = card(
        "📂",
        "My Files",
        f"<b>Recent {len(files)} Files</b>",
        "",
        "\n".join(lines),
        footer=BOT_NAME,
    )
    view_btns = [
        btn(f"🔗 #{f['id']}", f"viewfile:{f['id']}", style=BLUE) for f in files
    ]
    del_btns = [
        btn(f"🗑 #{f['id']}", f"delfile:{f['id']}", style=RED) for f in files
    ]
    rows = []
    for i in range(0, len(view_btns), 4):
        rows.append(view_btns[i : i + 4])
    for i in range(0, len(del_btns), 4):
        rows.append(del_btns[i : i + 4])
    rows.append(
        [
            btn("📤 Upload File", "adm:upload", style=GREEN),
            btn("🛠 Back", "adm:home", style=BLUE),
        ]
    )
    try:
        await q.edit_message_text(
            text,
            reply_markup=kb(*rows),
            disable_web_page_preview=True,
        )
    except BadRequest:
        pass


async def view_file_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not await guard_admin(update):
        return
    try:
        file_db_id = int(q.data.split(":")[1])
    except (IndexError, ValueError):
        await q.answer("Invalid file ID", show_alert=True)
        return

    row = get_file(file_db_id)
    if not row:
        await q.answer("❌ File not found!", show_alert=True)
        await my_files_cb(update, context)
        return

    await q.answer()
    username = await get_bot_username(context)
    link = file_link(username, file_db_id)
    icon = FILE_ICONS.get(row["file_type"], "📄")
    text = card(
        icon,
        f"File #{row['id']} Details",
        f"📝 <b>Name:</b>  {esc(row['file_name'] or '—')}",
        f"📦 <b>Type:</b>  {esc(row['file_type'])}",
        f"⬇️ <b>Downloads:</b>  {row['downloads']}",
        f"💬 <b>Caption:</b>  {esc(short(row['caption'] or '—', 80))}",
        "",
        "🔗 <b>Shareable Link:</b>",
        f"<code>{esc(link)}</code>",
        footer=BOT_NAME,
    )
    try:
        await q.edit_message_text(
            text,
            disable_web_page_preview=True,
            reply_markup=kb(
                [
                    btn("📥 Send File Here", f"sendfile:{row['id']}", style=GREEN),
                    btn("🗑 Delete", f"delfile:{row['id']}", style=RED),
                ],
                [btn("📂 Back to Files", "adm:files", style=BLUE)],
            ),
        )
    except BadRequest:
        pass


async def send_file_admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not await guard_admin(update):
        return
    try:
        file_db_id = int(q.data.split(":")[1])
    except (IndexError, ValueError):
        return
    await q.answer("📤 Sending file…")
    await send_file(context, q.message.chat_id, file_db_id)


async def delete_channel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not await guard_admin(update):
        return
    ch_db_id = int(q.data.split(":")[1])
    delete_channel(ch_db_id)
    await q.answer("🗑 Channel removed!", show_alert=True)
    await list_channels_cb(update, context)


async def delete_file_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not await guard_admin(update):
        return
    file_db_id = int(q.data.split(":")[1])
    delete_file(file_db_id)
    await q.answer("🗑 File deleted!", show_alert=True)
    await my_files_cb(update, context)


# =====================================================================
#  7) 🔐 VERIFY (Force-Join Verification)
# =====================================================================
async def verify_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not (q.data or "").startswith("verify:"):
        return
    await q.answer("🔍 Checking membership…")

    file_db_id = int(q.data.split(":")[1])
    save_user(q.from_user)
    save_pending(q.from_user.id, file_db_id)

    status = await channel_status(context, q.from_user.id)
    pending = pending_channels(status)

    if pending:
        try:
            await q.message.edit_text(
                force_sub_text(status),
                reply_markup=force_sub_keyboard(status, file_db_id),
            )
        except BadRequest:
            pass
        return

    try:
        await q.message.edit_text(
            card(
                "✅",
                "Verified!",
                "◈ Sab channels joined.",
                "📤 File bheji ja rahi hai…",
                footer=BOT_NAME,
            )
        )
    except BadRequest:
        pass

    await send_file(context, q.message.chat_id, file_db_id)


# =====================================================================
#  8) ➕ ADD CHANNEL (Conversation)
# =====================================================================
ADDCH_INPUT = 1


async def addchannel_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    markup = select_chat_keyboard()
    text = card(
        "➕",
        "Add Channel",
        "<b>4 aasaan tareeke:</b>",
        "",
        "1️⃣ Neeche <b>Select Channel</b> dabayein",
        "2️⃣ <code>@username</code> ya <code>-100…</code> ID bhejein",
        "3️⃣ Channel ka koi message <b>forward</b> karein",
        "4️⃣ Bot ko channel me admin banayein (auto-detect)",
        "",
        "<blockquote>Bot ko channel me <b>admin</b> banana zaroori hai "
        "(invite permission ke saath).</blockquote>",
        footer=BOT_NAME,
    )
    await reply(update, context, text, markup=markup or cancel_kb())
    return ADDCH_INPUT


async def _resolve_and_save_channel(
    context: ContextTypes.DEFAULT_TYPE,
    chat_obj: Any,
    fallback_id: int | None = None,
) -> tuple[Any, str | None, str | None]:
    chat_id = getattr(chat_obj, "id", None) if chat_obj else fallback_id
    if not chat_id:
        return None, None, "❌ Chat identify nahi hua."

    try:
        full = await context.bot.get_chat(chat_id)
    except TelegramError as e:
        return None, None, f"❌ Chat access nahi mila: <code>{esc(str(e))}</code>"

    invite = getattr(full, "invite_link", None)
    if not invite:
        try:
            invite = await context.bot.export_chat_invite_link(chat_id)
        except TelegramError:
            invite = None
    if not invite and getattr(full, "username", None):
        invite = f"https://t.me/{full.username}"
    if not invite:
        return (
            None,
            None,
            "❌ Invite link nahi mila. Bot ko channel me <b>admin</b> banao "
            "(Invite Users permission ke saath).",
        )

    save_channel(chat_id, full.title or "Channel", full.username or "", invite)
    return full, invite, None


async def addchannel_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return ADDCH_INPUT

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(
            card("❌", "Cancelled", "◈ Add channel cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    chat_obj = None

    if msg.chat_shared:
        try:
            chat_obj = await context.bot.get_chat(msg.chat_shared.chat_id)
        except TelegramError as e:
            await msg.reply_text(f"❌ Chat info nahi mila: <code>{esc(str(e))}</code>")
            return ADDCH_INPUT

    elif msg.forward_from_chat:
        chat_obj = msg.forward_from_chat

    elif msg.text:
        ident = parse_chat_identifier(msg.text)
        if not ident:
            await msg.reply_text(
                "❌ Invalid format. <code>@username</code> ya "
                "<code>-100…</code> ID bhejo, ya Cancel dabao."
            )
            return ADDCH_INPUT
        try:
            chat_obj = await context.bot.get_chat(ident)
        except TelegramError as e:
            await msg.reply_text(
                f"❌ Channel resolve nahi hua: <code>{esc(str(e))}</code>\n"
                "Bot ko channel me admin banao aur try karo."
            )
            return ADDCH_INPUT

    if not chat_obj:
        await msg.reply_text(
            "❌ Kuch samajh nahi aaya. Select Channel, @username, "
            "-100… ID, ya forward try karo."
        )
        return ADDCH_INPUT

    full, invite, error = await _resolve_and_save_channel(context, chat_obj)
    if error:
        await msg.reply_text(error)
        return ADDCH_INPUT

    await msg.reply_text(
        card(
            "✅",
            "Channel Added",
            f"📢 <b>{esc(full.title)}</b>",
            f"🆔 <code>{full.id}</code>",
            f"🔗 <a href='{esc(invite or '')}'>Invite Link</a>",
            footer=BOT_NAME,
        ),
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True,
    )
    await msg.reply_text(
        card("🛠", "Admin Panel", "◈ Ab kya karna hai?", footer=BOT_NAME),
        reply_markup=panel_kb(),
    )
    return ConversationHandler.END


# =====================================================================
#  9) 📤 UPLOAD FILE (Conversation)
# =====================================================================
UPLOAD_INPUT = 1


async def upload_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    await reply(
        update,
        context,
        card(
            "📤",
            "Upload File",
            "◈ Koi bhi file bhejo:",
            "📄 Document · 🎬 Video · 🖼️ Photo",
            "🎵 Audio · 🎙️ Voice · 🎞️ Animation",
            "",
            "<i>Optional:</i> file ke saath caption bhejo, wahi caption users ko dikhega.",
            footer=BOT_NAME,
        ),
        markup=cancel_kb(),
    )
    return UPLOAD_INPUT


async def upload_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return UPLOAD_INPUT

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(
            card("❌", "Cancelled", "◈ File upload cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    ft = fid = fname = None

    if msg.document:
        ft, fid = "document", msg.document.file_id
        fname = msg.document.file_name or ""
    elif msg.video:
        ft, fid = "video", msg.video.file_id
        fname = msg.video.file_name or ""
    elif msg.photo:
        ft, fid = "photo", msg.photo[-1].file_id
        fname = f"photo_{msg.photo[-1].file_unique_id}.jpg"
    elif msg.audio:
        ft, fid = "audio", msg.audio.file_id
        fname = msg.audio.file_name or ""
    elif msg.voice:
        ft, fid = "voice", msg.voice.file_id
        fname = f"voice_{msg.voice.file_unique_id}.ogg"
    elif msg.animation:
        ft, fid = "animation", msg.animation.file_id
        fname = msg.animation.file_name or ""

    if not ft or not fid:
        await msg.reply_text(
            "❌ Sirf file/video/photo/audio/voice/animation bhejo, ya Cancel dabao.",
            reply_markup=cancel_kb(),
        )
        return UPLOAD_INPUT

    caption = msg.caption or ""
    file_db_id = save_file(fid, ft, fname, caption, update.effective_user.id)
    username = await get_bot_username(context)
    link = file_link(username, file_db_id)

    await msg.reply_text(
        card(
            "✅",
            "File Uploaded",
            f"🆔 <b>ID:</b>  <code>{file_db_id}</code>",
            f"{FILE_ICONS.get(ft, '📄')} <b>Type:</b>  {ft}",
            f"📝 <b>Name:</b>  {esc(fname) if fname else '—'}",
            "",
            "🔗 <b>Share Link:</b>",
            f"<code>{esc(link)}</code>",
            footer=BOT_NAME,
        ),
        disable_web_page_preview=True,
        reply_markup=kb(
            [
                btn("📂 My Files", "adm:files", style=BLUE),
                btn("📤 Upload Another", "adm:upload", style=GREEN),
            ],
            [btn("🛠 Panel", "adm:home", style=BLUE)],
        ),
    )
    return ConversationHandler.END


# =====================================================================
#  10) 📣 BROADCAST (Conversation)
# =====================================================================
BCAST_INPUT = 1


async def broadcast_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    total = len(get_user_ids())
    await reply(
        update,
        context,
        card(
            "📣",
            "Broadcast",
            f"◈ <b>{total}</b> users ko message bhejna hai.",
            "",
            "Koi bhi message bhejo (text/photo/video/file).",
            "<i>Sab users ko waisa hi copy hoga.</i>",
            footer=BOT_NAME,
        ),
        markup=cancel_kb(),
    )
    return BCAST_INPUT


async def broadcast_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return BCAST_INPUT

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(
            card("❌", "Cancelled", "◈ Broadcast cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    user_ids = get_user_ids()
    if not user_ids:
        await msg.reply_text(
            card("📣", "Broadcast", "◈ Koi user nahi hai abhi."),
            reply_markup=panel_kb(),
        )
        return ConversationHandler.END

    status_msg = await msg.reply_text(
        card("⏳", "Broadcasting…", f"◈ 0 / {len(user_ids)}")
    )

    sent = failed = 0
    for i, uid in enumerate(user_ids, 1):
        try:
            await msg.copy(chat_id=uid)
            sent += 1
        except RetryAfter as e:
            await asyncio.sleep(float(e.retry_after) + 1.0)
            try:
                await msg.copy(chat_id=uid)
                sent += 1
            except TelegramError:
                failed += 1
        except TelegramError:
            failed += 1

        if i % 25 == 0:
            try:
                await status_msg.edit_text(
                    card(
                        "⏳",
                        "Broadcasting…",
                        f"◈ {i} / {len(user_ids)}",
                        f"✅ Sent: {sent}  ❌ Failed: {failed}",
                    )
                )
            except BadRequest:
                pass
            await asyncio.sleep(0.5)

    try:
        await status_msg.edit_text(
            card(
                "✅",
                "Broadcast Complete",
                f"✅ <b>Sent:</b> {sent}",
                f"❌ <b>Failed:</b> {failed}",
                f"👥 <b>Total:</b> {len(user_ids)}",
                footer=BOT_NAME,
            ),
            reply_markup=kb([btn("🛠 Panel", "adm:home", style=BLUE)]),
        )
    except BadRequest:
        pass
    return ConversationHandler.END


# =====================================================================
#  11) ❌ CANCEL HANDLERS
# =====================================================================
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text(
            card("❌", "Cancelled", "◈ Operation cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


async def cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    if q:
        await q.answer("Cancelled")
        try:
            await q.message.edit_text(
                card(
                    "❌",
                    "Cancelled",
                    "◈ Operation cancel ho gaya.",
                    footer=BOT_NAME,
                ),
                reply_markup=home_kb() if is_admin(q.from_user) else None,
            )
        except BadRequest:
            pass
    return ConversationHandler.END


# =====================================================================
#  12) 🤝 CHANNEL EVENT HANDLERS (Auto-Approve + Auto-Deliver Pending File)
# =====================================================================
async def chat_join_request_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    req = update.chat_join_request
    if not req:
        return
    try:
        await context.bot.approve_chat_join_request(
            chat_id=req.chat.id, user_id=req.from_user.id
        )
        save_user(req.from_user)
        logger.info("Join approved: user=%s chat=%s", req.from_user.id, req.chat.id)

        pending_row = get_pending(req.from_user.id)
        if pending_row:
            file_db_id = int(pending_row["file_id"])
            status = await channel_status(context, req.from_user.id)
            remaining = pending_channels(status)
            if not remaining:
                try:
                    await context.bot.send_message(
                        req.from_user.id,
                        card(
                            "✅",
                            "All Channels Joined!",
                            "◈ Aapki join request approve ho gayi.",
                            "📤 Aapki file bheji ja rahi hai…",
                            footer=BOT_NAME,
                        ),
                    )
                except TelegramError:
                    pass
                await send_file(context, req.from_user.id, file_db_id)
                return
            else:
                try:
                    await context.bot.send_message(
                        req.from_user.id,
                        force_sub_text(status),
                        reply_markup=force_sub_keyboard(status, file_db_id),
                    )
                except TelegramError:
                    pass
                return

        try:
            await context.bot.send_message(
                req.from_user.id,
                card(
                    "✅",
                    "Request Approved",
                    "◈ Aap channel me add ho gaye.",
                    "Ab bot me wapas aakar <b>Verify</b> dabayein.",
                    footer=BOT_NAME,
                ),
            )
        except TelegramError:
            pass
    except TelegramError as e:
        logger.warning("Join approve failed: %s", e)


async def my_chat_member_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    cm = update.my_chat_member
    if not cm:
        return
    chat = cm.chat
    if chat.type not in ("channel", "supergroup", "group"):
        return

    new = cm.new_chat_member
    old = cm.old_chat_member
    was_admin = str(old.status) in ("administrator", "creator")
    is_admin_now = str(new.status) in ("administrator", "creator")

    if is_admin_now and not was_admin:
        invite = getattr(chat, "invite_link", None)
        if not invite:
            try:
                invite = await context.bot.export_chat_invite_link(chat.id)
            except TelegramError:
                invite = None
        if not invite and getattr(chat, "username", None):
            invite = f"https://t.me/{chat.username}"
        if invite:
            save_channel(chat.id, chat.title or "Channel", chat.username or "", invite)
            logger.info("Auto-added channel: %s", chat.id)
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        card(
                            "✅",
                            "Channel Auto-Added",
                            f"📢 <b>{esc(chat.title)}</b>",
                            f"🆔 <code>{chat.id}</code>",
                            footer=BOT_NAME,
                        ),
                    )
                except TelegramError:
                    pass

    if not is_admin_now and was_admin:
        with db_lock:
            db = ensure_db()
            row = db.execute(
                "SELECT id FROM channels WHERE chat_id = ?", (chat.id,)
            ).fetchone()
        if row:
            delete_channel(int(row["id"]))
            logger.info("Removed channel (bot demoted): %s", chat.id)


async def forwarded_channel_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    msg = update.message
    if not msg or not msg.forward_from_chat:
        return
    if not is_admin(update.effective_user):
        return

    chat = msg.forward_from_chat
    if chat.type != "channel":
        return

    full, invite, error = await _resolve_and_save_channel(context, chat)
    if error:
        await msg.reply_text(error)
        return

    await msg.reply_text(
        card(
            "✅",
            "Channel Added",
            f"📢 <b>{esc(full.title)}</b>",
            f"🆔 <code>{full.id}</code>",
            f"🔗 <a href='{esc(invite or '')}'>Invite Link</a>",
            footer=BOT_NAME,
        ),
        reply_markup=panel_kb(),
        disable_web_page_preview=True,
    )


# =====================================================================
#  13) 🚨 ERROR HANDLER & DIRECT UPDATE-QUEUE POLLING ENGINE
# =====================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = getattr(context, "error", None)
    if isinstance(err, Conflict):
        count = int(BOT_RUNTIME_STATUS.get("conflict_count", 0)) + 1
        BOT_RUNTIME_STATUS["conflict_count"] = count
        BOT_RUNTIME_STATUS["last_conflict_at"] = now_iso()
        BOT_RUNTIME_STATUS["last_error"] = (
            "Conflict: Another bot instance was polling getUpdates. "
            "Auto-cooldown active."
        )
        return

    if isinstance(err, RetryAfter):
        await asyncio.sleep(float(err.retry_after) + 1.0)
        return

    if isinstance(err, (BadRequest, Forbidden, NetworkError, TimedOut)):
        return

    BOT_RUNTIME_STATUS["last_error"] = str(err)
    logger.error("Update error:", exc_info=err)


async def _custom_polling_loop(app: Application, stop_event: asyncio.Event) -> None:
    """
    Direct update_queue polling engine that bypasses telegram.ext._updater and
    networkloop.py completely. Eliminates all getUpdates Conflict tracebacks and
    ping-pong retry loops during Render rolling deployments.
    """
    offset: int | None = None
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        BOT_RUNTIME_STATUS["webhook_cleared"] = True
    except Exception:
        pass

    logger.info("✅ Bot active and listening for Telegram updates.")
    while not stop_event.is_set():
        try:
            updates = await app.bot.get_updates(
                offset=offset,
                timeout=20,
                allowed_updates=Update.ALL_TYPES,
            )
            for upd in updates:
                offset = upd.update_id + 1
                await app.update_queue.put(upd)
        except Conflict:
            count = int(BOT_RUNTIME_STATUS.get("conflict_count", 0)) + 1
            BOT_RUNTIME_STATUS["conflict_count"] = count
            BOT_RUNTIME_STATUS["last_conflict_at"] = now_iso()
            # Quietly wait 15s so any retiring Render container finishes exiting
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=15.0)
            except asyncio.TimeoutError:
                pass
            if not stop_event.is_set():
                try:
                    await app.bot.delete_webhook(drop_pending_updates=False)
                except Exception:
                    pass
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 5.0)) + 1.0)
        except (TimedOut, NetworkError):
            await asyncio.sleep(2.0)
        except TelegramError:
            await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(5.0)


# =====================================================================
#  14) 🔒 SINGLE-INSTANCE LOCK + APPLICATION BUILDER
# =====================================================================
_lock_file_handle = None


def acquire_single_instance_lock() -> bool:
    global _lock_file_handle
    if _lock_file_handle is not None:
        return True
    lock_path = Path(f"{DB_PATH}.lock")
    try:
        import fcntl

        fh = open(lock_path, "w", encoding="utf-8")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.write(f"{os.getpid()}\n")
        fh.flush()
        _lock_file_handle = fh
        BOT_RUNTIME_STATUS["single_instance_locked"] = True
        return True
    except ImportError:
        BOT_RUNTIME_STATUS["single_instance_locked"] = True
        return True
    except OSError:
        BOT_RUNTIME_STATUS["single_instance_locked"] = False
        return False


async def _configure_bot_commands(app: Application) -> None:
    commands = [
        BotCommand("start", "🚀 Start bot"),
        BotCommand("help", "ℹ️ Help"),
        BotCommand("admin", "🛠 Admin panel"),
        BotCommand("addchannel", "➕ Add channel"),
        BotCommand("upload", "📤 Upload file"),
        BotCommand("broadcast", "📣 Broadcast"),
        BotCommand("cancel", "❌ Cancel"),
    ]
    try:
        me = await app.bot.get_me()
        app.bot_data["bot_username"] = me.username or "PremiumFileVaultBot"
        BOT_RUNTIME_STATUS["bot_username"] = app.bot_data["bot_username"]
        await app.bot.set_my_commands(commands)
        for admin_id in ADMIN_IDS:
            try:
                await app.bot.set_my_commands(
                    commands, scope=BotCommandScopeChat(chat_id=admin_id)
                )
            except TelegramError:
                pass
    except TelegramError as e:
        logger.warning("Commands set notice: %s", e)


async def _post_init(app: Application) -> None:
    await _configure_bot_commands(app)


def _common_fallbacks() -> list[Any]:
    return [
        CommandHandler("cancel", cancel_cmd),
        CallbackQueryHandler(cancel_cb, pattern=r"^cancel$"),
        CommandHandler("start", start_cmd),
        CommandHandler("admin", admin_cmd),
        CommandHandler("help", help_cmd),
        CallbackQueryHandler(adm_router, pattern=r"^adm:(home|stats|channels|files)$"),
    ]


def _build_app(token: str | None = None) -> Application:
    active_token = (token or BOT_TOKEN).strip()
    defaults = Defaults(parse_mode=ParseMode.HTML)
    app = (
        Application.builder()
        .token(active_token)
        .defaults(defaults)
        .updater(None)
        .post_init(_post_init)
        .build()
    )

    addchannel_conv = ConversationHandler(
        entry_points=[
            CommandHandler("addchannel", addchannel_entry),
            CallbackQueryHandler(addchannel_entry, pattern=r"^adm:addch$"),
        ],
        states={
            ADDCH_INPUT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, addchannel_input),
            ],
        },
        fallbacks=_common_fallbacks(),
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )

    upload_conv = ConversationHandler(
        entry_points=[
            CommandHandler("upload", upload_entry),
            CallbackQueryHandler(upload_entry, pattern=r"^adm:upload$"),
        ],
        states={
            UPLOAD_INPUT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, upload_received),
            ],
        },
        fallbacks=_common_fallbacks(),
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )

    broadcast_conv = ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", broadcast_entry),
            CallbackQueryHandler(broadcast_entry, pattern=r"^adm:bcast$"),
        ],
        states={
            BCAST_INPUT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_received),
            ],
        },
        fallbacks=_common_fallbacks(),
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )

    app.add_handler(addchannel_conv)
    app.add_handler(upload_conv)
    app.add_handler(broadcast_conv)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))

    app.add_handler(CallbackQueryHandler(verify_cb, pattern=r"^verify:"))
    app.add_handler(CallbackQueryHandler(delete_channel_cb, pattern=r"^delch:"))
    app.add_handler(CallbackQueryHandler(delete_file_cb, pattern=r"^delfile:"))
    app.add_handler(CallbackQueryHandler(view_file_cb, pattern=r"^viewfile:"))
    app.add_handler(CallbackQueryHandler(send_file_admin_cb, pattern=r"^sendfile:"))
    app.add_handler(CallbackQueryHandler(cancel_cb, pattern=r"^cancel$"))
    app.add_handler(CallbackQueryHandler(adm_router, pattern=r"^adm:"))

    app.add_handler(ChatJoinRequestHandler(chat_join_request_handler))
    app.add_handler(
        ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    app.add_handler(
        MessageHandler(
            filters.FORWARDED & filters.ChatType.PRIVATE,
            forwarded_channel_handler,
        )
    )

    app.add_error_handler(error_handler)
    return app


def seed_demo_data_if_empty() -> None:
    """Seeds initial starter records into bot_data.db if empty."""
    init_db()
    stats = get_stats()
    if stats["channels"] == 0 and stats["files"] == 0 and stats["users"] == 0:
        admin_uid = ADMIN_IDS[0] if ADMIN_IDS else 123456789
        save_user(admin_uid, "Vault Admin", "vault_admin")
        save_channel(
            -1001987654321,
            "Premium File Vault Updates",
            "PremiumVaultUpdates",
            "https://t.me/PremiumVaultUpdates",
        )
        save_file(
            "BQACAgUAAxkBAAIBZ2X_demo_masterclass_pack",
            "document",
            "Premium_Vault_Starter_Bundle_v2.zip",
            "Exclusive Premium File Vault Starter Bundle — Verified Members Only",
            admin_uid,
        )


async def _run_bot_lifecycle() -> None:
    """
    Runs the Telegram Bot using Webhook mode on Render Web Services (when
    RENDER_EXTERNAL_URL / RENDER_EXTERNAL_HOSTNAME / WEBHOOK_URL is available)
    so getUpdates Conflict is 100% impossible, or via the direct _custom_polling_loop
    that bypasses telegram.ext._updater completely.
    """
    global _ACTIVE_PTB_APP, _ACTIVE_BOT_LOOP
    _ACTIVE_BOT_LOOP = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            _ACTIVE_BOT_LOOP.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass

    app = _build_app(BOT_TOKEN)
    _ACTIVE_PTB_APP = app

    await app.initialize()
    await _configure_bot_commands(app)
    await app.start()

    webhook_base = resolve_webhook_base_url()
    if webhook_base:
        webhook_url = f"{webhook_base}/telegram-webhook"
        try:
            await app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
            BOT_RUNTIME_STATUS["mode"] = "webhook_live"
            BOT_RUNTIME_STATUS["bot_running"] = True
            BOT_RUNTIME_STATUS["webhook_url"] = webhook_url
            logger.info(
                "✅ Bot started in WEBHOOK mode: %s (Zero getUpdates Conflict!)",
                webhook_url,
            )

            async def _webhook_watchdog() -> None:
                # Re-verify shortly after Render switches live traffic, then every 20s
                for delay in (5.0, 12.0):
                    await asyncio.sleep(delay)
                    if stop_event.is_set():
                        return
                    try:
                        await app.bot.set_webhook(
                            url=webhook_url,
                            allowed_updates=Update.ALL_TYPES,
                        )
                    except Exception:
                        pass
                while not stop_event.is_set():
                    await asyncio.sleep(20.0)
                    if stop_event.is_set():
                        break
                    try:
                        info = await app.bot.get_webhook_info()
                        if getattr(info, "url", "") != webhook_url:
                            await app.bot.set_webhook(
                                url=webhook_url,
                                allowed_updates=Update.ALL_TYPES,
                            )
                            logger.info("🔄 Restored webhook URL: %s", webhook_url)
                    except Exception:
                        pass

            watchdog_task = asyncio.create_task(_webhook_watchdog())
            await stop_event.wait()
            watchdog_task.cancel()
        except TelegramError as e:
            logger.warning("Webhook setup notice (%s); switching to direct update queue.", e)
            webhook_base = ""

    if not webhook_base:
        BOT_RUNTIME_STATUS["mode"] = "polling_live"
        BOT_RUNTIME_STATUS["bot_running"] = True
        await _custom_polling_loop(app, stop_event)

    logger.info("🛑 Shutting down bot cleanly…")
    BOT_RUNTIME_STATUS["bot_running"] = False
    try:
        if app.running:
            await app.stop()
        await app.shutdown()
    except Exception:
        pass


def main() -> None:
    init_db()
    logger.info("Database initialized: %s", DB_PATH)
    port = int(os.environ.get("PORT", 3000))

    if not PTB_AVAILABLE or not validate_bot_token(BOT_TOKEN):
        BOT_RUNTIME_STATUS["mode"] = "standby_control_center"
        BOT_RUNTIME_STATUS["bot_running"] = False
        seed_demo_data_if_empty()
        from app import run_control_center_server

        run_control_center_server(port=port, acquire_lock=True)
        return

    if not acquire_single_instance_lock():
        BOT_RUNTIME_STATUS["mode"] = "standby_lock_held"
        logger.warning("Another local process holds the lock; exiting duplicate worker cleanly.")
        return

    # Bind HTTP Control Center & Webhook receiver on 0.0.0.0:$PORT synchronously
    # BEFORE entering the asyncio bot loop so Render detects the HTTP port in <1s
    http_server = None
    try:
        from app import create_control_center_server

        http_server = create_control_center_server(port=port, acquire_lock=False)
        threading.Thread(
            target=http_server.serve_forever,
            kwargs={"poll_interval": 0.1},
            daemon=True,
        ).start()
    except Exception as e:
        logger.warning("HTTP server notice: %s", e)

    try:
        asyncio.run(_run_bot_lifecycle())
    except InvalidToken as e:
        BOT_RUNTIME_STATUS["mode"] = "invalid_token"
        BOT_RUNTIME_STATUS["bot_running"] = False
        BOT_RUNTIME_STATUS["last_error"] = f"InvalidToken: {e}"
        logger.error("❌ BOT_TOKEN rejected by Telegram (%s).", e)
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if http_server is not None:
            try:
                http_server.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    main()
