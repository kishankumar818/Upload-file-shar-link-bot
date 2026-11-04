#!/usr/bin/env python3
# =====================================================================
#   ✦  𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗙𝗜𝗟𝗘 𝗩𝗔𝗨𝗟𝗧  —  24/7 ULTRA-FAST TELEGRAM BOT  ✦
# =====================================================================
#  FEATURES
#   • Instant <1s /start response with parallel membership cache
#   • 24/7 Keep-Alive self-ping heartbeat + Zero-Conflict Webhook/Polling
#   • Real Colorful Inline Buttons & VIP Unique Card UI
#   • File + Direct Link (URL) Upload with Custom Name & 4-6 Digit Random ID:
#       https://t.me/<BOT>?start=NAME?RANDOM_NUMBER
#   • /group-upload for permanent image/file links with Group Name + Name + 4-6 Digit ID:
#       https://t.me/<BOT>?start=GroupName?Name=RANDOM_NUMBER
#   • /Group-image-description & /ad-group for 15-Minute Group Banner Auto-Send & Delete
#   • 100% Permanent Storage (SQLite WAL + JSON Mirror) — never deletes files/images/links
#     unless explicitly deleted by Admin.
# =====================================================================

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import random
import re
import secrets
import signal
import sqlite3
import sys
import threading
import time
import urllib.request
import warnings
from datetime import datetime, timedelta, timezone
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
GROUP_BANNER_INTERVAL_SECONDS: int = int(os.getenv("GROUP_BANNER_INTERVAL_SECONDS", "900"))

KEEP_ALIVE_INTERVAL_SECONDS: int = int(os.getenv("KEEP_ALIVE_INTERVAL_SECONDS", "300"))

BOT_RUNTIME_STATUS: dict[str, Any] = {
    "mode": "initializing",
    "bot_running": False,
    "bot_username": os.getenv("BOT_USERNAME", "FILE_SHARE_00_bot").strip().lstrip("@") or "FILE_SHARE_00_bot",
    "token_valid": validate_bot_token(BOT_TOKEN),
    "ptb_installed": PTB_AVAILABLE,
    "webhook_url": "",
    "conflict_count": 0,
    "last_conflict_at": None,
    "last_error": None,
    "webhook_cleared": False,
    "single_instance_locked": False,
    "keep_alive_active": True,
    "keep_alive_interval_seconds": KEEP_ALIVE_INTERVAL_SECONDS,
    "keep_alive_pings": 0,
    "webhook_registrations": 0,
    "last_keep_alive_at": datetime.now(timezone.utc).isoformat(),
    "last_webhook_registered_at": None,
    "response_target_ms": "<100ms",
    "permanent_storage": True,
    "group_banner_interval_min": 15,
    "started_at": datetime.now(timezone.utc).isoformat(),
}

_ACTIVE_PTB_APP: Any = None
_ACTIVE_BOT_LOOP: asyncio.AbstractEventLoop | None = None
_BOT_THREAD: threading.Thread | None = None
_KEEPALIVE_STARTED = False

# Fast 15-second membership cache so /start and Verify respond in <100ms
_MEMBERSHIP_CACHE: dict[tuple[int, int], tuple[bool, float]] = {}
MEMBERSHIP_CACHE_TTL = 12.0


def get_active_bot_app() -> tuple[Any, asyncio.AbstractEventLoop | None]:
    return _ACTIVE_PTB_APP, _ACTIVE_BOT_LOOP


def resolve_keepalive_webhook_target(custom_base_url: str | None = None) -> str:
    """
    Resolves the bot's public HTTPS URL for the 5-minute Keep-Alive Telegram webhook registration.
    """
    base = (custom_base_url or "").strip().rstrip("/")
    if not base:
        base = resolve_webhook_base_url()
    if not base:
        app_url = os.getenv("APP_URL", "").strip().rstrip("/")
        if app_url.startswith("https://"):
            base = app_url
    if base.startswith("https://"):
        return (
            base
            if base.endswith("/telegram-webhook")
            else f"{base}/telegram-webhook"
        )
    return ""


def register_webhook_heartbeat(
    bot_token: str | None = None,
    base_url: str | None = None,
    port: int = 3000,
) -> dict[str, Any]:
    """
    Keep-Alive Heartbeat action:
    1) Pings local and external health endpoints so the instance stays awake 24/7.
    2) Registers the bot's webhook URL with the Telegram API (`setWebhook`) every 5 minutes
       so the webhook remains active 24/7 without manual restarts.
    """
    active_token = (bot_token or BOT_TOKEN).strip()
    webhook_url = resolve_keepalive_webhook_target(base_url)
    now_str = datetime.now(timezone.utc).isoformat()

    # 1. Self-ping HTTP health check endpoints
    ping_targets = [f"http://127.0.0.1:{port}/ping"]
    ext_base = resolve_webhook_base_url() or os.getenv("APP_URL", "").strip().rstrip("/")
    if ext_base.startswith("https://"):
        ping_targets.append(f"{ext_base}/ping")

    for p_url in ping_targets:
        try:
            req = urllib.request.Request(p_url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as _:
                pass
        except Exception:
            pass

    BOT_RUNTIME_STATUS["keep_alive_active"] = True
    BOT_RUNTIME_STATUS["keep_alive_interval_seconds"] = KEEP_ALIVE_INTERVAL_SECONDS
    BOT_RUNTIME_STATUS["keep_alive_pings"] = (
        int(BOT_RUNTIME_STATUS.get("keep_alive_pings", 0)) + 1
    )
    BOT_RUNTIME_STATUS["last_keep_alive_at"] = now_str

    # 2. Register webhook URL with Telegram API if token & HTTPS webhook URL are available
    webhook_registered = False
    if webhook_url:
        BOT_RUNTIME_STATUS["webhook_url"] = webhook_url

    if validate_bot_token(active_token) and webhook_url:
        try:
            tg_api_url = f"https://api.telegram.org/bot{active_token}/setWebhook"
            payload_bytes = json.dumps(
                {
                    "url": webhook_url,
                    "drop_pending_updates": False,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                tg_api_url,
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                if resp_data.get("ok"):
                    webhook_registered = True
        except Exception as e:
            logger.debug("Keep-Alive setWebhook HTTP notice: %s", e)

        # Also schedule via active PTB bot loop if running
        if not webhook_registered and _ACTIVE_PTB_APP is not None and _ACTIVE_BOT_LOOP is not None:
            try:
                fut = asyncio.run_coroutine_threadsafe(
                    _ACTIVE_PTB_APP.bot.set_webhook(
                        url=webhook_url,
                        allowed_updates=Update.ALL_TYPES,
                        drop_pending_updates=False,
                    ),
                    _ACTIVE_BOT_LOOP,
                )
                fut.result(timeout=5.0)
                webhook_registered = True
            except Exception:
                pass

    if webhook_registered or webhook_url:
        BOT_RUNTIME_STATUS["webhook_registrations"] = (
            int(BOT_RUNTIME_STATUS.get("webhook_registrations", 0)) + 1
        )
        BOT_RUNTIME_STATUS["last_webhook_registered_at"] = now_str

    return {
        "ok": True,
        "keep_alive_active": True,
        "interval_seconds": KEEP_ALIVE_INTERVAL_SECONDS,
        "webhook_url": webhook_url,
        "webhook_registered": webhook_registered,
        "keep_alive_pings": BOT_RUNTIME_STATUS["keep_alive_pings"],
        "webhook_registrations": BOT_RUNTIME_STATUS["webhook_registrations"],
        "last_keep_alive_at": BOT_RUNTIME_STATUS["last_keep_alive_at"],
        "last_webhook_registered_at": BOT_RUNTIME_STATUS["last_webhook_registered_at"],
    }


def start_keep_alive_daemon(port: int = 3000) -> None:
    """
    Starts the 24/7 Keep-Alive Heartbeat background service:
    - Runs an initial heartbeat registration right after boot
    - Re-registers the bot's URL with the Telegram API every 5 minutes (300s)
      while keeping local/external HTTP endpoints warm.
    """
    global _KEEPALIVE_STARTED
    if _KEEPALIVE_STARTED:
        return
    _KEEPALIVE_STARTED = True

    def _heartbeat_worker() -> None:
        # Initial registration shortly after startup
        time.sleep(2)
        try:
            register_webhook_heartbeat(port=port)
        except Exception:
            pass

        last_webhook_sync = time.monotonic()
        while True:
            time.sleep(60)
            now_mono = time.monotonic()
            # Every 5 minutes (300s), run full Telegram API webhook registration heartbeat
            if (now_mono - last_webhook_sync) >= KEEP_ALIVE_INTERVAL_SECONDS:
                last_webhook_sync = now_mono
                try:
                    register_webhook_heartbeat(port=port)
                    logger.info(
                        "💓 5-Minute Keep-Alive Heartbeat: Webhook registered & verified active 24/7."
                    )
                except Exception as e:
                    logger.debug("Keep-alive heartbeat error: %s", e)
            else:
                # Lightweight local ping every 60s between 5-minute webhook registrations
                try:
                    req = urllib.request.Request(f"http://127.0.0.1:{port}/ping", method="GET")
                    with urllib.request.urlopen(req, timeout=4) as _:
                        pass
                    BOT_RUNTIME_STATUS["keep_alive_pings"] = (
                        int(BOT_RUNTIME_STATUS.get("keep_alive_pings", 0)) + 1
                    )
                    BOT_RUNTIME_STATUS["last_keep_alive_at"] = datetime.now(timezone.utc).isoformat()
                except Exception:
                    pass

    threading.Thread(
        target=_heartbeat_worker, daemon=True, name="vault-keepalive-5m"
    ).start()


def ensure_bot_background_thread() -> None:
    """Ensures the live Telegram bot loop is running in a background thread when token is valid."""
    global _BOT_THREAD
    if not PTB_AVAILABLE or not validate_bot_token(BOT_TOKEN):
        return
    if _BOT_THREAD is not None and _BOT_THREAD.is_alive():
        return

    def _runner() -> None:
        try:
            asyncio.run(_run_bot_lifecycle())
        except Exception as e:
            BOT_RUNTIME_STATUS["last_error"] = str(e)
            logger.warning("Background bot thread exited: %s", e)

    _BOT_THREAD = threading.Thread(target=_runner, daemon=True, name="vault-ptb-bot")
    _BOT_THREAD.start()


def save_env_config(
    bot_token: str | None = None,
    admin_ids: str | list[int] | None = None,
    bot_name: str | None = None,
    db_path: str | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Updates configuration in memory and writes both .env and .evn."""
    global BOT_TOKEN, ADMIN_IDS, BOT_NAME, RAW_DB_PATH, DB_PATH

    token_changed = False
    if bot_token is not None and bot_token.strip():
        new_tok = bot_token.strip()
        if new_tok != BOT_TOKEN:
            token_changed = True
        BOT_TOKEN = new_tok
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
    if webhook_url is not None and webhook_url.strip().startswith("https://"):
        clean_wh = webhook_url.strip().rstrip("/")
        if clean_wh.endswith("/telegram-webhook"):
            clean_wh = clean_wh[: -len("/telegram-webhook")]
        os.environ["WEBHOOK_URL"] = clean_wh

    BOT_RUNTIME_STATUS["token_valid"] = validate_bot_token(BOT_TOKEN)

    db_rel = Path(DB_PATH).name if Path(DB_PATH).parent == _ROOT_DIR else DB_PATH
    wh_env = os.getenv("WEBHOOK_URL", "").strip()
    env_content = (
        f"BOT_TOKEN={BOT_TOKEN or 'YOUR_BOT_TOKEN_HERE'}\n"
        f"ADMIN_IDS={','.join(str(x) for x in ADMIN_IDS) if ADMIN_IDS else '123456789'}\n"
        f"BOT_NAME={BOT_NAME}\n"
        f"DB_PATH={db_rel}\n"
        + (f"WEBHOOK_URL={wh_env}\n" if wh_env else "")
    )
    for fname in (".env", ".evn"):
        try:
            (_ROOT_DIR / fname).write_text(env_content, encoding="utf-8")
        except OSError as e:
            logger.warning("Could not write %s: %s", fname, e)

    if token_changed and validate_bot_token(BOT_TOKEN):
        ensure_bot_background_thread()
        register_webhook_heartbeat()

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
#  1) 🌈 COLORFUL THEME & VIP UI BUILDERS
# =====================================================================
TOP = "✦━━━━━━━━━━━━━━━━━━━━━━✦"

FILE_ICONS = {
    "document": "📄",
    "video": "🎬",
    "photo": "🖼️",
    "audio": "🎵",
    "voice": "🎙️",
    "animation": "🎞️",
    "link": "🌐",
}

# Real Colorful Button Styles
BLUE = "primary"
GREEN = "success"
RED = "danger"
PURPLE = "purple"
ORANGE = "amber"
CYAN = "cyan"
PINK = "pink"
GOLD = "gold"

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
        out += ["", f"<i>⚡ {esc(smallcaps(footer + ' • 24/7 fast active'))} ⚡</i>"]
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
    if url:
        b = InlineKeyboardButton(text=text, url=url)
    else:
        b = InlineKeyboardButton(text=text, callback_data=data or "noop")
    try:
        setattr(b, "color_style", style or BLUE)
    except (AttributeError, TypeError):
        pass
    return b


def kb(
    *rows: list[InlineKeyboardButton] | tuple[InlineKeyboardButton, ...]
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([list(r) for r in rows if r])


def cancel_kb() -> InlineKeyboardMarkup:
    return kb([btn("🔴 ❌ Cancel Operation", "cancel", style=RED)])


def panel_kb() -> InlineKeyboardMarkup:
    return kb(
        [
            btn("🟢 📤 Upload File / Link (Lifetime)", "adm:upload", style=GREEN),
            btn("🟣 📸 /group-upload", "adm:grupload", style=PURPLE),
        ],
        [
            btn("🔵 📂 Permanent Vault", "adm:files", style=BLUE),
            btn("🟠 ➕ Add Force Channel", "adm:addch", style=ORANGE),
        ],
        [
            btn("🩷 🖼️ /Group-image-description", "adm:grpbanner", style=PINK),
            btn("🩵 👥 /ad-group (15m Loop)", "adm:adgroup", style=CYAN),
        ],
        [
            btn("🦄 🤖 /BOT-build (User Builder)", "adm:botbuild", style=PURPLE),
            btn("✨ 📝 /BOT-build-description", "adm:botbuilddesc", style=GOLD),
        ],
        [
            btn("🎛️ ⚙️ /start Features Control", "adm:startcfg", style=CYAN),
            btn("💎 🔑 /Pro-plan Secret Key", "adm:prokey", style=GOLD),
        ],
        [
            btn("🟡 📢 Channels List", "adm:channels", style=GOLD),
            btn("🔴 📣 Broadcast All", "adm:bcast", style=RED),
        ],
        [
            btn("💎 📊 Live Stats & User Bots", "adm:stats", style=BLUE),
        ],
    )


def home_kb() -> InlineKeyboardMarkup:
    return kb([btn("🔵 🛠 Back to VIP Admin Panel", "adm:home", style=BLUE)])


CANCEL_TEXT = "❌ Cancel"


def select_chat_keyboard(for_group_only: bool = False) -> ReplyKeyboardMarkup | None:
    try:
        rights = ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=True,
        )
        group_req = KeyboardButtonRequestChat(
            request_id=2,
            chat_is_channel=False,
            user_administrator_rights=rights,
            bot_administrator_rights=rights,
        )
        if for_group_only:
            rows = [
                [KeyboardButton("👥 Select Group (Admin)", request_chat=group_req)],
                [KeyboardButton(CANCEL_TEXT)],
            ]
        else:
            channel_req = KeyboardButtonRequestChat(
                request_id=1,
                chat_is_channel=True,
                user_administrator_rights=rights,
                bot_administrator_rights=rights,
            )
            rows = [
                [
                    KeyboardButton("📢 Select Channel", request_chat=channel_req),
                    KeyboardButton("👥 Select Group", request_chat=group_req),
                ],
                [KeyboardButton(CANCEL_TEXT)],
            ]
        return ReplyKeyboardMarkup(
            rows,
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="@username ya -100... ID bhi bhej sakte hain",
        )
    except Exception as e:
        logger.warning("Select-chat keyboard unavailable: %s", e)
        return None


# =====================================================================
#  2) 🔗 CUSTOM LINK GENERATOR & RESOLVER (4-6 DIGIT RANDOM NUMBER)
# =====================================================================
def generate_random_digits(digits: int = 6) -> str:
    """Generates a 4 to 6 digit random numeric string (e.g. '4829' or '583921')."""
    d = max(4, min(6, int(digits or 6)))
    low = 10 ** (d - 1)
    high = (10**d) - 1
    return str(random.randint(low, high))


def clean_slug_part(text: str | None, fallback: str = "FILE") -> str:
    """Cleans a name or group name so it looks neat in links."""
    raw = (text or "").strip()
    if not raw:
        return fallback
    # Remove file extension if it looks like .zip/.mp4/.jpg
    raw = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", raw)
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")
    return (cleaned[:28] if cleaned else fallback)


def build_share_code(
    custom_name: str,
    random_code: str,
    group_name: str = "",
) -> str:
    """
    Builds the canonical share token stored in DB:
    - If group_name is provided (/group-upload):
        '{group_name}?{custom_name}={random_code}'
    - Otherwise (standard file/link upload):
        '{custom_name}?{random_code}'
    """
    c_name = clean_slug_part(custom_name, "FILE")
    r_code = str(random_code or generate_random_digits(6)).strip()
    if not r_code.isdigit() or not (4 <= len(r_code) <= 6):
        r_code = generate_random_digits(6)
    if group_name and group_name.strip():
        g_name = clean_slug_part(group_name, "GROUP")
        return f"{g_name}?{c_name}={r_code}"
    return f"{c_name}?{r_code}"


def build_safe_deep_payload(
    custom_name: str,
    random_code: str,
    group_name: str = "",
) -> str:
    """
    Builds Telegram-safe [A-Za-z0-9_-] start payload so Telegram clients never truncate at '?':
    - Group upload: '{group_name}__{custom_name}__{random_code}'
    - Normal upload: '{custom_name}__{random_code}'
    """
    c_name = clean_slug_part(custom_name, "FILE")
    r_code = str(random_code or "482915").strip()
    if group_name and group_name.strip():
        g_name = clean_slug_part(group_name, "GROUP")
        return f"{g_name}__{c_name}__{r_code}"
    return f"{c_name}__{r_code}"


def file_link(username: str, file_or_id: int | sqlite3.Row | dict[str, Any]) -> str:
    """
    Generates the shareable link for a file/link/group-upload item.
    - If a DB row exists with custom_name & random_code:
        * Group upload: https://t.me/<bot>?start=<GroupName>?<Name>=<4-6DigitRandom>
        * Normal upload: https://t.me/<bot>?start=<NAME>?<4-6DigitRandom>
    - Legacy fallback (when called with an unseeded integer ID in unit tests):
        https://t.me/<bot>?start=file_<id>
    """
    clean_uname = (username or "FILE_SHARE_00_bot").lstrip("@")
    row: sqlite3.Row | dict[str, Any] | None = None
    if isinstance(file_or_id, (dict, sqlite3.Row)):
        row = file_or_id
    else:
        try:
            row = get_file(int(file_or_id))
        except Exception:
            row = None

    if row is not None:
        r_dict = dict(row)
        custom_name = (r_dict.get("custom_name") or "").strip()
        random_code = (r_dict.get("random_code") or "").strip()
        group_name = (r_dict.get("group_name") or "").strip()
        share_code = (r_dict.get("share_code") or "").strip()
        if share_code:
            return f"https://t.me/{clean_uname}?start={share_code}"
        if custom_name and random_code:
            code = build_share_code(custom_name, random_code, group_name)
            return f"https://t.me/{clean_uname}?start={code}"

    fid = int(file_or_id["id"]) if isinstance(file_or_id, (dict, sqlite3.Row)) else int(file_or_id)
    return f"https://t.me/{clean_uname}?start=file_{fid}"


def file_tg_safe_link(username: str, file_or_id: int | sqlite3.Row | dict[str, Any]) -> str:
    """Returns a 100% Telegram-client-safe deep link (?start=Name__Random or Group__Name__Random)."""
    clean_uname = (username or "FILE_SHARE_00_bot").lstrip("@")
    row = (
        file_or_id
        if isinstance(file_or_id, (dict, sqlite3.Row))
        else get_file(int(file_or_id))
    )
    if row is not None:
        r_dict = dict(row)
        custom_name = (r_dict.get("custom_name") or r_dict.get("file_name") or "FILE").strip()
        random_code = (r_dict.get("random_code") or "").strip()
        group_name = (r_dict.get("group_name") or "").strip()
        if random_code:
            payload = build_safe_deep_payload(custom_name, random_code, group_name)
            return f"https://t.me/{clean_uname}?start={payload}"
        return f"https://t.me/{clean_uname}?start=file_{r_dict['id']}"
    fid = int(file_or_id) if not isinstance(file_or_id, (dict, sqlite3.Row)) else int(file_or_id["id"])
    return f"https://t.me/{clean_uname}?start=file_{fid}"


# =====================================================================
#  3) 🗄️ PERMANENT DATABASE (bot_data.db + JSON Mirror Backup)
# =====================================================================
conn: sqlite3.Connection | None = None
db_lock = threading.RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _backup_json_path() -> Path:
    return Path(f"{DB_PATH}.permanent_backup.json")


def _connect_db(path: str | None = None) -> sqlite3.Connection:
    target = path or DB_PATH
    c = sqlite3.connect(target, timeout=15.0, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=FULL;")
    c.execute("PRAGMA busy_timeout=10000;")
    return c


def _sync_permanent_backup() -> None:
    """
    Writes a permanent JSON snapshot of all channels, files/links, banner config,
    and managed groups so data is NEVER lost or auto-deleted across restarts.
    """
    try:
        with db_lock:
            if conn is None:
                return
            data = {
                "channels": [dict(r) for r in conn.execute("SELECT * FROM channels").fetchall()],
                "files": [dict(r) for r in conn.execute("SELECT * FROM files").fetchall()],
                "group_banner": [
                    dict(r) for r in conn.execute("SELECT * FROM group_banner_config").fetchall()
                ],
                "managed_groups": [
                    dict(r) for r in conn.execute("SELECT * FROM managed_groups").fetchall()
                ],
                "bot_builder": [
                    dict(r) for r in conn.execute("SELECT * FROM bot_builder_config").fetchall()
                ],
                "user_bots": [
                    dict(r) for r in conn.execute("SELECT * FROM user_bots").fetchall()
                ],
            }
            _backup_json_path().write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    except Exception as e:
        logger.debug("Backup mirror note: %s", e)


def _restore_from_permanent_backup_if_needed(db: sqlite3.Connection) -> None:
    """Restores permanent records if SQLite file was recreated from scratch."""
    bpath = _backup_json_path()
    if not bpath.exists():
        return
    try:
        file_count = int(db.execute("SELECT COUNT(*) FROM files").fetchone()[0])
        ch_count = int(db.execute("SELECT COUNT(*) FROM channels").fetchone()[0])
        if file_count > 0 or ch_count > 0:
            return
        payload = json.loads(bpath.read_text(encoding="utf-8"))
        for ch in payload.get("channels", []):
            db.execute(
                """
                INSERT OR IGNORE INTO channels (id, chat_id, title, username, invite_link, added_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ch.get("id"),
                    ch["chat_id"],
                    ch.get("title", ""),
                    ch.get("username", ""),
                    ch.get("invite_link", ""),
                    ch.get("added_at", now_iso()),
                ),
            )
        for f in payload.get("files", []):
            db.execute(
                """
                INSERT OR IGNORE INTO files (
                    id, tg_file_id, file_type, file_name, custom_name, group_name,
                    random_code, share_code, external_url, is_permanent, caption,
                    created_by, created_at, downloads
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f.get("id"),
                    f.get("tg_file_id", ""),
                    f.get("file_type", "document"),
                    f.get("file_name", ""),
                    f.get("custom_name", ""),
                    f.get("group_name", ""),
                    f.get("random_code", ""),
                    f.get("share_code", ""),
                    f.get("external_url", ""),
                    1,
                    f.get("caption", ""),
                    f.get("created_by", 0),
                    f.get("created_at", now_iso()),
                    f.get("downloads", 0),
                ),
            )
        for gb in payload.get("group_banner", []):
            db.execute(
                """
                INSERT OR REPLACE INTO group_banner_config (
                    id, banner_file_id, banner_type, description, verified, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    gb.get("id", 1),
                    gb.get("banner_file_id", ""),
                    gb.get("banner_type", "photo"),
                    gb.get("description", ""),
                    gb.get("verified", 1),
                    gb.get("updated_at", now_iso()),
                ),
            )
        for mg in payload.get("managed_groups", []):
            db.execute(
                """
                INSERT OR IGNORE INTO managed_groups (
                    id, chat_id, title, username, invite_link, banner_file_id,
                    description, interval_minutes, last_message_id, last_sent_at,
                    send_count, active, added_by, added_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mg.get("id"),
                    mg["chat_id"],
                    mg.get("title", ""),
                    mg.get("username", ""),
                    mg.get("invite_link", ""),
                    mg.get("banner_file_id", ""),
                    mg.get("description", ""),
                    mg.get("interval_minutes", 15),
                    mg.get("last_message_id"),
                    mg.get("last_sent_at"),
                    mg.get("send_count", 0),
                    mg.get("active", 1),
                    mg.get("added_by", 0),
                    mg.get("added_at", now_iso()),
                ),
            )
        db.commit()
    except Exception as e:
        logger.warning("Restore from backup notice: %s", e)


def init_db(custom_path: str | None = None) -> None:
    """Initializes bot_data.db with all permanent tables and columns."""
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
                custom_name TEXT DEFAULT '',
                group_name TEXT DEFAULT '',
                random_code TEXT DEFAULT '',
                share_code TEXT DEFAULT '',
                external_url TEXT DEFAULT '',
                is_permanent INTEGER NOT NULL DEFAULT 1,
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

            CREATE TABLE IF NOT EXISTS group_banner_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                banner_file_id TEXT NOT NULL,
                banner_type TEXT NOT NULL DEFAULT 'photo',
                description TEXT NOT NULL,
                verified INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS managed_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                title TEXT NOT NULL,
                username TEXT DEFAULT '',
                invite_link TEXT DEFAULT '',
                banner_file_id TEXT DEFAULT '',
                description TEXT DEFAULT '',
                interval_minutes INTEGER NOT NULL DEFAULT 15,
                last_message_id INTEGER,
                last_sent_at TEXT,
                send_count INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                added_by INTEGER,
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bot_builder_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                description TEXT NOT NULL,
                allow_bot_build INTEGER NOT NULL DEFAULT 1,
                allow_user_upload INTEGER NOT NULL DEFAULT 1,
                allow_user_two_channels INTEGER NOT NULL DEFAULT 1,
                allow_pro_plan INTEGER NOT NULL DEFAULT 1,
                pro_plan_secret_key TEXT NOT NULL DEFAULT 'FILE-SHARE-YU6J-IEHU-828H',
                pro_key_used_by INTEGER NOT NULL DEFAULT 0,
                pro_key_used_at TEXT NOT NULL DEFAULT '',
                show_start_help INTEGER NOT NULL DEFAULT 1,
                start_welcome_text TEXT NOT NULL DEFAULT '',
                user_file_expiry_days INTEGER NOT NULL DEFAULT 7,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                owner_name TEXT NOT NULL DEFAULT '',
                bot_token TEXT NOT NULL,
                bot_username TEXT NOT NULL,
                bot_name TEXT NOT NULL,
                channel_1_title TEXT DEFAULT '',
                channel_1_link TEXT DEFAULT '',
                channel_2_title TEXT DEFAULT '',
                channel_2_link TEXT DEFAULT '',
                channel_3_title TEXT DEFAULT '',
                channel_3_link TEXT DEFAULT '',
                channel_4_title TEXT DEFAULT '',
                channel_4_link TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'online_24_7',
                created_at TEXT NOT NULL
            );
            """
        )

        # Ensure new columns exist on existing databases
        alter_statements = [
            "ALTER TABLE files ADD COLUMN downloads INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE files ADD COLUMN custom_name TEXT DEFAULT ''",
            "ALTER TABLE files ADD COLUMN group_name TEXT DEFAULT ''",
            "ALTER TABLE files ADD COLUMN random_code TEXT DEFAULT ''",
            "ALTER TABLE files ADD COLUMN share_code TEXT DEFAULT ''",
            "ALTER TABLE files ADD COLUMN external_url TEXT DEFAULT ''",
            "ALTER TABLE files ADD COLUMN is_permanent INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE files ADD COLUMN uploader_role TEXT NOT NULL DEFAULT 'admin'",
            "ALTER TABLE files ADD COLUMN expires_at TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN used_bot_build INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN used_user_upload INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_pro INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN pro_activated_at TEXT DEFAULT ''",
            "ALTER TABLE bot_builder_config ADD COLUMN allow_pro_plan INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE bot_builder_config ADD COLUMN pro_plan_secret_key TEXT NOT NULL DEFAULT 'FILE-SHARE-YU6J-IEHU-828H'",
            "ALTER TABLE bot_builder_config ADD COLUMN pro_key_used_by INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE bot_builder_config ADD COLUMN pro_key_used_at TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE bot_builder_config ADD COLUMN show_start_help INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE bot_builder_config ADD COLUMN start_welcome_text TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN channel_3_title TEXT DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN channel_3_link TEXT DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN channel_4_title TEXT DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN channel_4_link TEXT DEFAULT ''",
        ]
        for stmt in alter_statements:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass

        # Migrate old default key if still set to VIP-PRO-2026
        try:
            conn.execute(
                "UPDATE bot_builder_config SET pro_plan_secret_key = 'FILE-SHARE-YU6J-IEHU-828H' WHERE pro_plan_secret_key = 'VIP-PRO-2026' OR pro_plan_secret_key = ''"
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()
        if not custom_path:
            _restore_from_permanent_backup_if_needed(conn)


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


def is_user_pro(user_or_id: Any) -> bool:
    """Returns True if the user is an Admin or has activated /Pro-plan with the Secret Key."""
    if is_admin(user_or_id):
        return True
    uid = getattr(user_or_id, "id", user_or_id)
    try:
        uid_int = int(uid)
    except (TypeError, ValueError):
        return False
    with db_lock:
        db = ensure_db()
        row = db.execute(
            "SELECT is_pro FROM users WHERE user_id = ?", (uid_int,)
        ).fetchone()
        return bool(row and int(row["is_pro"] or 0) == 1)


def set_user_pro_status(user_id: int, is_pro: bool, first_name: str = "") -> bool:
    """Sets or revokes a user's /Pro-plan Lifetime Unlimited upload & 4-channel status."""
    uid = int(user_id)
    pro_val = 1 if is_pro else 0
    ts = now_iso() if is_pro else ""
    with db_lock:
        db = ensure_db()
        save_user(uid, first_name or f"User {uid}", "")
        db.execute(
            "UPDATE users SET is_pro = ?, pro_activated_at = ? WHERE user_id = ?",
            (pro_val, ts, uid),
        )
        if is_pro:
            # Upgrade any existing 7-day files of this user to Lifetime Permanent
            db.execute(
                "UPDATE files SET is_permanent = 1, expires_at = '', uploader_role = 'pro' WHERE created_by = ?",
                (uid,),
            )
        else:
            # If revoked and this user was holding the single-use key, free the single-use slot
            db.execute(
                "UPDATE bot_builder_config SET pro_key_used_by = 0, pro_key_used_at = '' WHERE pro_key_used_by = ?",
                (uid,),
            )
        db.commit()
        _sync_permanent_backup()
        return True


def normalize_pro_key_input(raw_key: str) -> str:
    """Normalizes a key or deep-link start token (strips optional PRO_ or proplan_ prefix)."""
    candidate = (raw_key or "").strip()
    for prefix in ("PRO_", "pro_", "PRO-", "pro-", "proplan_", "PROPLAN_"):
        if candidate.startswith(prefix) and not candidate.upper().startswith("FILE-SHARE-"):
            candidate = candidate[len(prefix) :].strip()
            break
    if candidate.upper().startswith("PRO_FILE-SHARE-"):
        candidate = candidate[4:].strip()
    return candidate


def is_pro_plan_start_token(raw_token: str) -> bool:
    """Returns True if raw_token is a Pro Plan activation deep link token."""
    t = (raw_token or "").strip()
    if not t:
        return False
    cfg = get_bot_builder_config()
    expected = (cfg.get("pro_plan_secret_key") or DEFAULT_PRO_PLAN_SECRET_KEY).strip()
    normalized = normalize_pro_key_input(t)
    if normalized == expected:
        return True
    if t.upper().startswith("PRO_") or t.upper().startswith("FILE-SHARE-"):
        return True
    return False


def reset_pro_plan_single_use_link() -> dict[str, Any]:
    """Re-arms the single-use Pro Plan activation link so the next user who clicks it can activate Pro Plan."""
    with db_lock:
        db = ensure_db()
        db.execute(
            """
            INSERT INTO bot_builder_config (id, description, pro_plan_secret_key, pro_key_used_by, pro_key_used_at, updated_at)
            VALUES (1, ?, ?, 0, '', ?)
            ON CONFLICT(id) DO UPDATE SET
                pro_key_used_by = 0,
                pro_key_used_at = '',
                updated_at = excluded.updated_at
            """,
            (DEFAULT_BOT_BUILD_DESCRIPTION, DEFAULT_PRO_PLAN_SECRET_KEY, now_iso()),
        )
        db.commit()
        _sync_permanent_backup()
        return get_bot_builder_config()


def activate_user_pro_plan(
    user_id: int,
    entered_key: str,
    first_name: str = "",
    username: str = "",
) -> tuple[bool, str]:
    """
    Verifies the /Pro-plan Secret Key or single-use deep-link token entered by a user.
    - Enforces single-use per link click: once claimed by a user, another user cannot claim the same link until Admin resets it.
    - Upgrades the user to Pro Plan (Unlimited Lifetime Permanent uploads + 4 User Force-Join Channels with Admin channels removed).
    """
    uid = int(user_id or 0)
    cfg = get_bot_builder_config()
    expected_key = (cfg.get("pro_plan_secret_key") or DEFAULT_PRO_PLAN_SECRET_KEY).strip()
    candidate = normalize_pro_key_input(entered_key)
    if not candidate or candidate != expected_key:
        return (
            False,
            "❌ Invalid Secret Key / Activation Link! Kripya Admin se valid Pro Plan Activation Link lein.",
        )

    used_by = int(cfg.get("pro_key_used_by") or 0)
    if used_by != 0 and used_by != uid and not is_admin(uid):
        return (
            False,
            "⚠️ Yeh Single-Use Pro Plan Link pehle hi use ho chuka hai! Naya Pro Plan Link lene ke liye Admin se sampark karein.",
        )

    save_user(uid, first_name, username)
    set_user_pro_status(uid, True, first_name=first_name)
    if not is_admin(uid):
        with db_lock:
            db = ensure_db()
            db.execute(
                """
                INSERT INTO bot_builder_config (id, description, pro_plan_secret_key, pro_key_used_by, pro_key_used_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    pro_key_used_by = excluded.pro_key_used_by,
                    pro_key_used_at = excluded.pro_key_used_at,
                    updated_at = excluded.updated_at
                """,
                (
                    cfg.get("description") or DEFAULT_BOT_BUILD_DESCRIPTION,
                    expected_key,
                    uid,
                    now_iso(),
                    now_iso(),
                ),
            )
            db.commit()
            _sync_permanent_backup()

    return (
        True,
        "🦄✨💎 YOUR PRO PLAN ACTIVE! 💎✨🦄\n"
        "♾️ Unlimited Lifetime Uploads Unlocked!\n"
        "📢 Admin ke 2 Channels aapke bot se hata diye gaye hain — ab aap apne khud ke 4 Channels jod sakte hain!",
    )


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
        _sync_permanent_backup()
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
        _sync_permanent_backup()
        return cur.rowcount > 0


def save_file(
    tg_file_id: str,
    file_type: str,
    file_name: str,
    caption: str,
    created_by: int,
    custom_name: str = "",
    group_name: str = "",
    random_digits: int = 6,
    random_code: str = "",
    external_url: str = "",
    uploader_role: str = "admin",
) -> int:
    """
    Saves a File, Image (/group-upload), or Direct Link (URL) in bot_data.db.
    - If uploader_role == 'admin' OR user has /Pro-plan (is_user_pro): Saved for LIFETIME (is_permanent = 1, expires_at = ''). Never auto-deletes!
    - If uploader_role == 'user' (Free user without /Pro-plan): Saved for 1 WEEK / 7 DAYS (is_permanent = 0, expires_at = +7d).
    """
    uid = int(created_by or (ADMIN_IDS[0] if ADMIN_IDS else 0))
    user_has_pro = is_user_pro(uid)

    with db_lock:
        db = ensure_db()
        effective_custom_name = clean_slug_part(
            custom_name or file_name or ("Link" if file_type == "link" else "File"),
            fallback="FILE",
        )
        effective_group = clean_slug_part(group_name, fallback="") if group_name else ""
        r_code = (random_code or "").strip()
        if not (r_code.isdigit() and 4 <= len(r_code) <= 6):
            r_code = generate_random_digits(random_digits)

        # Ensure random_code uniqueness
        for _ in range(10):
            exists = db.execute(
                "SELECT 1 FROM files WHERE random_code = ?", (r_code,)
            ).fetchone()
            if not exists:
                break
            r_code = generate_random_digits(random_digits)

        s_code = build_share_code(effective_custom_name, r_code, effective_group)
        valid_type = file_type if file_type in FILE_ICONS else "document"
        raw_role = str(uploader_role).lower()
        if raw_role == "pro":
            role = "pro"
            is_perm = 1
            exp_at = ""
        elif raw_role == "user":
            if user_has_pro and uid not in ADMIN_IDS:
                role = "pro"
                is_perm = 1
                exp_at = ""
            else:
                role = "user"
                is_perm = 0
                exp_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        else:
            role = "admin"
            is_perm = 1
            exp_at = ""

        cur = db.execute(
            """
            INSERT INTO files (
                tg_file_id, file_type, file_name, custom_name, group_name,
                random_code, share_code, external_url, is_permanent, uploader_role,
                expires_at, caption, created_by, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tg_file_id or external_url or f"VAULT_{r_code}",
                valid_type,
                file_name or effective_custom_name,
                effective_custom_name,
                effective_group,
                r_code,
                s_code,
                external_url or (tg_file_id if valid_type == "link" else ""),
                is_perm,
                role,
                exp_at,
                caption or "",
                uid,
                now_iso(),
            ),
        )
        if role in ("user", "pro") and uid:
            db.execute(
                "UPDATE users SET used_user_upload = 1 WHERE user_id = ?",
                (uid,),
            )
        db.commit()
        _sync_permanent_backup()
        return int(cur.lastrowid)


def get_file(file_db_id: int) -> sqlite3.Row | None:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM files WHERE id = ?", (int(file_db_id),)
        ).fetchone()


def resolve_file_by_start_token(token: str | None) -> sqlite3.Row | None:
    """
    Resolves any start deep-link payload to its permanent file/link record:
    1) Legacy: 'file_<id>'
    2) Custom format: 'NAME?RANDOM' or 'NAME_RANDOM' or 'NAME__RANDOM'
    3) Group upload format: 'GroupName?Name=RANDOM' or 'GroupName__Name__RANDOM'
    4) Direct 4-6 digit random_code match
    5) Fallback match on custom_name or group_name if client truncated query string at '?'
    """
    raw = (token or "").strip()
    if not raw:
        return None

    with db_lock:
        db = ensure_db()

        # 1. Legacy file_<id>
        if raw.lower().startswith("file_") and raw[5:].isdigit():
            row = db.execute(
                "SELECT * FROM files WHERE id = ?", (int(raw[5:]),)
            ).fetchone()
            if row:
                return row

        # 2. Exact share_code match
        row = db.execute(
            "SELECT * FROM files WHERE lower(share_code) = lower(?) ORDER BY id DESC LIMIT 1",
            (raw,),
        ).fetchone()
        if row:
            return row

        # 3. Extract 4-6 digit random number at the end of the token
        m_num = re.search(r"(\d{4,6})$", raw)
        if m_num:
            r_code = m_num.group(1)
            row = db.execute(
                "SELECT * FROM files WHERE random_code = ? ORDER BY id DESC LIMIT 1",
                (r_code,),
            ).fetchone()
            if row:
                return row

        # 4. If token is purely numeric ID
        if raw.isdigit():
            row = db.execute(
                "SELECT * FROM files WHERE id = ? OR random_code = ? ORDER BY id DESC LIMIT 1",
                (int(raw), raw),
            ).fetchone()
            if row:
                return row

        # 5. If client truncated at '?' (e.g. 'NAME' or 'GroupName'), match custom_name or group_name
        clean_tok = clean_slug_part(raw, "")
        if clean_tok:
            row = db.execute(
                """
                SELECT * FROM files
                WHERE lower(custom_name) = lower(?)
                   OR lower(group_name) = lower(?)
                   OR lower(file_name) = lower(?)
                ORDER BY id DESC LIMIT 1
                """,
                (clean_tok, clean_tok, raw),
            ).fetchone()
            if row:
                return row

        return None


def get_files(limit: int = 50) -> list[sqlite3.Row]:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM files ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()


def delete_file(file_db_id: int) -> bool:
    """Only deletes when explicitly requested by Admin."""
    with db_lock:
        db = ensure_db()
        cur = db.execute("DELETE FROM files WHERE id = ?", (int(file_db_id),))
        db.execute("DELETE FROM pending WHERE file_id = ?", (int(file_db_id),))
        db.commit()
        _sync_permanent_backup()
        return cur.rowcount > 0


def delete_files_bulk(file_ids: list[int]) -> int:
    """Bulk deletes multiple selected files by ID when requested by Admin."""
    clean_ids = [int(x) for x in file_ids if str(x).isdigit()]
    if not clean_ids:
        return 0
    with db_lock:
        db = ensure_db()
        placeholders = ",".join("?" for _ in clean_ids)
        cur = db.execute(
            f"DELETE FROM files WHERE id IN ({placeholders})", tuple(clean_ids)
        )
        db.execute(
            f"DELETE FROM pending WHERE file_id IN ({placeholders})", tuple(clean_ids)
        )
        db.commit()
        _sync_permanent_backup()
        return int(cur.rowcount or 0)


def cleanup_expired_user_files() -> int:
    """
    Deletes ONLY expired Free user-uploaded files (/user-upload after 7 days / 1 week).
    NEVER deletes Admin's lifetime files OR /Pro-plan users' lifetime files (is_permanent = 1).
    """
    now_s = now_iso()
    with db_lock:
        db = ensure_db()
        cur = db.execute(
            """
            DELETE FROM files
            WHERE uploader_role = 'user'
              AND is_permanent = 0
              AND expires_at != ''
              AND expires_at <= ?
            """,
            (now_s,),
        )
        if cur.rowcount > 0:
            db.commit()
            _sync_permanent_backup()
        return int(cur.rowcount or 0)


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


# =====================================================================
#  3B) 🖼️ GROUP BANNER (/Group-image-description) & (/ad-group) STORAGE
# =====================================================================
def save_group_banner_config(
    banner_file_id: str,
    description: str,
    banner_type: str = "photo",
) -> dict[str, Any]:
    """Saves the verified banner image + description from /Group-image-description."""
    with db_lock:
        db = ensure_db()
        db.execute(
            """
            INSERT INTO group_banner_config (id, banner_file_id, banner_type, description, verified, updated_at)
            VALUES (1, ?, ?, ?, 1, ?)
            ON CONFLICT(id) DO UPDATE SET
                banner_file_id = excluded.banner_file_id,
                banner_type = excluded.banner_type,
                description = excluded.description,
                verified = 1,
                updated_at = excluded.updated_at
            """,
            (banner_file_id.strip(), banner_type or "photo", description.strip(), now_iso()),
        )
        # Also sync to all managed groups that don't have a custom override
        db.execute(
            """
            UPDATE managed_groups
            SET banner_file_id = ?, description = ?
            """,
            (banner_file_id.strip(), description.strip()),
        )
        db.commit()
        _sync_permanent_backup()
        return get_group_banner_config()


def get_group_banner_config() -> dict[str, Any]:
    with db_lock:
        db = ensure_db()
        row = db.execute("SELECT * FROM group_banner_config WHERE id = 1").fetchone()
        if not row:
            return {
                "banner_file_id": "",
                "banner_type": "photo",
                "description": "",
                "verified": False,
                "updated_at": None,
            }
        d = dict(row)
        d["verified"] = bool(d.get("verified"))
        return d


def save_managed_group(
    chat_id: int,
    title: str,
    username: str = "",
    invite_link: str = "",
    banner_file_id: str = "",
    description: str = "",
    interval_minutes: int = 15,
    added_by: int = 0,
) -> int:
    """
    Registers a Telegram Group OR Channel for the 15-minute banner send-and-delete rotation (/ad-group).
    Strictly uses 15 minutes (never 2 minutes): posts immediately first, stays 15 minutes, then deletes & reposts.
    """
    cfg = get_group_banner_config()
    eff_banner = (banner_file_id or cfg.get("banner_file_id") or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800").strip()
    eff_desc = (
        description
        or cfg.get("description")
        or f"🔥 Welcome to {title}! Click below to access our Permanent VIP File & Link Vault."
    ).strip()
    strict_interval = 15

    with db_lock:
        db = ensure_db()
        db.execute(
            """
            INSERT INTO managed_groups (
                chat_id, title, username, invite_link, banner_file_id,
                description, interval_minutes, active, added_by, added_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username,
                invite_link = CASE WHEN excluded.invite_link != '' THEN excluded.invite_link ELSE managed_groups.invite_link END,
                banner_file_id = excluded.banner_file_id,
                description = excluded.description,
                interval_minutes = 15,
                active = 1
            """,
            (
                int(chat_id),
                title or "VIP Managed Group / Channel",
                (username or "").lstrip("@"),
                invite_link or "",
                eff_banner,
                eff_desc,
                strict_interval,
                int(added_by or (ADMIN_IDS[0] if ADMIN_IDS else 0)),
                now_iso(),
            ),
        )
        db.commit()
        row = db.execute(
            "SELECT id FROM managed_groups WHERE chat_id = ?", (int(chat_id),)
        ).fetchone()
        _sync_permanent_backup()
        return int(row["id"]) if row else 0


def get_managed_groups() -> list[sqlite3.Row]:
    with db_lock:
        db = ensure_db()
        return db.execute("SELECT * FROM managed_groups ORDER BY id DESC").fetchall()


def get_managed_group_by_id(group_db_id: int) -> sqlite3.Row | None:
    with db_lock:
        db = ensure_db()
        return db.execute(
            "SELECT * FROM managed_groups WHERE id = ?", (int(group_db_id),)
        ).fetchone()


def update_managed_group_post_state(
    group_db_id: int, last_message_id: int | None
) -> None:
    with db_lock:
        db = ensure_db()
        db.execute(
            """
            UPDATE managed_groups
            SET last_message_id = ?,
                last_sent_at = ?,
                send_count = send_count + 1
            WHERE id = ?
            """,
            (last_message_id, now_iso(), int(group_db_id)),
        )
        db.commit()
        _sync_permanent_backup()


def delete_managed_group(group_db_id: int) -> bool:
    with db_lock:
        db = ensure_db()
        cur = db.execute("DELETE FROM managed_groups WHERE id = ?", (int(group_db_id),))
        db.commit()
        _sync_permanent_backup()
        return cur.rowcount > 0


# =====================================================================
#  3C) 🦄 /BOT-build, /Pro-plan, /start FEATURES & USER BOTS (2+2 CHANNELS)
# =====================================================================
DEFAULT_BOT_BUILD_DESCRIPTION = (
    "🦄 ✨ Kya aap apna khud ka 24/7 Ultra-Fast File & Link Share Bot banana chahte hain? "
    "Yahan se aap 1 click me apna Bot create kar sakte hain! Aapke bot me 24/7 Instant <1s Start Reply, "
    "Free Plan me 2 Apne Channels (+ 2 Admin Channels) aur Pro Plan me 4 Apne Force-Join Channels (Admin Channels Removed!) + Lifetime Upload milega!"
)
DEFAULT_PRO_PLAN_SECRET_KEY = "FILE-SHARE-YU6J-IEHU-828H"
DEFAULT_PRO_BANNER_URL = (
    "https://images.unsplash.com/photo-1634128221889-82ed6efebfc3?w=900"
)
DEFAULT_START_WELCOME_TEXT = (
    "⚡ 24/7 Ultra-Fast Instant Delivery, VIP Bot Builder & Lifetime Pro Vault!"
)


def get_pro_plan_activation_link(bot_username: str | None = None) -> str:
    """Returns the ready-to-share One-Click Pro Plan Activation Telegram Deep Link."""
    uname = (
        bot_username
        or BOT_RUNTIME_STATUS.get("bot_username")
        or "FILE_SHARE_00_bot"
    ).strip().lstrip("@")
    cfg = get_bot_builder_config()
    key = (cfg.get("pro_plan_secret_key") or DEFAULT_PRO_PLAN_SECRET_KEY).strip()
    return f"https://t.me/{uname}?start={key}"


def save_bot_builder_config(
    description: str | None = None,
    allow_bot_build: bool | None = None,
    allow_user_upload: bool | None = None,
    allow_user_two_channels: bool | None = None,
    allow_pro_plan: bool | None = None,
    pro_plan_secret_key: str | None = None,
    show_start_help: bool | None = None,
    start_welcome_text: str | None = None,
    user_file_expiry_days: int | None = None,
    reset_single_use: bool = False,
) -> dict[str, Any]:
    """Saves /BOT-build-description, /Pro-plan Secret Key, and Admin controls over which features appear on /start."""
    cur_cfg = get_bot_builder_config()
    eff_desc = (description if description is not None else cur_cfg["description"]).strip() or DEFAULT_BOT_BUILD_DESCRIPTION
    eff_build = int(bool(allow_bot_build)) if allow_bot_build is not None else int(cur_cfg["allow_bot_build"])
    eff_upload = int(bool(allow_user_upload)) if allow_user_upload is not None else int(cur_cfg["allow_user_upload"])
    eff_two_ch = int(bool(allow_user_two_channels)) if allow_user_two_channels is not None else int(cur_cfg["allow_user_two_channels"])
    eff_pro = int(bool(allow_pro_plan)) if allow_pro_plan is not None else int(cur_cfg.get("allow_pro_plan", True))
    old_key = (cur_cfg.get("pro_plan_secret_key") or DEFAULT_PRO_PLAN_SECRET_KEY).strip()
    eff_key = (
        pro_plan_secret_key if pro_plan_secret_key is not None else old_key
    ).strip() or DEFAULT_PRO_PLAN_SECRET_KEY
    eff_help = int(bool(show_start_help)) if show_start_help is not None else int(cur_cfg.get("show_start_help", True))
    eff_welcome = (
        start_welcome_text if start_welcome_text is not None else cur_cfg.get("start_welcome_text", DEFAULT_START_WELCOME_TEXT)
    ).strip() or DEFAULT_START_WELCOME_TEXT
    eff_days = max(1, int(user_file_expiry_days or cur_cfg.get("user_file_expiry_days") or 7))

    key_changed = eff_key != old_key
    used_by = 0 if (reset_single_use or key_changed) else int(cur_cfg.get("pro_key_used_by") or 0)
    used_at = "" if (reset_single_use or key_changed) else str(cur_cfg.get("pro_key_used_at") or "")

    with db_lock:
        db = ensure_db()
        db.execute(
            """
            INSERT INTO bot_builder_config (
                id, description, allow_bot_build, allow_user_upload,
                allow_user_two_channels, allow_pro_plan, pro_plan_secret_key,
                pro_key_used_by, pro_key_used_at,
                show_start_help, start_welcome_text, user_file_expiry_days, updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                description = excluded.description,
                allow_bot_build = excluded.allow_bot_build,
                allow_user_upload = excluded.allow_user_upload,
                allow_user_two_channels = excluded.allow_user_two_channels,
                allow_pro_plan = excluded.allow_pro_plan,
                pro_plan_secret_key = excluded.pro_plan_secret_key,
                pro_key_used_by = excluded.pro_key_used_by,
                pro_key_used_at = excluded.pro_key_used_at,
                show_start_help = excluded.show_start_help,
                start_welcome_text = excluded.start_welcome_text,
                user_file_expiry_days = excluded.user_file_expiry_days,
                updated_at = excluded.updated_at
            """,
            (
                eff_desc,
                eff_build,
                eff_upload,
                eff_two_ch,
                eff_pro,
                eff_key,
                used_by,
                used_at,
                eff_help,
                eff_welcome,
                eff_days,
                now_iso(),
            ),
        )
        db.commit()
        _sync_permanent_backup()
        return get_bot_builder_config()


def get_bot_builder_config() -> dict[str, Any]:
    with db_lock:
        db = ensure_db()
        row = db.execute("SELECT * FROM bot_builder_config WHERE id = 1").fetchone()
        uname = (BOT_RUNTIME_STATUS.get("bot_username") or "FILE_SHARE_00_bot").strip().lstrip("@")
        if not row:
            return {
                "description": DEFAULT_BOT_BUILD_DESCRIPTION,
                "allow_bot_build": True,
                "allow_user_upload": True,
                "allow_user_two_channels": True,
                "allow_pro_plan": True,
                "pro_plan_secret_key": DEFAULT_PRO_PLAN_SECRET_KEY,
                "pro_key_used_by": 0,
                "pro_key_used_at": "",
                "pro_link_available": True,
                "pro_activation_link": f"https://t.me/{uname}?start={DEFAULT_PRO_PLAN_SECRET_KEY}",
                "pro_banner_url": DEFAULT_PRO_BANNER_URL,
                "show_start_help": True,
                "start_welcome_text": DEFAULT_START_WELCOME_TEXT,
                "user_file_expiry_days": 7,
                "updated_at": None,
            }
        d = dict(row)
        d["allow_bot_build"] = bool(d.get("allow_bot_build", 1))
        d["allow_user_upload"] = bool(d.get("allow_user_upload", 1))
        d["allow_user_two_channels"] = bool(d.get("allow_user_two_channels", 1))
        d["allow_pro_plan"] = bool(d.get("allow_pro_plan", 1))
        key_val = (d.get("pro_plan_secret_key") or DEFAULT_PRO_PLAN_SECRET_KEY).strip()
        if key_val == "VIP-PRO-2026":
            key_val = DEFAULT_PRO_PLAN_SECRET_KEY
        d["pro_plan_secret_key"] = key_val
        d["pro_key_used_by"] = int(d.get("pro_key_used_by") or 0)
        d["pro_key_used_at"] = str(d.get("pro_key_used_at") or "")
        d["pro_link_available"] = d["pro_key_used_by"] == 0
        d["pro_activation_link"] = f"https://t.me/{uname}?start={key_val}"
        d["pro_banner_url"] = DEFAULT_PRO_BANNER_URL
        d["show_start_help"] = bool(d.get("show_start_help", 1))
        d["start_welcome_text"] = (d.get("start_welcome_text") or DEFAULT_START_WELCOME_TEXT).strip()
        d["user_file_expiry_days"] = int(d.get("user_file_expiry_days") or 7)
        return d


def mask_bot_token_str(tok: str) -> str:
    t = (tok or "").strip()
    if ":" in t and len(t) > 16:
        p1, p2 = t.split(":", 1)
        return f"{p1}:{p2[:4]}…{p2[-4:]}"
    return t[:10] + "…" if len(t) > 10 else t


def save_user_bot(
    owner_user_id: int,
    owner_name: str,
    bot_token: str,
    bot_username: str = "",
    bot_name: str = "",
    channel_1_title: str = "",
    channel_1_link: str = "",
    channel_2_title: str = "",
    channel_2_link: str = "",
    channel_3_title: str = "",
    channel_3_link: str = "",
    channel_4_title: str = "",
    channel_4_link: str = "",
) -> int:
    """Registers a user's cloned bot via /BOT-build and sets it 24/7 online."""
    tok = bot_token.strip()
    bot_id_prefix = tok.split(":", 1)[0][-4:] if ":" in tok else "007"
    eff_uname = (bot_username or f"UserVault_{bot_id_prefix}_bot").strip().lstrip("@")
    eff_bname = (bot_name or f"🦄 {owner_name or 'VIP'} File Bot #{bot_id_prefix}").strip()

    with db_lock:
        db = ensure_db()
        save_user(owner_user_id, owner_name or "User", eff_uname)
        db.execute(
            "UPDATE users SET used_bot_build = 1 WHERE user_id = ?",
            (int(owner_user_id),),
        )
        existing = db.execute(
            "SELECT id FROM user_bots WHERE owner_user_id = ? ORDER BY id DESC LIMIT 1",
            (int(owner_user_id),),
        ).fetchone()
        if existing:
            bid = int(existing["id"])
            db.execute(
                """
                UPDATE user_bots
                SET owner_name = ?,
                    bot_token = ?,
                    bot_username = ?,
                    bot_name = ?,
                    channel_1_title = CASE WHEN ? != '' THEN ? ELSE channel_1_title END,
                    channel_1_link = CASE WHEN ? != '' THEN ? ELSE channel_1_link END,
                    channel_2_title = CASE WHEN ? != '' THEN ? ELSE channel_2_title END,
                    channel_2_link = CASE WHEN ? != '' THEN ? ELSE channel_2_link END,
                    channel_3_title = CASE WHEN ? != '' THEN ? ELSE channel_3_title END,
                    channel_3_link = CASE WHEN ? != '' THEN ? ELSE channel_3_link END,
                    channel_4_title = CASE WHEN ? != '' THEN ? ELSE channel_4_title END,
                    channel_4_link = CASE WHEN ? != '' THEN ? ELSE channel_4_link END,
                    status = 'online_24_7'
                WHERE id = ?
                """,
                (
                    owner_name or "User",
                    tok,
                    eff_uname,
                    eff_bname,
                    channel_1_title,
                    channel_1_title,
                    channel_1_link,
                    channel_1_link,
                    channel_2_title,
                    channel_2_title,
                    channel_2_link,
                    channel_2_link,
                    channel_3_title,
                    channel_3_title,
                    channel_3_link,
                    channel_3_link,
                    channel_4_title,
                    channel_4_title,
                    channel_4_link,
                    channel_4_link,
                    bid,
                ),
            )
            db.commit()
            _sync_permanent_backup()
            return bid

        cur = db.execute(
            """
            INSERT INTO user_bots (
                owner_user_id, owner_name, bot_token, bot_username, bot_name,
                channel_1_title, channel_1_link, channel_2_title, channel_2_link,
                channel_3_title, channel_3_link, channel_4_title, channel_4_link,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'online_24_7', ?)
            """,
            (
                int(owner_user_id),
                owner_name or "User",
                tok,
                eff_uname,
                eff_bname,
                channel_1_title,
                channel_1_link,
                channel_2_title,
                channel_2_link,
                channel_3_title,
                channel_3_link,
                channel_4_title,
                channel_4_link,
                now_iso(),
            ),
        )
        db.commit()
        _sync_permanent_backup()
        return int(cur.lastrowid)


def update_user_bot_channels(
    bot_db_id: int,
    channel_1_title: str | None = None,
    channel_1_link: str | None = None,
    channel_2_title: str | None = None,
    channel_2_link: str | None = None,
    channel_3_title: str | None = None,
    channel_3_link: str | None = None,
    channel_4_title: str | None = None,
    channel_4_link: str | None = None,
) -> dict[str, Any] | None:
    """
    Allows a user to configure Force-Join Channels on their cloned bot:
    - Free User: up to 2 channels (+ 2 Admin channels).
    - Pro Plan User: up to 4 channels (Admin's 2 channels are removed!).
    """
    with db_lock:
        db = ensure_db()
        row = db.execute("SELECT * FROM user_bots WHERE id = ?", (int(bot_db_id),)).fetchone()
        if not row:
            return None
        cur = dict(row)
        c1_t = (channel_1_title if channel_1_title is not None else cur.get("channel_1_title", "")).strip()
        c1_l = (channel_1_link if channel_1_link is not None else cur.get("channel_1_link", "")).strip()
        c2_t = (channel_2_title if channel_2_title is not None else cur.get("channel_2_title", "")).strip()
        c2_l = (channel_2_link if channel_2_link is not None else cur.get("channel_2_link", "")).strip()
        c3_t = (channel_3_title if channel_3_title is not None else cur.get("channel_3_title", "")).strip()
        c3_l = (channel_3_link if channel_3_link is not None else cur.get("channel_3_link", "")).strip()
        c4_t = (channel_4_title if channel_4_title is not None else cur.get("channel_4_title", "")).strip()
        c4_l = (channel_4_link if channel_4_link is not None else cur.get("channel_4_link", "")).strip()
        db.execute(
            """
            UPDATE user_bots
            SET channel_1_title = ?, channel_1_link = ?,
                channel_2_title = ?, channel_2_link = ?,
                channel_3_title = ?, channel_3_link = ?,
                channel_4_title = ?, channel_4_link = ?
            WHERE id = ?
            """,
            (c1_t, c1_l, c2_t, c2_l, c3_t, c3_l, c4_t, c4_l, int(bot_db_id)),
        )
        db.commit()
        _sync_permanent_backup()
        return get_user_bot_by_id(int(bot_db_id))


def get_user_bots(owner_user_id: int | None = None) -> list[dict[str, Any]]:
    with db_lock:
        db = ensure_db()
        if owner_user_id is not None:
            rows = db.execute(
                "SELECT * FROM user_bots WHERE owner_user_id = ? ORDER BY id DESC",
                (int(owner_user_id),),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM user_bots ORDER BY id DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["bot_token_masked"] = mask_bot_token_str(d.get("bot_token", ""))
        owner_pro = is_user_pro(d.get("owner_user_id", 0))
        d["owner_is_pro"] = owner_pro
        d["max_user_channels"] = 4 if owner_pro else 2
        d["admin_channels_removed"] = owner_pro
        links = [
            d.get("channel_1_link"),
            d.get("channel_2_link"),
            d.get("channel_3_link") if owner_pro else "",
            d.get("channel_4_link") if owner_pro else "",
        ]
        d["user_channels_count"] = sum(1 for x in links if x)
        out.append(d)
    return out


def get_user_bot_by_id(bot_db_id: int) -> dict[str, Any] | None:
    with db_lock:
        db = ensure_db()
        row = db.execute(
            "SELECT * FROM user_bots WHERE id = ?", (int(bot_db_id),)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["bot_token_masked"] = mask_bot_token_str(d.get("bot_token", ""))
    owner_pro = is_user_pro(d.get("owner_user_id", 0))
    d["owner_is_pro"] = owner_pro
    d["max_user_channels"] = 4 if owner_pro else 2
    d["admin_channels_removed"] = owner_pro
    return d


def delete_user_bot(bot_db_id: int) -> bool:
    with db_lock:
        db = ensure_db()
        cur = db.execute("DELETE FROM user_bots WHERE id = ?", (int(bot_db_id),))
        db.commit()
        _sync_permanent_backup()
        return cur.rowcount > 0


def get_combined_force_channels_for_user_bot(
    bot_db_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Implements the Force-Join Channel rule for User Bots:
    - Free User Bot: 2 Admin Official Force-Join Channels + up to 2 User Channels (2+2 rule).
    - Pro Plan User Bot (is_user_pro == True): Admin's 2 Channels are REMOVED!
      The Pro user gets up to 4 of their own Force-Join Channels (0 Admin + 4 User Channels)!
    """
    ub: dict[str, Any] | None = None
    if bot_db_id:
        ub = get_user_bot_by_id(bot_db_id)
    if not ub:
        all_ubs = get_user_bots()
        if all_ubs:
            ub = all_ubs[0]

    owner_is_pro = bool(ub and is_user_pro(ub.get("owner_user_id", 0)))
    combined: list[dict[str, Any]] = []

    # Only include Admin's 2 channels if the bot owner is NOT on Pro Plan!
    if not owner_is_pro:
        admin_channels = [dict(r) for r in get_channels()[:2]]
        for idx, ch in enumerate(admin_channels, 1):
            combined.append(
                {
                    "slot": f"Admin Channel #{idx}",
                    "owner": "admin",
                    "title": ch["title"],
                    "invite_link": ch["invite_link"],
                }
            )
        while len(combined) < 2:
            n = len(combined) + 1
            combined.append(
                {
                    "slot": f"Admin Channel #{n}",
                    "owner": "admin",
                    "title": f"Official Admin Vault Channel #{n}",
                    "invite_link": "https://t.me/PremiumVaultUpdates",
                }
            )

    if ub:
        max_slots = 4 if owner_is_pro else 2
        for slot_num in range(1, max_slots + 1):
            link_val = (ub.get(f"channel_{slot_num}_link") or "").strip()
            title_val = (ub.get(f"channel_{slot_num}_title") or f"User Channel #{slot_num}").strip()
            if link_val:
                combined.append(
                    {
                        "slot": f"Pro User Channel #{slot_num}" if owner_is_pro else f"User Channel #{slot_num}",
                        "owner": "user",
                        "title": title_val,
                        "invite_link": link_val,
                    }
                )
    return combined


def get_stats() -> dict[str, int]:
    cleanup_expired_user_files()
    with db_lock:
        db = ensure_db()
        return {
            "channels": int(db.execute("SELECT COUNT(*) FROM channels").fetchone()[0]),
            "files": int(db.execute("SELECT COUNT(*) FROM files").fetchone()[0]),
            "users": int(db.execute("SELECT COUNT(*) FROM users").fetchone()[0]),
            "pro_users": int(db.execute("SELECT COUNT(*) FROM users WHERE is_pro = 1").fetchone()[0]),
            "downloads": int(
                db.execute("SELECT COALESCE(SUM(downloads), 0) FROM files").fetchone()[0]
            ),
            "pending": int(db.execute("SELECT COUNT(*) FROM pending").fetchone()[0]),
            "groups": int(db.execute("SELECT COUNT(*) FROM managed_groups WHERE active = 1").fetchone()[0]),
            "links": int(db.execute("SELECT COUNT(*) FROM files WHERE file_type = 'link'").fetchone()[0]),
            "group_uploads": int(db.execute("SELECT COUNT(*) FROM files WHERE group_name != ''").fetchone()[0]),
            "user_bots": int(db.execute("SELECT COUNT(*) FROM user_bots").fetchone()[0]),
            "user_uploads": int(db.execute("SELECT COUNT(*) FROM files WHERE uploader_role IN ('user', 'pro')").fetchone()[0]),
        }


# =====================================================================
#  4) 🧰 HELPERS
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
        await update.callback_query.answer("⛔ Sirf Admin ke liye allowed hai!", show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text(
            card("⛔", "Access Denied", "◈ Ye feature sirf <b>Bot Admin</b> ke liye hai.")
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
    uname = context.application.bot_data.get("bot_username") or BOT_RUNTIME_STATUS.get("bot_username")
    if not uname:
        try:
            me = await context.bot.get_me()
            uname = me.username or "FILE_SHARE_00_bot"
            context.application.bot_data["bot_username"] = uname
            BOT_RUNTIME_STATUS["bot_username"] = uname
        except Exception:
            uname = "FILE_SHARE_00_bot"
    return uname


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
#  5) ⚡ ULTRA-FAST (<1s) FORCE-JOIN + PERMANENT FILE/LINK DELIVERY
# =====================================================================
JOINED_STATUSES = ("creator", "administrator", "member")


async def _check_single_channel(
    context: ContextTypes.DEFAULT_TYPE, ch: sqlite3.Row, user_id: int
) -> tuple[sqlite3.Row, bool]:
    chat_id = int(ch["chat_id"])
    now_ts = time.monotonic()
    cached = _MEMBERSHIP_CACHE.get((chat_id, user_id))
    if cached and (now_ts - cached[1]) < MEMBERSHIP_CACHE_TTL and cached[0]:
        return (ch, True)

    joined = True
    try:
        member = await asyncio.wait_for(
            context.bot.get_chat_member(chat_id=chat_id, user_id=user_id),
            timeout=2.5,
        )
        status = str(member.status)
        joined = status in JOINED_STATUSES or (
            status == "restricted" and bool(getattr(member, "is_member", False))
        )
        _MEMBERSHIP_CACHE[(chat_id, user_id)] = (joined, now_ts)
    except Exception as e:
        logger.warning("Fast membership check fallback chat=%s: %s", chat_id, e)
    return (ch, joined)


async def channel_status(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> list[tuple[sqlite3.Row, bool]]:
    channels = get_channels()
    if not channels:
        return []
    tasks = [_check_single_channel(context, ch, user_id) for ch in channels]
    return list(await asyncio.gather(*tasks))


def pending_channels(status: list[tuple[sqlite3.Row, bool]]) -> list[sqlite3.Row]:
    return [ch for ch, ok in status if not ok]


def force_sub_text(status: list[tuple[sqlite3.Row, bool]]) -> str:
    total = len(status)
    done = sum(1 for _, ok in status if ok)
    lines = []
    for i, (ch, ok) in enumerate(status, 1):
        mark = "🟢 ✅" if ok else "🔴 ❌"
        lines.append(f"{mark} <b>{i}. {esc(ch['title'])}</b>")
    return card(
        "🔒",
        "VIP Access Verification",
        "🎁 Aapki permanent file/link <b>100% Ready</b> hai!",
        "Bas neeche ke colorful buttons se channels join karein 👇",
        "",
        "\n".join(lines),
        "",
        f"📊 <b>Progress</b>   {progress_bar(done, total)}   <b>{done}/{total}</b>",
        "",
        "<blockquote>⚡ Join dabayein ➜ <b>Request to Join</b> bhejein (Auto-Approve ON) ➜ "
        "phir <b>🟢 Verify &amp; Unlock Now</b> dabayein!</blockquote>",
        footer=BOT_NAME,
    )


def force_sub_keyboard(
    status: list[tuple[sqlite3.Row, bool]], file_db_id: int
) -> InlineKeyboardMarkup:
    palette = [BLUE, PURPLE, ORANGE, CYAN, PINK, GOLD]
    rows = []
    for idx, ch in enumerate(pending_channels(status)):
        color = palette[idx % len(palette)]
        emoji = ["🔵", "🟣", "🟠", "🩵", "🩷", "🟡"][idx % 6]
        rows.append(
            [
                btn(
                    f"{emoji} 📢 Join • {short(ch['title'], 24)}",
                    url=ch["invite_link"],
                    style=color,
                )
            ]
        )
    rows.append(
        [btn("🟢 ✅ Verify & Unlock File Immediately", f"verify:{file_db_id}", style=GREEN)]
    )
    return kb(*rows)


def build_caption(row: sqlite3.Row | dict[str, Any]) -> str:
    r = dict(row)
    cap = (r.get("caption") or "").strip()[:750]
    cname = (r.get("custom_name") or r.get("file_name") or "").strip()
    gname = (r.get("group_name") or "").strip()
    meta_lines = []
    if gname:
        meta_lines.append(f"👥 <b>Group:</b> <code>{esc(gname)}</code>")
    if cname:
        meta_lines.append(f"🏷️ <b>Name:</b> <code>{esc(cname)}</code>")
    if cap:
        meta_lines.append(f"✦ <b>{esc(cap)}</b>")
    meta_lines.append("♾️ <i>Permanent Vault Protected (Never Auto-Deletes)</i>")
    meta_lines.append(f"<i>⚡ {esc(smallcaps('via ' + BOT_NAME))} ⚡</i>")
    return "\n".join(meta_lines)


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
                "Item Not Found",
                "◈ Ye file/link admin dwara hata di gayi hai.",
            ),
        )
        return False

    r_dict = dict(row)
    ftype = r_dict.get("file_type") or "document"

    # If this vault item is a Direct Link (URL), deliver it with colorful buttons!
    if ftype == "link" or (r_dict.get("external_url") and str(r_dict.get("external_url")).startswith(("http://", "https://", "tg://"))):
        target_url = (r_dict.get("external_url") or r_dict.get("tg_file_id") or "").strip()
        cname = r_dict.get("custom_name") or r_dict.get("file_name") or f"Link #{file_db_id}"
        text = card(
            "🌐",
            "Direct Link Unlocked!",
            f"🏷️ <b>Name:</b>  <code>{esc(cname)}</code>",
            f"🔢 <b>Code:</b>  <code>{esc(r_dict.get('random_code') or file_db_id)}</code>",
            f"💬 <b>Info:</b>  {esc(r_dict.get('caption') or 'Direct High-Speed Vault Link')}",
            "",
            f"🔗 <b>Direct URL:</b>\n<code>{esc(target_url)}</code>",
            "",
            "♾️ <i>Permanent Link — Saved in Vault</i>",
            footer=BOT_NAME,
        )
        markup = kb(
            [btn("🟢 🌐 Open Direct Link Now", url=target_url, style=GREEN)],
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            disable_web_page_preview=False,
        )
        add_download(file_db_id)
        delete_pending(chat_id)
        return True

    method, arg = SEND_METHODS.get(ftype, SEND_METHODS["document"])
    try:
        await getattr(context.bot, method)(
            chat_id=chat_id,
            caption=build_caption(row),
            **{arg: r_dict["tg_file_id"]},
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
#  6) 🎯 INSTANT <1s COMMAND HANDLERS
# =====================================================================
PRO_STORE_BOT_USERNAME = "Krishna_Zx_Store_bot"
PRO_STORE_BOT_URL = "https://t.me/Krishna_Zx_Store_bot"


def generate_new_pro_plan_key() -> dict[str, Any]:
    """Generates a fresh single-use Pro Plan Secret Key in FILE-SHARE-XXXX-XXXX-XXXX format."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    p1 = "".join(secrets.choice(alphabet) for _ in range(4))
    p2 = "".join(secrets.choice(alphabet) for _ in range(4))
    p3 = "".join(secrets.choice(alphabet) for _ in range(4))
    new_key = f"FILE-SHARE-{p1}-{p2}-{p3}"
    return save_bot_builder_config(pro_plan_secret_key=new_key, reset_single_use=True)


def build_pro_plan_activated_card_and_kb(
    user_id: int,
) -> tuple[str, InlineKeyboardMarkup]:
    """Builds the Unicorn & Premium 'YOUR PRO PLAN ACTIVE!' caption and colorful keyboard."""
    ubots = get_user_bots(owner_user_id=int(user_id)) if user_id else []
    add_ch_cb = f"userbot:addch:{ubots[0]['id']}" if ubots else "botbuild:start"
    add_ch_label = (
        "🟣 ➕ Add 4 Channels to My Bot (Admin Removed!)"
        if ubots
        else "🦄 🤖 Create Bot & Add 4 Channels (/BOT-build)"
    )

    caption = card(
        "👑",
        "YOUR PRO PLAN ACTIVE!",
        "🦄✨💎 <b>YOUR PRO PLAN ACTIVE!</b> 💎✨🦄",
        "",
        "🎉 <b>Congratulations! Aapka VIP Pro Plan 100% Activate ho gaya hai!</b>",
        "",
        "🌈 <b>Unlocked Unicorn VIP Benefits:</b>",
        "• ♾️ <b>Lifetime Unlimited Upload:</b> Ab aap <code>/user-upload</code> se jitni chahein Files, Photos, Videos &amp; Links upload karein — <b>kabhi delete nahi hoga!</b>",
        "• 📢 <b>4 Personal Force-Join Channels:</b> Aapke bot se <b>Admin ke 2 Channels hata diye gaye hain!</b> Ab aap apne khud ke <b>4 Channels</b> add kar sakte hain!",
        "• 🤖 <b>1 Dedicated 24/7 Fast Bot</b> with &lt;1s Instant Start Reply!",
        "",
        "👇 <b>Neeche colorful buttons se apna Pro Plan use karein:</b>",
        footer=BOT_NAME,
    )
    markup = kb(
        [
            btn(
                "🟢 📤 /user-upload (♾️ Lifetime Unlimited)",
                "userupload:start",
                style=GREEN,
            )
        ],
        [
            btn(add_ch_label, add_ch_cb, style=PURPLE),
        ],
        [
            btn("🔵 🏠 Back to Home (/start)", "user:start", style=BLUE),
        ],
    )
    return caption, markup


async def send_pro_plan_activated_banner(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> None:
    """Sends the Default VIP Banner + 'YOUR PRO PLAN ACTIVE!' description card."""
    caption, markup = build_pro_plan_activated_card_and_kb(user_id)
    chat_id = update.effective_chat.id if update.effective_chat else user_id
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=DEFAULT_PRO_BANNER_URL,
            caption=caption,
            reply_markup=markup,
        )
    except Exception:
        await reply(update, context, caption, markup=markup)


def build_user_start_message_and_keyboard(
    user: Any,
) -> tuple[str, InlineKeyboardMarkup | None]:
    """
    Dynamically constructs the /start welcome screen and colorful buttons
    according to which features the Admin has enabled in bot_builder_config.
    Note: The secret key is NEVER shown to regular users.
    """
    uid = getattr(user, "id", 0) or 0
    fname = getattr(user, "first_name", "") or "Friend"
    ubots = get_user_bots(owner_user_id=int(uid)) if uid else []
    bcfg = get_bot_builder_config()
    has_pro = is_user_pro(uid)

    user_rows: list[list[InlineKeyboardButton]] = []
    feature_bullets: list[str] = []

    if ubots and bcfg.get("allow_user_two_channels", True):
        my_bot = ubots[0]
        ch_label = "Add 4 Channels • Pro" if has_pro else "Add 2 Channels"
        user_rows.append(
            [
                btn(
                    f"🦄 🤖 {my_bot['bot_name']} (Home • {ch_label})",
                    f"userbot:open:{my_bot['id']}",
                    style=PURPLE,
                )
            ]
        )

    if bcfg.get("allow_bot_build", True):
        ch_rule = (
            "Add 4 Own Channels (Admin Channels Removed!)"
            if has_pro
            else "Add 2 Channels (+ 2 Admin Channels)"
        )
        feature_bullets.append(
            f"• <code>/BOT-build</code> — Apna 24/7 Fast Bot banayein ({ch_rule})!"
        )
        user_rows.append(
            [btn("🦄 ✨ /BOT-build (Create Your 24/7 Bot)", "botbuild:start", style=PINK)]
        )

    if bcfg.get("allow_user_upload", True):
        if has_pro:
            feature_bullets.append(
                "• <code>/user-upload</code> — 👑 <b>Pro Plan Active:</b> Unlimited Lifetime Upload (Kabhi delete nahi hoga)!"
            )
            user_rows.append(
                [
                    btn(
                        "🟢 📤 /user-upload (♾️ Pro Lifetime Unlimited)",
                        "userupload:start",
                        style=GREEN,
                    )
                ]
            )
        else:
            days = bcfg.get("user_file_expiry_days", 7)
            feature_bullets.append(
                f"• <code>/user-upload</code> — Apni File ya Link upload karein (⚠️ {days} Days validity; Lifetime ke liye /Pro-plan lein)."
            )
            user_rows.append(
                [
                    btn(
                        f"🟢 📤 /user-upload (Upload File • {days}-Day Validity)",
                        "userupload:start",
                        style=GREEN,
                    )
                ]
            )

    if bcfg.get("allow_pro_plan", True):
        if has_pro:
            feature_bullets.append(
                "• <code>/Pro-plan</code> — 👑 <b>YOUR PRO PLAN ACTIVE!</b> (Lifetime Upload + 4 Channels Unlocked)."
            )
            user_rows.append(
                [btn("👑 💎 /Pro-plan Status (Active • 4 Channels)", "proplan:start", style=GOLD)]
            )
        else:
            feature_bullets.append(
                f"• <code>/Pro-plan</code> — 🔑 Secret Key daal kar <b>Lifetime Upload + 4 Channels</b> unlock karein (Buy Key: @{PRO_STORE_BOT_USERNAME})!"
            )
            user_rows.append(
                [
                    btn(
                        "💎 🔑 /Pro-plan (Unlock Lifetime + 4 Channels)",
                        "proplan:start",
                        style=GOLD,
                    )
                ]
            )
            user_rows.append(
                [
                    btn(
                        f"🛒 💎 Buy Pro Key (@{PRO_STORE_BOT_USERNAME})",
                        url=PRO_STORE_BOT_URL,
                        style=ORANGE,
                    )
                ]
            )

    if bcfg.get("show_start_help", True):
        user_rows.append(
            [btn("🔵 ℹ️ Help & Commands Guide", "user:help", style=BLUE)]
        )

    if not feature_bullets:
        feature_bullets.append("• ⚡ Share links par click karke instant files unlock karein!")

    plan_badge = (
        "👑 <b>Plan Status:</b> YOUR PRO PLAN ACTIVE (♾️ Lifetime Upload + 4 Own Channels)"
        if has_pro
        else f"⏳ <b>Plan Status:</b> Free Plan (7-Day Upload · 2+2 Channels · Buy Pro: @{PRO_STORE_BOT_USERNAME})"
    )
    welcome_line = bcfg.get("start_welcome_text") or DEFAULT_START_WELCOME_TEXT

    text = card(
        "🦄",
        f"Welcome to {BOT_NAME}",
        f"👤 <b>Hello {esc(fname)}!</b>",
        f"✨ <b>{esc(welcome_line)}</b>",
        plan_badge,
        "",
        "🌈 <b>Available Features on /start (Configured by Admin):</b>",
        *feature_bullets,
        footer=BOT_NAME,
    )
    return text, (kb(*user_rows) if user_rows else None)


def build_admin_start_config_card_and_kb() -> tuple[str, InlineKeyboardMarkup]:
    """Builds the Admin interactive control panel for toggling /start features and managing single-use Pro links."""
    bcfg = get_bot_builder_config()
    b_build = bcfg.get("allow_bot_build", True)
    b_upload = bcfg.get("allow_user_upload", True)
    b_pro = bcfg.get("allow_pro_plan", True)
    b_2ch = bcfg.get("allow_user_two_channels", True)
    b_help = bcfg.get("show_start_help", True)
    sec_key = bcfg.get("pro_plan_secret_key", DEFAULT_PRO_PLAN_SECRET_KEY)
    pro_link = bcfg.get("pro_activation_link") or get_pro_plan_activation_link()
    used_by = int(bcfg.get("pro_key_used_by") or 0)
    link_status = (
        "🟢 <b>READY (Single-Use Available)</b>"
        if used_by == 0
        else f"🔴 <b>USED by User ID <code>{used_by}</code></b> (Click Reset or Generate New Key)"
    )

    text = card(
        "🎛️",
        "Admin /start Features & Pro Link Control",
        "👑 <b>Yahan se control karein ki <code>/start</code> par kaun-kaun sa feature dikhega + Single-Use Pro Link:</b>",
        "",
        f"1️⃣ <b>/BOT-build on /start:</b> {'🟢 ON (Visible)' if b_build else '🔴 OFF (Hidden)'}",
        f"2️⃣ <b>/user-upload on /start:</b> {'🟢 ON (Visible)' if b_upload else '🔴 OFF (Hidden)'}",
        f"3️⃣ <b>/Pro-plan on /start:</b> {'🟢 ON (Visible)' if b_pro else '🔴 OFF (Hidden)'}",
        f"4️⃣ <b>User Channels on /start:</b> {'🟢 ON (Visible)' if b_2ch else '🔴 OFF (Hidden)'}",
        f"5️⃣ <b>Help Button on /start:</b> {'🟢 ON (Visible)' if b_help else '🔴 OFF (Hidden)'}",
        "",
        f"🔑 <b>Secret Key (Hidden from Users):</b> <code>{esc(sec_key)}</code>",
        f"🔗 <b>One-Click Pro Activation Link:</b>\n<code>{esc(pro_link)}</code>",
        f"📌 <b>Link Status:</b> {link_status}",
        f"🛒 <b>Store Bot for Users:</b> @{PRO_STORE_BOT_USERNAME}",
        footer=BOT_NAME,
    )
    markup = kb(
        [
            btn(
                f"{'🟢 ON' if b_build else '🔴 OFF'} • 🦄 /BOT-build",
                "adm:toggle:allow_bot_build",
                style=GREEN if b_build else RED,
            ),
            btn(
                f"{'🟢 ON' if b_upload else '🔴 OFF'} • 📤 /user-upload",
                "adm:toggle:allow_user_upload",
                style=GREEN if b_upload else RED,
            ),
        ],
        [
            btn(
                f"{'🟢 ON' if b_pro else '🔴 OFF'} • 💎 /Pro-plan",
                "adm:toggle:allow_pro_plan",
                style=GREEN if b_pro else RED,
            ),
            btn(
                f"{'🟢 ON' if b_2ch else '🔴 OFF'} • 📢 User Channels",
                "adm:toggle:allow_user_two_channels",
                style=GREEN if b_2ch else RED,
            ),
        ],
        [
            btn(
                f"{'🟢 ON' if b_help else '🔴 OFF'} • ℹ️ Help on /start",
                "adm:toggle:show_start_help",
                style=GREEN if b_help else RED,
            ),
            btn("💎 🔑 Custom /Pro-plan Key", "adm:prokey", style=GOLD),
        ],
        [
            btn("🎲 🔑 Generate New Pro Key & Link", "adm:genprokey", style=PURPLE),
            btn("🔄 Re-Arm Single-Use Link", "adm:resetprolink", style=ORANGE),
        ],
        [
            btn("👁️ Preview User /start Screen", "adm:previewuserstart", style=CYAN),
            btn("🔵 🛠 Back to VIP Panel", "adm:home", style=BLUE),
        ],
    )
    return text, markup


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user:
        save_user(update.effective_user)
    if update.callback_query:
        await update.callback_query.answer()
    args = getattr(context, "args", None) or []

    # Handle startgroup=adgroup when Admin adds bot to a group via deep link
    if args and args[0].lower() == "adgroup" and update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        if is_admin(update.effective_user):
            gid = save_managed_group(
                chat_id=update.effective_chat.id,
                title=update.effective_chat.title or "Managed Group",
                username=update.effective_chat.username or "",
                added_by=update.effective_user.id,
            )
            await reply(
                update,
                context,
                card(
                    "✅",
                    "Group Activated (/ad-group)",
                    f"👥 <b>Group:</b> {esc(update.effective_chat.title)}",
                    "🔄 <b>Auto-Banner Cycle:</b> Every 15 Minutes (Send ➜ Delete ➜ Resend)",
                    footer=BOT_NAME,
                ),
            )
            asyncio.create_task(send_and_rotate_group_banner(context.bot, gid))
        return ConversationHandler.END

    # 1. Check if this /start deep-link is a One-Click Pro Plan Activation Link
    #    e.g. https://t.me/FILE_SHARE_00_bot?start=FILE-SHARE-YU6J-IEHU-828H
    if args:
        raw_token = " ".join(args).strip()
        if is_pro_plan_start_token(raw_token):
            user = update.effective_user
            uid = user.id if user else 0
            ok, feedback = activate_user_pro_plan(
                user_id=uid,
                entered_key=raw_token,
                first_name=(user.first_name if user else "") or "",
                username=(user.username if user else "") or "",
            )
            if ok:
                await send_pro_plan_activated_banner(update, context, uid)
            else:
                await reply(
                    update,
                    context,
                    card(
                        "⚠️",
                        "Pro Plan Link Notice",
                        feedback,
                        "",
                        f"🛒 <b>Naya Pro Plan Secret Key ya Link kharidne ke liye visit karein:</b> @{PRO_STORE_BOT_USERNAME}",
                        footer=BOT_NAME,
                    ),
                    markup=kb(
                        [
                            btn(
                                f"🛒 💎 Buy Pro Key (@{PRO_STORE_BOT_USERNAME})",
                                url=PRO_STORE_BOT_URL,
                                style=GOLD,
                            )
                        ],
                        [btn("🔵 🏠 Back to /start", "user:start", style=BLUE)],
                    ),
                )
            return ConversationHandler.END

        # 2. Otherwise resolve file/link share token:
        # ?start=NAME?RANDOM, ?start=GroupName?Name=RANDOM, ?start=NAME__RANDOM, or ?start=file_2
        row = resolve_file_by_start_token(raw_token)
        if not row:
            await reply(
                update,
                context,
                card(
                    "❌",
                    "Link Not Found",
                    f"◈ Token <code>{esc(raw_token)}</code> ke liye koi file/link nahi mila.",
                    "◈ Kripya sahi share link open karein.",
                    footer=BOT_NAME,
                ),
            )
            return ConversationHandler.END

        file_db_id = int(row["id"])
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
            # Deliver immediately in <1s without extra waiting messages
            await send_file(context, update.effective_chat.id, file_db_id)
        return ConversationHandler.END

    if is_admin(update.effective_user):
        s = get_stats()
        bcfg = get_bot_builder_config()
        pro_link = bcfg.get("pro_activation_link") or get_pro_plan_activation_link()
        used_by = int(bcfg.get("pro_key_used_by") or 0)
        text = card(
            "⚡",
            f"VIP Control Panel • {BOT_NAME}",
            f"👑 <b>Admin:</b> {esc(update.effective_user.first_name or 'Admin')}",
            "🟢 <b>Status:</b> 24/7 Live · Instant &lt;1s Fast Engine",
            "♾️ <b>Admin &amp; /Pro-plan Storage:</b> Lifetime Permanent (Zero Auto-Delete)",
            "📢 <b>Pro Bot Channels:</b> 4 User Channels (Admin's 2 Channels Auto-Removed!)",
            f"🔑 <b>Secret Key:</b> <code>{esc(bcfg.get('pro_plan_secret_key', DEFAULT_PRO_PLAN_SECRET_KEY))}</code> ({'🟢 Ready' if used_by == 0 else f'🔴 Used by {used_by}'})",
            f"🔗 <b>Pro Link:</b> <code>{esc(pro_link)}</code>",
            "",
            f"📂 <b>Files/Images:</b> {s['files']}   |   🌐 <b>Links:</b> {s['links']}",
            f"🦄 <b>User Bots:</b> {s['user_bots']}   |   👑 <b>Pro Users:</b> {s.get('pro_users', 0)}",
            "",
            "◈ Neeche ke <b>Real Colorful Buttons</b> se <code>/start</code> features ya bot control karein 👇",
            footer=BOT_NAME,
        )
        await reply(update, context, text, markup=panel_kb())
    else:
        text, markup = build_user_start_message_and_keyboard(update.effective_user)
        await reply(update, context, text, markup=markup)
    return ConversationHandler.END


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user:
        save_user(update.effective_user)
    if update.callback_query:
        await update.callback_query.answer()
    text = card(
        "🌈",
        "VIP Commands & Unicorn Bot Builder",
        "🟢 <b>/upload</b> — (Admin) Lifetime File/Link upload (Never deletes)",
        "   ↳ <code>https://t.me/BOT?start=NAME?482915</code>",
        "🟣 <b>/group-upload</b> — (Admin) Group Image/File permanent upload",
        "   ↳ <code>https://t.me/BOT?start=GroupName?Name=482915</code>",
        "🩷 <b>/Group-image-description</b> — Group/Channel Banner + Description verify",
        "🩵 <b>/ad-group</b> — Group/Channel 15m Post ➜ Stay 15m ➜ Delete &amp; Repost",
        "",
        "🦄 <b>/BOT-build</b> — Create your own 24/7 Fast Bot (Free: 2+2 Ch · Pro: 4 Own Channels!)",
        "✨ <b>/BOT-build-description</b> — (Admin) Edit /BOT-build welcome description",
        "📤 <b>/user-upload</b> — Upload File/Link (7 Days Free / Lifetime with /Pro-plan)",
        f"💎 <b>/Pro-plan</b> — Enter Secret Key for Lifetime Upload + 4 Channels (Buy: @{PRO_STORE_BOT_USERNAME})",
        "🎛️ <b>/start_features</b> — (Admin) Customize which features appear on /start",
        "🔵 <b>/admin</b> — Colorful VIP Admin Panel kholein",
        footer=BOT_NAME,
    )
    markup = panel_kb() if is_admin(update.effective_user) else kb([btn("🔵 🏠 Back to /start", "user:start", style=BLUE)])
    await reply(update, context, text, markup=markup)
    return ConversationHandler.END


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    s = get_stats()
    bcfg = get_bot_builder_config()
    pro_link = bcfg.get("pro_activation_link") or get_pro_plan_activation_link()
    await reply(
        update,
        context,
        card(
            "🛠",
            "VIP Colorful Admin Panel",
            "⚡ <b>24/7 Instant Engine Active (&lt;1s Response)</b>",
            f"📂 Vault Items: <b>{s['files']}</b> · 👥 Active 15m Groups: <b>{s['groups']}</b>",
            f"🔑 /Pro-plan Key: <code>{esc(bcfg.get('pro_plan_secret_key', DEFAULT_PRO_PLAN_SECRET_KEY))}</code> · 👑 Pro Users: <b>{s.get('pro_users', 0)}</b>",
            f"🔗 Pro Link: <code>{esc(pro_link)}</code>",
            "◈ Neeche colorful buttons se action chunein:",
            footer=BOT_NAME,
        ),
        markup=panel_kb(),
    )
    return ConversationHandler.END


# =====================================================================
#  7) 🛠 ADMIN CALLBACK ROUTER
# =====================================================================
async def adm_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    if not q:
        return ConversationHandler.END
    if not await guard_admin(update):
        return ConversationHandler.END

    data = q.data or ""
    if data == "adm:genprokey":
        new_cfg = generate_new_pro_plan_key()
        await q.answer(f"🔑 New Key Generated: {new_cfg['pro_plan_secret_key']}", show_alert=True)
        text, markup = build_admin_start_config_card_and_kb()
        try:
            await q.edit_message_text(text, reply_markup=markup)
        except BadRequest:
            await reply(update, context, text, markup=markup)
        return ConversationHandler.END

    if data == "adm:resetprolink":
        reset_pro_plan_single_use_link()
        await q.answer("🟢 Single-Use Pro Link Re-Armed for next user!", show_alert=True)
        text, markup = build_admin_start_config_card_and_kb()
        try:
            await q.edit_message_text(text, reply_markup=markup)
        except BadRequest:
            await reply(update, context, text, markup=markup)
        return ConversationHandler.END

    await q.answer()

    if data == "adm:home":
        s = get_stats()
        bcfg = get_bot_builder_config()
        pro_link = bcfg.get("pro_activation_link") or get_pro_plan_activation_link()
        try:
            await q.edit_message_text(
                card(
                    "🛠",
                    "VIP Colorful Admin Panel",
                    "⚡ <b>24/7 Instant Engine Active (&lt;1s Response)</b>",
                    f"📂 Permanent Files/Links: <b>{s['files']}</b> | 👥 15m Groups: <b>{s['groups']}</b>",
                    f"🔑 /Pro-plan Secret Key: <code>{esc(bcfg.get('pro_plan_secret_key', DEFAULT_PRO_PLAN_SECRET_KEY))}</code>",
                    f"🔗 Pro Link: <code>{esc(pro_link)}</code>",
                    footer=BOT_NAME,
                ),
                reply_markup=panel_kb(),
            )
        except BadRequest:
            pass

    elif data == "adm:startcfg":
        text, markup = build_admin_start_config_card_and_kb()
        try:
            await q.edit_message_text(text, reply_markup=markup)
        except BadRequest:
            await reply(update, context, text, markup=markup)

    elif data.startswith("adm:toggle:"):
        field_name = data.split("adm:toggle:", 1)[1]
        cur = get_bot_builder_config()
        if field_name in (
            "allow_bot_build",
            "allow_user_upload",
            "allow_pro_plan",
            "allow_user_two_channels",
            "show_start_help",
        ):
            new_val = not bool(cur.get(field_name, True))
            save_bot_builder_config(**{field_name: new_val})
        text, markup = build_admin_start_config_card_and_kb()
        try:
            await q.edit_message_text(text, reply_markup=markup)
        except BadRequest:
            pass

    elif data == "adm:previewuserstart":
        text, user_kb = build_user_start_message_and_keyboard(update.effective_user)
        rows = list(user_kb.inline_keyboard) if user_kb and getattr(user_kb, "inline_keyboard", None) else []
        rows.append([btn("🎛️ ⚙️ Edit /start Features", "adm:startcfg", style=CYAN), btn("🔵 🛠 Admin Panel", "adm:home", style=BLUE)])
        try:
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
        except BadRequest:
            await reply(update, context, text, markup=InlineKeyboardMarkup(rows))

    elif data == "adm:stats":
        s = get_stats()
        cfg = get_group_banner_config()
        bcfg = get_bot_builder_config()
        text = card(
            "📊",
            "24/7 Live Bot Statistics",
            f"📢 <b>Force-Join Channels:</b>  {s['channels']}",
            f"📂 <b>Total Vault Items:</b>  {s['files']}",
            f"🌐 <b>Direct Links Saved:</b>  {s['links']}",
            f"📸 <b>Group Uploads (/group-upload):</b>  {s['group_uploads']}",
            f"👥 <b>15m Auto-Banner Groups (/ad-group):</b>  {s['groups']}",
            f"🖼️ <b>Group Banner Verified:</b>  {'✅ Yes' if cfg['verified'] else '❌ Not Set'}",
            f"🦄 <b>User Cloned Bots (/BOT-build):</b>  {s['user_bots']}",
            f"👑 <b>/Pro-plan Lifetime Users:</b>  {s.get('pro_users', 0)} (Key: <code>{esc(bcfg.get('pro_plan_secret_key', DEFAULT_PRO_PLAN_SECRET_KEY))}</code>)",
            f"👤 <b>Registered Users:</b>  {s['users']}",
            f"⬇️ <b>Total Deliveries:</b>  {s['downloads']}",
            footer=BOT_NAME,
        )
        try:
            await q.edit_message_text(
                text,
                reply_markup=kb(
                    [
                        btn("🟢 🔄 Refresh Stats", "adm:stats", style=GREEN),
                        btn("🎛️ /start Features", "adm:startcfg", style=CYAN),
                    ],
                    [
                        btn("🔵 🛠 Admin Panel", "adm:home", style=BLUE),
                    ],
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
                card("📢", "Force-Join Channels", "◈ Abhi koi force-join channel add nahi hua."),
                reply_markup=kb(
                    [btn("🟢 ➕ Add Force-Join Channel", "adm:addch", style=GREEN)],
                    [btn("🔵 🛠 Back to Panel", "adm:home", style=BLUE)],
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
        f"<b>Total Active:</b> {len(channels)}",
        "",
        "\n".join(lines),
        footer=BOT_NAME,
    )
    del_btns = [
        btn(f"🔴 🗑 #{ch['id']}", f"delch:{ch['id']}", style=RED) for ch in channels
    ]
    rows = [del_btns[i : i + 4] for i in range(0, len(del_btns), 4)]
    rows.append(
        [
            btn("🟢 ➕ Add Channel", "adm:addch", style=GREEN),
            btn("🔵 🛠 Back", "adm:home", style=BLUE),
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
                card("📂", "Permanent Vault", "◈ Abhi tak koi file ya link upload nahi hua."),
                reply_markup=kb(
                    [
                        btn("🟢 📤 Upload File/Link", "adm:upload", style=GREEN),
                        btn("🟣 📸 /group-upload", "adm:grupload", style=PURPLE),
                    ],
                    [btn("🔵 🛠 Back", "adm:home", style=BLUE)],
                ),
            )
        except BadRequest:
            pass
        return

    username = await get_bot_username(context)
    lines = []
    for f in files:
        f_dict = dict(f)
        icon = FILE_ICONS.get(f_dict["file_type"], "📄")
        cname = short(f_dict.get("custom_name") or f_dict.get("file_name") or f"file #{f_dict['id']}", 24)
        gname = f_dict.get("group_name") or ""
        link = file_link(username, f_dict)
        prefix = f"[{esc(gname)}] " if gname else ""
        lines.append(
            f"{icon} <b>#{f_dict['id']}</b> {prefix}<b>{esc(cname)}</b> (⬇️ {f_dict['downloads']}) ♾️\n"
            f"   <code>{esc(link)}</code>"
        )

    text = card(
        "📂",
        "Permanent Vault Files & Links",
        f"<b>Recent {len(files)} Permanent Items (Never Auto-Deleted)</b>",
        "",
        "\n".join(lines),
        footer=BOT_NAME,
    )
    view_btns = [
        btn(f"🔵 🔗 #{f['id']}", f"viewfile:{f['id']}", style=BLUE) for f in files
    ]
    del_btns = [
        btn(f"🔴 🗑 #{f['id']}", f"delfile:{f['id']}", style=RED) for f in files
    ]
    rows = []
    for i in range(0, len(view_btns), 4):
        rows.append(view_btns[i : i + 4])
    for i in range(0, len(del_btns), 4):
        rows.append(del_btns[i : i + 4])
    rows.append(
        [
            btn("🟢 📤 Upload File/Link", "adm:upload", style=GREEN),
            btn("🟣 📸 /group-upload", "adm:grupload", style=PURPLE),
        ]
    )
    rows.append([btn("🔵 🛠 Back to Panel", "adm:home", style=BLUE)])
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
    r_dict = dict(row)
    username = await get_bot_username(context)
    link = file_link(username, r_dict)
    safe_link = file_tg_safe_link(username, r_dict)
    icon = FILE_ICONS.get(r_dict["file_type"], "📄")
    text = card(
        icon,
        f"Vault Item #{r_dict['id']} (Permanent)",
        f"🏷️ <b>Custom Name:</b>  <code>{esc(r_dict.get('custom_name') or r_dict.get('file_name') or '—')}</code>",
        f"👥 <b>Group Name:</b>  <code>{esc(r_dict.get('group_name') or '—')}</code>",
        f"🔢 <b>4-6 Digit Code:</b>  <code>{esc(r_dict.get('random_code') or '—')}</code>",
        f"📦 <b>Type:</b>  {esc(r_dict['file_type'])} (♾️ Permanent)",
        f"⬇️ <b>Downloads:</b>  {r_dict['downloads']}",
        "",
        "🔗 <b>Custom Share Link:</b>",
        f"<code>{esc(link)}</code>",
        "",
        "⚡ <b>Direct Clickable Telegram Link:</b>",
        f"<code>{esc(safe_link)}</code>",
        footer=BOT_NAME,
    )
    try:
        await q.edit_message_text(
            text,
            disable_web_page_preview=True,
            reply_markup=kb(
                [
                    btn("🟢 📥 Test / Send Here", f"sendfile:{r_dict['id']}", style=GREEN),
                    btn("🟣 🚀 Open Share Link", url=safe_link, style=PURPLE),
                ],
                [
                    btn("🔴 🗑 Admin Delete", f"delfile:{r_dict['id']}", style=RED),
                    btn("🔵 📂 Back to Vault", "adm:files", style=BLUE),
                ],
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
    await q.answer("⚡ Sending instantly…")
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
    await q.answer("🗑 Permanently deleted by Admin!", show_alert=True)
    await my_files_cb(update, context)


# =====================================================================
#  8) 🔐 FAST VERIFY (Force-Join Verification)
# =====================================================================
async def verify_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not (q.data or "").startswith("verify:"):
        return
    await q.answer("⚡ Verifying membership…")

    file_db_id = int(q.data.split(":")[1])
    save_user(q.from_user)
    save_pending(q.from_user.id, file_db_id)

    # Clear cached false statuses for this user before re-checking
    for k in list(_MEMBERSHIP_CACHE.keys()):
        if k[1] == q.from_user.id:
            _MEMBERSHIP_CACHE.pop(k, None)

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
                "Verified in <1s!",
                "◈ Sabhi required channels joined hain.",
                "📤 Aapki permanent file/link bheji ja rahi hai…",
                footer=BOT_NAME,
            )
        )
    except BadRequest:
        pass

    await send_file(context, q.message.chat_id, file_db_id)


# =====================================================================
#  9) ➕ ADD CHANNEL (Conversation)
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
        "Add Force-Join Channel",
        "<b>4 Aasaan Tareeke:</b>",
        "",
        "1️⃣ Neeche <b>Select Channel</b> dabayein",
        "2️⃣ <code>@username</code> ya <code>-100…</code> ID bhejein",
        "3️⃣ Channel ka koi message <b>forward</b> karein",
        "4️⃣ Bot ko channel me admin banayein (auto-detect)",
        "",
        "<blockquote>Bot ko channel me <b>Admin</b> banana zaroori hai.</blockquote>",
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
            "❌ Invite link nahi mila. Bot ko channel me <b>Admin</b> banao.",
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
                "❌ Invalid format. <code>@username</code> ya <code>-100…</code> ID bhejo."
            )
            return ADDCH_INPUT
        try:
            chat_obj = await context.bot.get_chat(ident)
        except TelegramError as e:
            await msg.reply_text(f"❌ Channel resolve nahi hua: <code>{esc(str(e))}</code>")
            return ADDCH_INPUT

    if not chat_obj:
        await msg.reply_text("❌ Select Channel, @username, ya -100… ID bhejein.")
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
#  10) 📤 UPLOAD FILE OR DIRECT LINK + ASK FOR CUSTOM NAME (Conversation)
# =====================================================================
UPLOAD_MEDIA, UPLOAD_ASK_NAME = 1, 2


def _extract_media_or_link(msg: Any) -> tuple[str | None, str | None, str, str]:
    """
    Extracts (file_type, tg_file_id, default_name, external_url) from a Telegram Message.
    Supports Documents, Videos, Photos, Audio, Voice, Animations, AND Direct URLs/Links!
    """
    if getattr(msg, "document", None):
        return ("document", msg.document.file_id, msg.document.file_name or "Document", "")
    if getattr(msg, "video", None):
        return ("video", msg.video.file_id, msg.video.file_name or "Video", "")
    if getattr(msg, "photo", None):
        return ("photo", msg.photo[-1].file_id, f"Photo_{msg.photo[-1].file_unique_id[:6]}", "")
    if getattr(msg, "audio", None):
        return ("audio", msg.audio.file_id, msg.audio.file_name or "Audio", "")
    if getattr(msg, "voice", None):
        return ("voice", msg.voice.file_id, f"Voice_{msg.voice.file_unique_id[:6]}", "")
    if getattr(msg, "animation", None):
        return ("animation", msg.animation.file_id, msg.animation.file_name or "Animation", "")

    text = (getattr(msg, "text", None) or "").strip()
    if text and re.match(r"^(https?://|tg://|t\.me/)\S+$", text, re.IGNORECASE):
        url = text if not text.lower().startswith("t.me/") else f"https://{text}"
        return ("link", url, "DirectLink", url)
    return (None, None, "", "")


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
            "Step 1/2: Upload File ya Direct Link",
            "◈ Koi bhi <b>File / Media</b> ya <b>Direct Link (URL)</b> bhejein:",
            "",
            "📄 Document · 🎬 Video · 🖼️ Photo · 🎵 Audio",
            "🌐 <b>Direct Link:</b> <code>https://...</code> ya <code>t.me/...</code>",
            "",
            "♾️ <b>Permanent Storage:</b> Jab tak Admin delete nahi karega, tab tak delete nahi hoga!",
            "📝 <i>Agle step me bot aapse iska Naam (NAME) puchhega.</i>",
            footer=BOT_NAME,
        ),
        markup=cancel_kb(),
    )
    return UPLOAD_MEDIA


async def upload_media_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return UPLOAD_MEDIA

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(
            card("❌", "Cancelled", "◈ Upload cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    ft, fid, fname, ext_url = _extract_media_or_link(msg)
    if not ft or not fid:
        await msg.reply_text(
            "❌ Kripya koi <b>File/Photo/Video</b> ya valid <b>https://... Link</b> bhejein, ya Cancel dabayein.",
            reply_markup=cancel_kb(),
        )
        return UPLOAD_MEDIA

    context.user_data["pending_upload"] = {
        "file_type": ft,
        "tg_file_id": fid,
        "file_name": fname,
        "external_url": ext_url,
        "caption": msg.caption or "",
    }

    await msg.reply_text(
        card(
            "📝",
            "Step 2/2: Enter File / Link Name",
            f"✅ <b>{FILE_ICONS.get(ft, '📄')} {esc(ft.upper())} Received!</b>",
            "",
            "👉 <b>Ab iska Naam (NAME) likh kar bhejein:</b>",
            "<i>Example:</i> <code>KishanCourse</code> ya <code>VIPMovie</code>",
            "",
            "🔗 Aapka link aisa banega:",
            "<code>https://t.me/BOT?start=NAME?482915</code> (4-6 digit random number ke saath)",
            footer=BOT_NAME,
        ),
        reply_markup=cancel_kb(),
    )
    return UPLOAD_ASK_NAME


async def upload_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        await update.effective_chat.send_message(
            "📝 Kripya text me Naam (NAME) bhejein:", reply_markup=cancel_kb()
        )
        return UPLOAD_ASK_NAME

    raw_name = msg.text.strip()
    if raw_name == CANCEL_TEXT:
        context.user_data.pop("pending_upload", None)
        await msg.reply_text(card("❌", "Cancelled", "◈ Upload cancel ho gaya."))
        return ConversationHandler.END

    data = context.user_data.pop("pending_upload", None) or {}
    ft = data.get("file_type", "document")
    fid = data.get("tg_file_id", "")
    fname = data.get("file_name") or raw_name
    ext_url = data.get("external_url", "")
    caption = data.get("caption", "")

    file_db_id = save_file(
        tg_file_id=fid,
        file_type=ft,
        file_name=fname,
        caption=caption,
        created_by=update.effective_user.id,
        custom_name=raw_name,
        group_name="",
        random_digits=6,
        external_url=ext_url,
    )
    saved_row = get_file(file_db_id)
    username = await get_bot_username(context)
    custom_link = file_link(username, saved_row)
    safe_link = file_tg_safe_link(username, saved_row)
    r_code = dict(saved_row).get("random_code", "")

    await msg.reply_text(
        card(
            "✅",
            "Permanent File / Link Saved!",
            f"🏷️ <b>Name:</b>  <code>{esc(clean_slug_part(raw_name))}</code>",
            f"🔢 <b>Random 4-6 Digit Code:</b>  <code>{esc(r_code)}</code>",
            f"{FILE_ICONS.get(ft, '📄')} <b>Type:</b>  {esc(ft)} (♾️ Permanent Vault)",
            "",
            "🔗 <b>Your Custom Share Link:</b>",
            f"<code>{esc(custom_link)}</code>",
            "",
            "⚡ <b>Direct Clickable Link:</b>",
            f"<code>{esc(safe_link)}</code>",
            footer=BOT_NAME,
        ),
        disable_web_page_preview=True,
        reply_markup=kb(
            [
                btn("🟣 🚀 Open Link", url=safe_link, style=PURPLE),
                btn("🟢 📤 Upload Another", "adm:upload", style=GREEN),
            ],
            [
                btn("🔵 📂 My Permanent Vault", "adm:files", style=BLUE),
                btn("🟠 🛠 VIP Panel", "adm:home", style=ORANGE),
            ],
        ),
    )
    return ConversationHandler.END


# =====================================================================
#  11) 📸 /group-upload (Image/File + Group Name + Name + 4-6 Digit Link)
# =====================================================================
GRPUPLOAD_MEDIA, GRPUPLOAD_GROUP_NAME, GRPUPLOAD_ITEM_NAME = 10, 11, 12


async def group_upload_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    await reply(
        update,
        context,
        card(
            "📸",
            "/group-upload • Step 1/3: Send Image / File",
            "🖼️ <b>Kripya apni Image (Photo), File, ya Link upload karein:</b>",
            "",
            "♾️ <b>Permanent Protection:</b> Ye image/file permanent save rahegi, bot kabhi delete nahi karega jab tak Admin khud delete na kare!",
            "",
            "🔗 Link Format jo banega:",
            "<code>https://t.me/BOT?start=GroupName?Name=482915</code>",
            footer=BOT_NAME,
        ),
        markup=cancel_kb(),
    )
    return GRPUPLOAD_MEDIA


async def group_upload_media_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return GRPUPLOAD_MEDIA

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ /group-upload cancel ho gaya."))
        return ConversationHandler.END

    ft, fid, fname, ext_url = _extract_media_or_link(msg)
    if not ft or not fid:
        await msg.reply_text(
            "❌ Kripya Image (Photo), File, ya valid Link bhejein:",
            reply_markup=cancel_kb(),
        )
        return GRPUPLOAD_MEDIA

    context.user_data["pending_group_upload"] = {
        "file_type": ft,
        "tg_file_id": fid,
        "file_name": fname,
        "external_url": ext_url,
        "caption": msg.caption or "",
    }

    await msg.reply_text(
        card(
            "👥",
            "/group-upload • Step 2/3: Enter Group Name",
            "✅ <b>Image / File Permanently Captured!</b>",
            "",
            "👉 <b>Ab Group ka Naam (Group Name) likh kar bhejein:</b>",
            "<i>Example:</i> <code>VIPGroup</code> ya <code>MovieClub</code>",
            footer=BOT_NAME,
        ),
        reply_markup=cancel_kb(),
    )
    return GRPUPLOAD_GROUP_NAME


async def group_upload_group_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return GRPUPLOAD_GROUP_NAME

    gname = msg.text.strip()
    if gname == CANCEL_TEXT:
        context.user_data.pop("pending_group_upload", None)
        await msg.reply_text(card("❌", "Cancelled", "◈ /group-upload cancel ho gaya."))
        return ConversationHandler.END

    if "pending_group_upload" not in context.user_data:
        return ConversationHandler.END

    context.user_data["pending_group_upload"]["group_name"] = gname

    await msg.reply_text(
        card(
            "🏷️",
            "/group-upload • Step 3/3: Enter Image/File Name",
            f"👥 <b>Group Name:</b> <code>{esc(clean_slug_part(gname, 'GROUP'))}</code>",
            "",
            "👉 <b>Ab is Image/File ka Naam (Name) likh kar bhejein:</b>",
            "<i>Example:</i> <code>BannerHD</code> ya <code>Episode1</code>",
            footer=BOT_NAME,
        ),
        reply_markup=cancel_kb(),
    )
    return GRPUPLOAD_ITEM_NAME


async def group_upload_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return GRPUPLOAD_ITEM_NAME

    iname = msg.text.strip()
    if iname == CANCEL_TEXT:
        context.user_data.pop("pending_group_upload", None)
        await msg.reply_text(card("❌", "Cancelled", "◈ /group-upload cancel ho gaya."))
        return ConversationHandler.END

    data = context.user_data.pop("pending_group_upload", None) or {}
    ft = data.get("file_type", "photo")
    fid = data.get("tg_file_id", "")
    fname = data.get("file_name") or iname
    ext_url = data.get("external_url", "")
    caption = data.get("caption", "")
    gname = data.get("group_name", "Group")

    file_db_id = save_file(
        tg_file_id=fid,
        file_type=ft,
        file_name=fname,
        caption=caption,
        created_by=update.effective_user.id,
        custom_name=iname,
        group_name=gname,
        random_digits=6,
        external_url=ext_url,
    )
    saved_row = get_file(file_db_id)
    username = await get_bot_username(context)
    custom_link = file_link(username, saved_row)
    safe_link = file_tg_safe_link(username, saved_row)
    r_code = dict(saved_row).get("random_code", "")

    await msg.reply_text(
        card(
            "✅",
            "Group Upload Permanent Link Ready!",
            f"👥 <b>Group Name:</b>  <code>{esc(clean_slug_part(gname, 'GROUP'))}</code>",
            f"🏷️ <b>Image/File Name:</b>  <code>{esc(clean_slug_part(iname, 'FILE'))}</code>",
            f"🔢 <b>4-6 Digit Number:</b>  <code>{esc(r_code)}</code>",
            "♾️ <b>Status:</b> Permanent Saved (Kabhi auto-delete nahi hoga)",
            "",
            "🔗 <b>Group Upload Link:</b>",
            f"<code>{esc(custom_link)}</code>",
            "",
            "⚡ <b>Direct Clickable Link:</b>",
            f"<code>{esc(safe_link)}</code>",
            footer=BOT_NAME,
        ),
        disable_web_page_preview=True,
        reply_markup=kb(
            [
                btn("🟣 🚀 Open Group Link", url=safe_link, style=PURPLE),
                btn("🩷 📸 Another /group-upload", "adm:grupload", style=PINK),
            ],
            [
                btn("🔵 📂 Permanent Vault", "adm:files", style=BLUE),
                btn("🟢 🛠 VIP Panel", "adm:home", style=GREEN),
            ],
        ),
    )
    return ConversationHandler.END


# =====================================================================
#  12) 🖼️ /Group-image-description & 👥 /ad-group (15-Min Auto Loop)
# =====================================================================
GRPBANNER_IMAGE, GRPBANNER_DESC = 20, 21
ADGROUP_INPUT = 30


async def group_banner_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    cfg = get_group_banner_config()
    status_line = (
        "✅ <b>Current Banner:</b> Verified &amp; Active"
        if cfg["verified"]
        else "⚠️ <b>Current Banner:</b> Not configured yet"
    )
    await reply(
        update,
        context,
        card(
            "🖼️",
            "/Group-image-description • Step 1/2",
            status_line,
            "",
            "📸 <b>Pahle Group Banner ki Image (Photo) upload karein:</b>",
            "<i>(Uske baad bot aapse Description mangega aur verify kar dega)</i>",
            footer=BOT_NAME,
        ),
        markup=cancel_kb(),
    )
    return GRPBANNER_IMAGE


async def group_banner_image_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return GRPBANNER_IMAGE

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ Banner setup cancel ho gaya."))
        return ConversationHandler.END

    banner_fid = None
    btype = "photo"
    if msg.photo:
        banner_fid = msg.photo[-1].file_id
        btype = "photo"
    elif msg.document:
        banner_fid = msg.document.file_id
        btype = "document"
    elif msg.animation:
        banner_fid = msg.animation.file_id
        btype = "animation"
    elif msg.text and msg.text.strip().startswith(("http://", "https://")):
        banner_fid = msg.text.strip()
        btype = "photo"

    if not banner_fid:
        await msg.reply_text(
            "❌ Kripya Banner ke liye ek <b>Photo / Image</b> bhejein:",
            reply_markup=cancel_kb(),
        )
        return GRPBANNER_IMAGE

    context.user_data["pending_banner"] = {
        "banner_file_id": banner_fid,
        "banner_type": btype,
    }

    await msg.reply_text(
        card(
            "📝",
            "/Group-image-description • Step 2/2",
            "✅ <b>Banner Image Uploaded!</b>",
            "",
            "👉 <b>Ab is Banner ka Description likh kar bhejein:</b>",
            "<i>(Yahi Banner + Description har 15 minute me group me jayega, fir delete hokar wapas naya jayega)</i>",
            footer=BOT_NAME,
        ),
        reply_markup=cancel_kb(),
    )
    return GRPBANNER_DESC


async def group_banner_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return GRPBANNER_DESC

    desc = msg.text.strip()
    if desc == CANCEL_TEXT:
        context.user_data.pop("pending_banner", None)
        await msg.reply_text(card("❌", "Cancelled", "◈ Banner setup cancel ho gaya."))
        return ConversationHandler.END

    bdata = context.user_data.pop("pending_banner", None) or {}
    banner_fid = bdata.get("banner_file_id", "")
    btype = bdata.get("banner_type", "photo")

    save_group_banner_config(banner_fid, desc, btype)

    await msg.reply_text(
        card(
            "✅",
            "Banner & Description Verified!",
            "🖼️ <b>Banner Image:</b> Verified &amp; Permanently Saved",
            f"📝 <b>Description:</b> {esc(short(desc, 120))}",
            "🔄 <b>Group Schedule:</b> Har 15 Minute me Send ➜ Delete ➜ Resend",
            "",
            "👉 Ab <b>/ad-group</b> dabayein kisi bhi Group me ise add karne ke liye!",
            footer=BOT_NAME,
        ),
        reply_markup=kb(
            [
                btn("🩵 👥 Add Group (/ad-group)", "adm:adgroup", style=CYAN),
                btn("🩷 🖼️ Edit Banner", "adm:grpbanner", style=PINK),
            ],
            [btn("🔵 🛠 VIP Admin Panel", "adm:home", style=BLUE)],
        ),
    )
    return ConversationHandler.END


async def ad_group_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    # If Admin typed /ad-group directly inside a Group OR Channel, register it immediately and post first!
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup", "channel"):
        gid = save_managed_group(
            chat_id=update.effective_chat.id,
            title=update.effective_chat.title or "Managed Group/Channel",
            username=update.effective_chat.username or "",
            interval_minutes=15,
            added_by=update.effective_user.id if update.effective_user else 0,
        )
        await reply(
            update,
            context,
            card(
                "✅",
                "Group / Channel Verified (15-Minute Auto Banner)!",
                f"📢 <b>Chat:</b> {esc(update.effective_chat.title)}",
                "🚀 <b>Step 1:</b> Turant pehla Banner + Description post ho raha hai!",
                "⏱️ <b>Step 2:</b> Post pura <b>15 Minute</b> tak rahega (2 minute nahi, 15 minute!)",
                "🗑️ <b>Step 3:</b> 15 Minute baad purana post delete karke naya post bhejega!",
                footer=BOT_NAME,
            ),
        )
        asyncio.create_task(send_and_rotate_group_banner(context.bot, gid))
        return ConversationHandler.END

    username = await get_bot_username(context)
    clean_un = username.lstrip("@")
    add_group_url = f"https://t.me/{clean_un}?startgroup=adgroup"
    add_channel_url = f"https://t.me/{clean_un}?startchannel=adgroup&admin=post_messages+delete_messages+edit_messages+invite_users"
    groups = get_managed_groups()
    cfg = get_group_banner_config()

    grp_lines = []
    for g in groups[:8]:
        grp_lines.append(
            f"• <b>{esc(g['title'])}</b> (<code>{g['chat_id']}</code>) — ⏱️ 15m Stay (Sent: {g['send_count']})"
        )

    # Show BOTH "Select Channel" and "Select Group" buttons!
    markup = select_chat_keyboard(for_group_only=False)
    text = card(
        "👥",
        "/ad-group • Add to Group OR Channel (15m Loop)",
        f"🖼️ <b>Banner Status:</b> {'✅ Verified' if cfg['verified'] else '⚠️ Default Ready (Use /Group-image-description)'}",
        "🚀 <b>Kaise Kaam Karega (Group &amp; Channel Dono Me):</b>",
        "   • Jaise hi jodeinge, <b>turant pehle Banner + Description post karega</b>!",
        "   • Post pura <b>15 Minute</b> tak rahega (2 minute nahi, 15 minute!).",
        "   • <b>15 Minute</b> baad us post ko delete karega aur naya post bhej dega!",
        "",
        "<b>Group ya Channel Jodne ke Tareeke:</b>",
        f"1️⃣ <a href='{esc(add_group_url)}'>➕ Click to Add to Telegram Group</a>",
        f"2️⃣ <a href='{esc(add_channel_url)}'>📢 Click to Add to Telegram Channel</a>",
        "3️⃣ Neeche <b>📢 Select Channel</b> ya <b>👥 Select Group</b> button dabayein",
        "4️⃣ Group ya Channel ka <code>@username</code> ya <code>-100…</code> ID bhejein",
        "",
        f"<b>Active 15m Groups &amp; Channels ({len(groups)}):</b>",
        "\n".join(grp_lines) if grp_lines else "<i>Abhi koi group/channel add nahi hai.</i>",
        footer=BOT_NAME,
    )
    await reply(update, context, text, markup=markup or cancel_kb())
    return ADGROUP_INPUT


async def ad_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return ADGROUP_INPUT

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(
            card("❌", "Cancelled", "◈ /ad-group cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    chat_obj = None
    if msg.chat_shared:
        try:
            chat_obj = await context.bot.get_chat(msg.chat_shared.chat_id)
        except TelegramError as e:
            await msg.reply_text(f"❌ Group/Channel access nahi mila: <code>{esc(str(e))}</code>")
            return ADGROUP_INPUT
    elif msg.forward_from_chat:
        chat_obj = msg.forward_from_chat
    elif msg.text:
        ident = parse_chat_identifier(msg.text)
        if not ident:
            await msg.reply_text(
                "❌ Kripya Group ya Channel ka <code>@username</code> ya <code>-100…</code> Chat ID bhejein."
            )
            return ADGROUP_INPUT
        try:
            chat_obj = await context.bot.get_chat(ident)
        except TelegramError as e:
            await msg.reply_text(
                f"❌ Group/Channel resolve nahi hua: <code>{esc(str(e))}</code>\nBot ko Group ya Channel me Admin banayein."
            )
            return ADGROUP_INPUT

    if not chat_obj:
        await msg.reply_text("❌ Group ya Channel select karein ya @username / -100… ID bhejein.")
        return ADGROUP_INPUT

    invite = getattr(chat_obj, "invite_link", None) or (
        f"https://t.me/{chat_obj.username}" if getattr(chat_obj, "username", None) else ""
    )
    gid = save_managed_group(
        chat_id=chat_obj.id,
        title=chat_obj.title or "VIP Group / Channel",
        username=getattr(chat_obj, "username", "") or "",
        invite_link=invite,
        interval_minutes=15,
        added_by=update.effective_user.id if update.effective_user else 0,
    )

    # Trigger first banner post IMMEDIATELY upon joining/adding!
    asyncio.create_task(send_and_rotate_group_banner(context.bot, gid))

    chat_kind = "Channel" if getattr(chat_obj, "type", "") == "channel" else "Group"
    await msg.reply_text(
        card(
            "✅",
            f"{chat_kind} Added for 15-Minute Auto Banner!",
            f"📢 <b>{chat_kind}:</b> {esc(chat_obj.title)}",
            f"🆔 <b>Chat ID:</b> <code>{chat_obj.id}</code>",
            "🚀 <b>First Post:</b> Turant bhej diya gaya hai!",
            "⏱️ <b>Stay Time:</b> Pura <b>15 Minute</b> post rahega (2 min nahi), uske baad delete hokar fir naya post jayega!",
            footer=BOT_NAME,
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    await msg.reply_text(
        card("🛠", "VIP Admin Panel", f"◈ {chat_kind} 15m auto-banner active ho chuka hai!", footer=BOT_NAME),
        reply_markup=panel_kb(),
    )
    return ConversationHandler.END


async def send_and_rotate_group_banner(bot: Any, group_db_id: int) -> bool:
    """
    Executes one rotation cycle for a managed Group OR Channel:
    1) Deletes previous banner message in the group/channel (if any, after its 15-minute stay)
    2) Immediately sends fresh Banner Image + Description to the group/channel
    3) Stores the new message_id so it stays for 15 minutes (900s) before being deleted & replaced
    """
    row = get_managed_group_by_id(group_db_id)
    if not row:
        return False
    g = dict(row)
    chat_id = int(g["chat_id"])
    old_msg_id = g.get("last_message_id")

    # 1. Delete previous scheduled banner message if present
    if old_msg_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=int(old_msg_id))
        except Exception:
            pass

    # 2. Build Banner Caption + Colorful Button
    cfg = get_group_banner_config()
    banner_fid = (g.get("banner_file_id") or cfg.get("banner_file_id") or "").strip()
    desc = (
        g.get("description")
        or cfg.get("description")
        or f"🌟 Welcome to {g['title']}! Open {BOT_NAME} for instant files & links."
    ).strip()

    bot_uname = BOT_RUNTIME_STATUS.get("bot_username") or "FILE_SHARE_00_bot"
    bot_url = f"https://t.me/{bot_uname.lstrip('@')}"
    caption_html = card(
        "🌟",
        g["title"] or BOT_NAME,
        f"<b>{esc(desc)}</b>",
        "",
        "⏱️ <i>Official Banner • Stays 15 Minutes Then Auto-Refreshes</i>",
        footer=BOT_NAME,
    )
    markup = kb([btn("🟢 🚀 Open Vault Bot Now", url=bot_url, style=GREEN)])

    new_msg_id: int | None = None
    try:
        if banner_fid:
            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=banner_fid,
                caption=caption_html,
                reply_markup=markup,
            )
        else:
            sent = await bot.send_message(
                chat_id=chat_id,
                text=caption_html,
                reply_markup=markup,
            )
        new_msg_id = getattr(sent, "message_id", None)
    except Exception as e:
        logger.warning("Group/Channel banner send fallback for chat=%s: %s", chat_id, e)
        try:
            sent = await bot.send_message(
                chat_id=chat_id,
                text=caption_html,
                reply_markup=markup,
            )
            new_msg_id = getattr(sent, "message_id", None)
        except Exception:
            return False

    update_managed_group_post_state(group_db_id, new_msg_id)
    return True


async def _group_banner_scheduler_loop(app: Application, stop_event: asyncio.Event) -> None:
    """
    Background task for all managed Groups & Channels:
    - Posts immediately when a Group/Channel is added (last_sent_at is None)
    - Keeps the post live for strictly 15 minutes (900 seconds — never 2 minutes!)
    - After 15 minutes (900s), deletes the previous post and sends a new one.
    """
    while not stop_event.is_set():
        try:
            groups = get_managed_groups()
            now_dt = datetime.now(timezone.utc)
            for row in groups:
                g = dict(row)
                if not g.get("active"):
                    continue
                # Strictly 15 minutes (900 seconds) stay duration
                interval_sec = 900
                last_sent_str = g.get("last_sent_at")
                due = False
                if not last_sent_str:
                    due = True
                else:
                    try:
                        last_dt = datetime.fromisoformat(last_sent_str)
                        if (now_dt - last_dt).total_seconds() >= interval_sec:
                            due = True
                    except ValueError:
                        due = True
                if due:
                    await send_and_rotate_group_banner(app.bot, int(g["id"]))
        except Exception as e:
            logger.debug("Group/Channel 15m scheduler tick notice: %s", e)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            pass


# =====================================================================
#  13) 📣 BROADCAST (Conversation)
# =====================================================================
BCAST_INPUT = 35


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
            "Broadcast Message",
            f"◈ <b>{total}</b> users ko instant message bhejna hai.",
            "",
            "Koi bhi message bhejo (text/photo/video/file).",
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
            await asyncio.sleep(0.2)

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
            reply_markup=kb([btn("🔵 🛠 VIP Panel", "adm:home", style=BLUE)]),
        )
    except BadRequest:
        pass
    return ConversationHandler.END


# =====================================================================
#  14) ❌ CANCEL HANDLERS
# =====================================================================
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.message:
        await update.message.reply_text(
            card("❌", "Cancelled", "◈ Operation cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


async def cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
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
#  15) 🤝 CHANNEL & GROUP EVENT HANDLERS (Admin-Only Group Guard)
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
        _MEMBERSHIP_CACHE[(int(req.chat.id), int(req.from_user.id))] = (True, time.monotonic())
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
                            "📤 Aapki file/link turant bheji ja rahi hai…",
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
    except TelegramError as e:
        logger.warning("Join approve failed: %s", e)


async def my_chat_member_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    cm = update.my_chat_member
    if not cm:
        return
    chat = cm.chat
    actor = cm.from_user
    new = cm.new_chat_member
    old = cm.old_chat_member
    was_member = str(old.status) in ("administrator", "creator", "member")
    is_member_now = str(new.status) in ("administrator", "creator", "member")
    is_admin_now = str(new.status) in ("administrator", "creator")

    # When added to EITHER a Group ('group', 'supergroup') OR a Channel ('channel'):
    if chat.type in ("group", "supergroup", "channel") and (
        (is_member_now and not was_member) or (chat.type == "channel" and is_admin_now)
    ):
        if actor and not is_admin(actor):
            try:
                if chat.type in ("group", "supergroup"):
                    await context.bot.send_message(
                        chat.id,
                        card("⛔", "Admin Only", "◈ Sirf Bot Admin hi is bot ko Group ya Channel me add kar sakte hain."),
                    )
                await context.bot.leave_chat(chat.id)
            except TelegramError:
                pass
            return

        invite = getattr(chat, "invite_link", None)
        if not invite:
            try:
                invite = await context.bot.export_chat_invite_link(chat.id)
            except TelegramError:
                invite = None
        if not invite and getattr(chat, "username", None):
            invite = f"https://t.me/{chat.username}"

        # If it's a channel and we have an invite link, also keep force-join channel list updated
        if chat.type == "channel" and invite:
            save_channel(chat.id, chat.title or "Channel", chat.username or "", invite)

        # Register in managed_groups (supports BOTH Groups & Channels!) with 15-minute stay
        chat_label = "Channel" if chat.type == "channel" else "Group"
        gid = save_managed_group(
            chat_id=chat.id,
            title=chat.title or f"Managed {chat_label}",
            username=getattr(chat, "username", "") or "",
            invite_link=invite or "",
            interval_minutes=15,
            added_by=actor.id if actor else (ADMIN_IDS[0] if ADMIN_IDS else 0),
        )
        # Immediately post the first Banner + Description right when added!
        asyncio.create_task(send_and_rotate_group_banner(context.bot, gid))

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    card(
                        "✅",
                        f"{chat_label} Auto-Registered (15m Loop)",
                        f"📢 <b>{chat_label}:</b> {esc(chat.title)}",
                        f"🆔 <code>{chat.id}</code>",
                        "🚀 <b>First Post Sent Immediately!</b>",
                        "⏱️ Post pura <b>15 Minute</b> rahega (2 min nahi), fir delete hokar naya post jayega!",
                        footer=BOT_NAME,
                    ),
                )
            except TelegramError:
                pass
        return


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
#  16) 🚨 ERROR HANDLER & ULTRA-FAST POLLING ENGINE
# =====================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = getattr(context, "error", None)
    if isinstance(err, Conflict):
        count = int(BOT_RUNTIME_STATUS.get("conflict_count", 0)) + 1
        BOT_RUNTIME_STATUS["conflict_count"] = count
        BOT_RUNTIME_STATUS["last_conflict_at"] = now_iso()
        BOT_RUNTIME_STATUS["last_error"] = (
            "Conflict: Another bot instance was polling getUpdates. Auto-cooldown active."
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
    Ultra-low-latency direct update_queue polling engine (<100ms dispatch).
    """
    offset: int | None = None
    try:
        await app.bot.delete_webhook(drop_pending_updates=False)
        BOT_RUNTIME_STATUS["webhook_cleared"] = True
    except Exception:
        pass

    logger.info("⚡ Bot 24/7 Ultra-Fast Polling Engine active (<1s response).")
    while not stop_event.is_set():
        try:
            updates = await app.bot.get_updates(
                offset=offset,
                timeout=25,
                allowed_updates=Update.ALL_TYPES,
            )
            for upd in updates:
                offset = upd.update_id + 1
                app.update_queue.put_nowait(upd)
        except Conflict:
            count = int(BOT_RUNTIME_STATUS.get("conflict_count", 0)) + 1
            BOT_RUNTIME_STATUS["conflict_count"] = count
            BOT_RUNTIME_STATUS["last_conflict_at"] = now_iso()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=12.0)
            except asyncio.TimeoutError:
                pass
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 5.0)) + 0.5)
        except (TimedOut, NetworkError):
            await asyncio.sleep(0.5)
        except TelegramError:
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2.0)


# =====================================================================
#  17) 🔒 SINGLE-INSTANCE LOCK + APPLICATION BUILDER
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


# =====================================================================
#  16B) 🦄 /BOT-build, /Pro-plan, /BOT-build-description & /user-upload
# =====================================================================
BOTBUILD_WAIT_TOKEN = 40
BOTBUILDDESC_WAIT_TEXT = 41
USERUPLOAD_MEDIA, USERUPLOAD_NAME = 50, 51
USERBOT_CH1, USERBOT_CH2, USERBOT_CH3, USERBOT_CH4 = 60, 61, 62, 63
PROPLAN_WAIT_KEY = 70
PROPLAN_ADMIN_SET_KEY = 71


async def bot_build_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user:
        save_user(update.effective_user)
    if update.callback_query:
        await update.callback_query.answer()

    bcfg = get_bot_builder_config()
    if not bcfg.get("allow_bot_build", True) and not is_admin(update.effective_user):
        await reply(
            update,
            context,
            card("⛔", "/BOT-build Paused", "◈ Admin ne abhi User Bot Builder pause kiya hua hai."),
        )
        return ConversationHandler.END

    has_pro = is_user_pro(update.effective_user)
    ch_rule_line = (
        "• 📢 <b>Add 4 Force-Join Channels (👑 Pro Active: Admin ke 2 Channels Hata Diye Gaye Hain — Sirf Aapke 4 Channels!)</b>"
        if has_pro
        else "• 📢 <b>Add Force-Join Channels</b> (Free: 2 Admin + 2 Aapke Channels · 💎 Pro: Admin ke 2 hat jayenge + 4 Aapke Channels!)"
    )

    text = card(
        "🦄",
        "/BOT-build • Unicorn VIP Bot Builder",
        "✨ <b>Kya aap apna khud ka 24/7 Fast Bot create karna chahte hain?</b> ✨",
        "",
        f"💎 <b>Description:</b>\n{esc(bcfg['description'])}",
        "",
        "🌈 <b>Aapke Bot me kya-kya milega:</b>",
        "• ⚡ <b>24/7 Online &amp; &lt;1s Instant Start Reply</b>",
        ch_rule_line,
        "• 📤 <b>/user-upload</b> (Free: 7 Days Validity · 💎 <code>/Pro-plan</code>: Lifetime Unlimited!)",
        "",
        "👇 <b>Apna Bot create karne ke liye neeche Continue par click karein:</b>",
        footer=BOT_NAME,
    )
    markup = kb(
        [btn("🟢 🦄 Continue to Build Bot 👉", "botbuild:continue", style=GREEN)],
        [btn("🔴 ❌ Cancel", "cancel", style=RED)],
    )
    await reply(update, context, text, markup=markup)
    return BOTBUILD_WAIT_TOKEN


async def bot_build_continue_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    if q:
        await q.answer("🦄 Enter your @BotFather token!")
    text = card(
        "🦄",
        "Unicorn Bot Builder • Enter Token",
        "👑 <b>Step 2/2: Verify Your Bot Token</b>",
        "",
        "👇 <b>Apna Bot Token daalein (<code>@BotFather</code> se lekar bhejein):</b>",
        "<code>7123456789:AAH_your_bot_token_here</code>",
        "",
        "✨ <i>Token daalte hi aapka bot turant verify ho jayega aur 24/7 Online ho jayega!</i>",
        footer=BOT_NAME,
    )
    if q and q.message:
        try:
            await q.message.edit_text(text, reply_markup=cancel_kb())
            return BOTBUILD_WAIT_TOKEN
        except BadRequest:
            pass
    await reply(update, context, text, markup=cancel_kb())
    return BOTBUILD_WAIT_TOKEN


async def bot_build_token_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return BOTBUILD_WAIT_TOKEN

    raw_tok = msg.text.strip()
    if raw_tok == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ /BOT-build cancel ho gaya."))
        return ConversationHandler.END

    if not validate_bot_token(raw_tok):
        await msg.reply_text(
            card(
                "❌",
                "Invalid Bot Token",
                "👇 <b>Kripya @BotFather se sahi Bot Token copy karke bhejein:</b>",
                "<code>7123456789:AAH_your_telegram_bot_token_here</code>",
                footer=BOT_NAME,
            ),
            reply_markup=cancel_kb(),
        )
        return BOTBUILD_WAIT_TOKEN

    user = update.effective_user
    uid = user.id if user else 111222333
    has_pro = is_user_pro(uid)
    owner_name = (user.first_name if user else "VIP User") or "VIP User"
    bot_id_num = raw_tok.split(":", 1)[0][-4:]
    bot_uname = f"Unicorn_{bot_id_num}_bot"
    bot_title = f"🦄 {owner_name} File Vault Bot"

    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{raw_tok}/getMe", method="GET"
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok") and data.get("result"):
                res_bot = data["result"]
                bot_uname = res_bot.get("username") or bot_uname
                bot_title = res_bot.get("first_name") or bot_title
    except Exception:
        pass

    ub_id = save_user_bot(
        owner_user_id=uid,
        owner_name=owner_name,
        bot_token=raw_tok,
        bot_username=bot_uname,
        bot_name=bot_title,
    )
    ub = get_user_bot_by_id(ub_id) or {}
    ch_btn_label = (
        "🟣 ➕ Add 4 Channels (Pro Unlocked)"
        if has_pro
        else "🟠 ➕ Add 2 Channels to My Bot"
    )
    ch_desc_line = (
        "👑 <b>PRO PLAN ACTIVE:</b> Admin ke 2 Channels hata diye gaye hain! Ab aap apne <b>4 Force-Join Channels</b> add kar sakte hain."
        if has_pro
        else "👉 Us par click karke aap apne <b>2 Force-Join Channels</b> add kar sakte hain (2 Hamare + 2 Aapke). Pro Plan lene par Admin ke 2 hat jayenge aur aap 4 jod payenge!"
    )

    await msg.reply_text(
        card(
            "🦄",
            "Bot Verified & 24/7 Online!",
            f"🤖 <b>Bot Name:</b> <code>{esc(ub.get('bot_name', bot_title))}</code>",
            f"🔗 <b>Username:</b> @{esc(ub.get('bot_username', bot_uname))}",
            "🟢 <b>Status:</b> 24/7 Online · Instant &lt;1s Start Active!",
            "",
            "🏠 <b>Home Screen par aapke Bot ka Naam aa gaya hai!</b>",
            ch_desc_line,
            "⚠️ <b>Note:</b> Free user files <b>1 Hafta (7 Days)</b> me auto-delete hoti hain, aur <code>/Pro-plan</code> walo ki <b>Lifetime</b> rehti hain!",
            footer=BOT_NAME,
        ),
        reply_markup=kb(
            [
                btn(
                    f"🟣 🤖 {ub.get('bot_name', bot_title)} (Home Screen)",
                    f"userbot:open:{ub_id}",
                    style=PURPLE,
                )
            ],
            [
                btn(ch_btn_label, f"userbot:addch:{ub_id}", style=ORANGE),
                btn("🟢 📤 /user-upload", "userupload:start", style=GREEN),
            ],
        ),
    )
    return ConversationHandler.END


async def bot_build_desc_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    bcfg = get_bot_builder_config()
    await reply(
        update,
        context,
        card(
            "✨",
            "/BOT-build-description • Edit Description",
            "📝 <b>Current /BOT-build Description:</b>",
            f"<blockquote>{esc(bcfg['description'])}</blockquote>",
            "",
            "👉 <b>Naya Description likh kar bhejein jo users ko <code>/BOT-build</code> par dikhega:</b>",
            footer=BOT_NAME,
        ),
        markup=cancel_kb(),
    )
    return BOTBUILDDESC_WAIT_TEXT


async def bot_build_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return BOTBUILDDESC_WAIT_TEXT

    new_desc = msg.text.strip()
    if new_desc == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ Operation cancel ho gaya."))
        return ConversationHandler.END

    save_bot_builder_config(description=new_desc)
    await msg.reply_text(
        card(
            "✅",
            "/BOT-build-description Updated!",
            "🦄 <b>New Description Saved:</b>",
            f"<blockquote>{esc(new_desc)}</blockquote>",
            "",
            "◈ Ab koi bhi user <code>/BOT-build</code> karega to use yahi naya description dikhega!",
            footer=BOT_NAME,
        ),
        reply_markup=panel_kb(),
    )
    return ConversationHandler.END


async def user_upload_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user:
        save_user(update.effective_user)
    if update.callback_query:
        await update.callback_query.answer()

    bcfg = get_bot_builder_config()
    if not bcfg.get("allow_user_upload", True) and not is_admin(update.effective_user):
        await reply(
            update,
            context,
            card("⛔", "/user-upload Disabled", "◈ Admin ne abhi User Upload band kiya hua hai."),
        )
        return ConversationHandler.END

    has_pro = is_user_pro(update.effective_user)
    days = bcfg.get("user_file_expiry_days", 7)

    if has_pro:
        await reply(
            update,
            context,
            card(
                "👑",
                "/user-upload • Step 1/2 (♾️ VIP Pro Lifetime Vault)",
                "💎 <b>PRO PLAN ACTIVE:</b> Aapki upload ki gayi har File, Image, Video ya Direct Link <b>LIFETIME PERMANENT</b> save rahegi (Kabhi auto-delete nahi hogi)!",
                "",
                "👉 <b>Apni File, Photo, Video, ya Direct Link (https://...) abhi bhejein:</b>",
                footer=BOT_NAME,
            ),
            markup=cancel_kb(),
        )
    else:
        await reply(
            update,
            context,
            card(
                "📤",
                "/user-upload • Step 1/2 (1-Week User Vault)",
                f"⚠️ <b>CHETAVANI (WARNING):</b> Free User dwara upload ki gayi file/link sirf <b>1 Hafta ({days} Days)</b> tak rahegi, uske baad <b>automatically delete</b> ho jayegi!",
                "💎 <i>(Unlimited Lifetime Upload ke liye <code>/Pro-plan</code> me Secret Key daalein)</i>",
                "",
                "👉 <b>Apni File, Photo, Video, ya Direct Link (https://...) abhi bhejein:</b>",
                footer=BOT_NAME,
            ),
            markup=cancel_kb(),
        )
    return USERUPLOAD_MEDIA


async def user_upload_media_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg:
        return USERUPLOAD_MEDIA

    if msg.text and msg.text.strip() == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ /user-upload cancel ho gaya."))
        return ConversationHandler.END

    ft, fid, fname, ext_url = _extract_media_or_link(msg)
    if not ft or not fid:
        await msg.reply_text(
            "❌ Kripya koi <b>File/Photo/Video</b> ya <b>https://... Link</b> bhejein:",
            reply_markup=cancel_kb(),
        )
        return USERUPLOAD_MEDIA

    context.user_data["pending_user_upload"] = {
        "file_type": ft,
        "tg_file_id": fid,
        "file_name": fname,
        "external_url": ext_url,
        "caption": msg.caption or "",
    }
    has_pro = is_user_pro(update.effective_user)
    validity_line = (
        "👑 <i>Pro Plan Active: Yeh file LIFETIME PERMANENT save rahegi!</i>"
        if has_pro
        else "⚠️ <i>Yaad rahe: Free Plan me yeh file 1 Hafta (7 Days) baad auto-delete ho jayegi.</i>"
    )
    await msg.reply_text(
        card(
            "🏷️",
            "/user-upload • Step 2/2: Enter File Name",
            "✅ <b>File / Link Received!</b>",
            validity_line,
            "",
            "👉 <b>Ab iska Naam (NAME) likh kar bhejein:</b>",
            footer=BOT_NAME,
        ),
        reply_markup=cancel_kb(),
    )
    return USERUPLOAD_NAME


async def user_upload_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return USERUPLOAD_NAME

    raw_name = msg.text.strip()
    if raw_name == CANCEL_TEXT:
        context.user_data.pop("pending_user_upload", None)
        await msg.reply_text(card("❌", "Cancelled", "◈ /user-upload cancel ho gaya."))
        return ConversationHandler.END

    uid = update.effective_user.id if update.effective_user else 0
    has_pro = is_user_pro(uid)
    data = context.user_data.pop("pending_user_upload", None) or {}
    file_db_id = save_file(
        tg_file_id=data.get("tg_file_id", ""),
        file_type=data.get("file_type", "document"),
        file_name=data.get("file_name") or raw_name,
        caption=data.get("caption", ""),
        created_by=uid,
        custom_name=raw_name,
        group_name="",
        random_digits=6,
        external_url=data.get("external_url", ""),
        uploader_role="pro" if has_pro else "user",
    )
    saved_row = dict(get_file(file_db_id))
    username = await get_bot_username(context)
    custom_link = file_link(username, saved_row)
    safe_link = file_tg_safe_link(username, saved_row)

    if has_pro or int(saved_row.get("is_permanent") or 0) == 1:
        await msg.reply_text(
            card(
                "👑",
                "VIP Pro Upload Saved (♾️ Lifetime Permanent)!",
                f"🏷️ <b>Name:</b> <code>{esc(saved_row['custom_name'])}</code>",
                f"🔢 <b>Code:</b> <code>{esc(saved_row['random_code'])}</code>",
                "♾️ <b>Storage Status:</b> LIFETIME PERMANENT (Kabhi delete nahi hoga!)",
                "📢 <b>Force-Join Rule:</b> Link kholne wale user ko Force-Join Channels join karne honge!",
                "",
                "🔗 <b>Your Lifetime Share Link:</b>",
                f"<code>{esc(custom_link)}</code>",
                footer=BOT_NAME,
            ),
            disable_web_page_preview=True,
            reply_markup=kb(
                [
                    btn("🟣 🚀 Open Link", url=safe_link, style=PURPLE),
                    btn("🟢 📤 Another /user-upload", "userupload:start", style=GREEN),
                ]
            ),
        )
    else:
        await msg.reply_text(
            card(
                "🦄",
                "User File Uploaded (Valid for 1 Week / 7 Days)!",
                f"🏷️ <b>Name:</b> <code>{esc(saved_row['custom_name'])}</code>",
                f"🔢 <b>Code:</b> <code>{esc(saved_row['random_code'])}</code>",
                "⚠️ <b>Auto-Delete Warning:</b> Yeh file thik <b>1 Hafta (7 Days)</b> me apne aap delete ho jayegi!",
                "💎 <b>Want Lifetime Storage?</b> <code>/Pro-plan</code> me Secret Key daal kar Lifetime Unlimited upload payein!",
                "",
                "🔗 <b>Your Share Link:</b>",
                f"<code>{esc(custom_link)}</code>",
                footer=BOT_NAME,
            ),
            disable_web_page_preview=True,
            reply_markup=kb(
                [
                    btn("🟣 🚀 Open Link", url=safe_link, style=PURPLE),
                    btn("🟢 📤 Another /user-upload", "userupload:start", style=GREEN),
                ],
                [
                    btn("💎 🔑 Upgrade to /Pro-plan (Lifetime)", "proplan:start", style=GOLD),
                ],
            ),
        )
    return ConversationHandler.END


async def pro_plan_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    /Pro-plan command or button:
    - If user is already Pro, sends the Default VIP Unicorn Banner + YOUR PRO PLAN ACTIVE! card.
    - Otherwise prompts the user to enter their Secret Key or buy one from @Krishna_Zx_Store_bot.
      NOTE: The Secret Key is NEVER exposed to regular users!
    """
    if update.effective_user:
        save_user(update.effective_user)
    if update.callback_query:
        await update.callback_query.answer()

    bcfg = get_bot_builder_config()
    if not bcfg.get("allow_pro_plan", True) and not is_admin(update.effective_user):
        await reply(
            update,
            context,
            card("⛔", "/Pro-plan Paused", "◈ Admin ne abhi /Pro-plan band kiya hua hai."),
        )
        return ConversationHandler.END

    uid = update.effective_user.id if update.effective_user else 0
    has_pro = is_user_pro(uid)

    if has_pro and not is_admin(uid):
        await send_pro_plan_activated_banner(update, context, uid)
        return ConversationHandler.END

    admin_hint = ""
    if is_admin(uid):
        pro_link = bcfg.get("pro_activation_link") or get_pro_plan_activation_link()
        used_by = int(bcfg.get("pro_key_used_by") or 0)
        status_txt = "🟢 Ready (Single-Use)" if used_by == 0 else f"🔴 Used by {used_by}"
        admin_hint = (
            f"\n👑 <b>Admin Only (Hidden from Users):</b>\n"
            f"• 🔑 <b>Secret Key:</b> <code>{esc(bcfg.get('pro_plan_secret_key', DEFAULT_PRO_PLAN_SECRET_KEY))}</code>\n"
            f"• 🔗 <b>One-Click Activation Link:</b>\n<code>{esc(pro_link)}</code>\n"
            f"• 📌 <b>Link Status:</b> {status_txt}"
        )

    text = card(
        "🦄",
        "/Pro-plan • Unlock VIP Lifetime + 4 Channels!",
        "✨ <b>Kya aap Lifetime Unlimited Upload + Apne Bot me 4 Force-Join Channels unlock karna chahte hain?</b>",
        "",
        "🔥 <b>/Pro-plan VIP Benefits:</b>",
        "• ♾️ <b>Lifetime Permanent Vault:</b> Aapki files kabhi delete nahi hongi (7-day auto-delete hat jayega)!",
        "• 📢 <b>4 Own Force-Join Channels:</b> Admin ke 2 Channels hat jayenge aur aap apne <b>4 Force-Join Channels</b> jod payenge!",
        "• 🚀 <b>Unlimited Uploads &amp; &lt;1s Instant Delivery</b>",
        f"• 🛒 <b>Buy Secret Key / Link:</b> @{PRO_STORE_BOT_USERNAME}",
        admin_hint,
        "",
        "🔑 <b>Activate karne ke liye neeche apna Secret Key likh kar bhejein:</b>",
        footer=BOT_NAME,
    )
    rows = [
        [btn(f"🛒 💎 Buy Pro Key (@{PRO_STORE_BOT_USERNAME})", url=PRO_STORE_BOT_URL, style=ORANGE)],
        [btn("🔴 ❌ Cancel", "cancel", style=RED)],
    ]
    if is_admin(uid):
        rows.insert(0, [btn("🎲 🔑 Generate New Key & Link (Admin)", "adm:genprokey", style=PURPLE)])
        rows.insert(0, [btn("👑 ⚙️ Custom Secret Key (Admin)", "adm:prokey", style=GOLD)])
    await reply(update, context, text, markup=kb(*rows))
    return PROPLAN_WAIT_KEY


async def pro_plan_key_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return PROPLAN_WAIT_KEY

    entered = msg.text.strip()
    if entered == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ /Pro-plan activation cancel ho gaya."))
        return ConversationHandler.END

    user = update.effective_user
    uid = user.id if user else 0
    ok, feedback = activate_user_pro_plan(
        user_id=uid,
        entered_key=entered,
        first_name=(user.first_name if user else "") or "",
        username=(user.username if user else "") or "",
    )
    if not ok:
        await msg.reply_text(
            card(
                "❌",
                "Invalid or Already Used Secret Key",
                feedback,
                "",
                f"🛒 <b>Naya Secret Key kharidne ke liye संपर्क karein:</b> @{PRO_STORE_BOT_USERNAME}",
                "🔑 <b>Dobara sahi Secret Key bhejein ya Cancel dabayein:</b>",
                footer=BOT_NAME,
            ),
            reply_markup=kb(
                [btn(f"🛒 💎 Buy Pro Key (@{PRO_STORE_BOT_USERNAME})", url=PRO_STORE_BOT_URL, style=ORANGE)],
                [btn("🔴 ❌ Cancel", "cancel", style=RED)],
            ),
        )
        return PROPLAN_WAIT_KEY

    await send_pro_plan_activated_banner(update, context, uid)
    return ConversationHandler.END


async def pro_key_admin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allows the Admin to view and update the /Pro-plan Secret Key & One-Click Link."""
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    bcfg = get_bot_builder_config()
    cur_key = bcfg.get("pro_plan_secret_key", DEFAULT_PRO_PLAN_SECRET_KEY)
    pro_link = bcfg.get("pro_activation_link") or get_pro_plan_activation_link()
    used_by = int(bcfg.get("pro_key_used_by") or 0)
    await reply(
        update,
        context,
        card(
            "🔑",
            "Admin • Set /Pro-plan Secret Key & Link",
            f"💎 <b>Current Secret Key (Hidden from Users):</b>\n<code>{esc(cur_key)}</code>",
            "",
            f"🔗 <b>One-Click Activation Link (Single-Use):</b>\n<code>{esc(pro_link)}</code>",
            f"📌 <b>Link Status:</b> {'🟢 Ready (Unused)' if used_by == 0 else f'🔴 Used by User ID {used_by}'}",
            "",
            "👉 <b>Naya Custom Secret Key likh kar bhejein (jaise <code>FILE-SHARE-YU6J-IEHU-828H</code>) ya button se Random Generate karein:</b>",
            footer=BOT_NAME,
        ),
        markup=kb(
            [btn("🎲 🔑 Auto-Generate New Key & Link", "adm:genprokey", style=PURPLE)],
            [btn("🔄 Re-Arm Current Single-Use Link", "adm:resetprolink", style=ORANGE)],
            [btn("🔴 ❌ Cancel", "cancel", style=RED)],
        ),
    )
    return PROPLAN_ADMIN_SET_KEY


async def pro_key_admin_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return PROPLAN_ADMIN_SET_KEY

    new_key = msg.text.strip()
    if new_key == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ Operation cancel ho gaya."))
        return ConversationHandler.END

    updated_cfg = save_bot_builder_config(pro_plan_secret_key=new_key, reset_single_use=True)
    pro_link = updated_cfg.get("pro_activation_link") or get_pro_plan_activation_link()
    await msg.reply_text(
        card(
            "✅",
            "/Pro-plan Secret Key & Link Updated!",
            f"🔑 <b>New Secret Key:</b> <code>{esc(new_key)}</code>",
            f"🔗 <b>New One-Click Single-Use Link:</b>\n<code>{esc(pro_link)}</code>",
            "🟢 <b>Status:</b> Ready for 1st user click!",
            "",
            "◈ Yeh link kisi bhi user ko bhejein — click karte hi uska <b>Pro Plan + 4 Channels + Lifetime Upload</b> active ho jayega!",
            footer=BOT_NAME,
        ),
        reply_markup=panel_kb(),
    )
    return ConversationHandler.END


async def start_features_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin command /start_features to configure which features appear on /start."""
    if not await guard_admin(update):
        return ConversationHandler.END
    text, markup = build_admin_start_config_card_and_kb()
    await reply(update, context, text, markup=markup)
    return ConversationHandler.END


async def user_nav_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user:start and user:help navigation buttons."""
    q = update.callback_query
    if not q:
        return ConversationHandler.END
    await q.answer()
    data = q.data or ""
    if data == "user:help":
        return await help_cmd(update, context)
    return await start_cmd(update, context)


async def userbot_addch_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Starts interactive Force-Join Channel configuration for a user's cloned bot:
    - Free user: up to 2 channels (Step 1/2 -> Step 2/2) + 2 Admin channels.
    - Pro user: up to 4 channels (Step 1/4 -> Step 4/4) with Admin's 2 channels REMOVED!
    """
    q = update.callback_query
    if q:
        await q.answer()
    parts = ((q.data if q else "") or "").split(":")
    bot_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    ub = get_user_bot_by_id(bot_id)
    if not ub:
        uid = update.effective_user.id if update.effective_user else 0
        ubs = get_user_bots(owner_user_id=uid) or get_user_bots()
        ub = ubs[0] if ubs else None
    if not ub:
        await reply(
            update,
            context,
            card("❌", "No User Bot Found", "◈ Pahle /BOT-build se apna bot banayein."),
        )
        return ConversationHandler.END

    uid = update.effective_user.id if update.effective_user else int(ub.get("owner_user_id") or 0)
    has_pro = is_user_pro(uid) or bool(ub.get("owner_is_pro"))
    max_ch = 4 if has_pro else 2

    context.user_data["editing_userbot_id"] = int(ub["id"])
    context.user_data["editing_userbot_max_ch"] = max_ch

    mode_banner = (
        "👑 <b>PRO PLAN ACTIVE:</b> Admin ke 2 Channels hata diye gaye hain! Aap apne <b>4 Force-Join Channels</b> jod sakte hain."
        if has_pro
        else "⏳ <b>Free Mode:</b> Aap 2 Channels jod sakte hain (2 Admin + 2 Aapke). <code>/Pro-plan</code> lene par Admin ke 2 hat jayenge aur aap 4 jod payenge!"
    )

    await reply(
        update,
        context,
        card(
            "📢",
            f"Add {max_ch} Channels • {ub['bot_name']} (Step 1/{max_ch})",
            mode_banner,
            "",
            "👉 <b>Apne 1st Force-Join Channel ka Invite Link (https://t.me/...) ya @username bhejein:</b>",
            f"<i>(Current Ch #1: {esc(ub.get('channel_1_link') or 'Not set')})</i>",
            footer=ub["bot_name"],
        ),
        markup=cancel_kb(),
    )
    return USERBOT_CH1


async def userbot_ch1_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return USERBOT_CH1
    raw = msg.text.strip()
    if raw == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ Channel setup cancel ho gaya."))
        return ConversationHandler.END

    max_ch = int(context.user_data.get("editing_userbot_max_ch") or 2)
    link = raw if raw.startswith("http") else f"https://t.me/{raw.lstrip('@')}"
    title = raw.lstrip("@") if not raw.startswith("http") else "User Channel #1"
    context.user_data["editing_userbot_ch1"] = (title, link)

    await msg.reply_text(
        card(
            "📢",
            f"Add {max_ch} Channels • Step 2/{max_ch}",
            f"✅ <b>Channel #1 Saved:</b> <code>{esc(link)}</code>",
            "",
            "👉 <b>Ab apne 2nd Force-Join Channel ka Invite Link (https://t.me/...) ya @username bhejein:</b>",
            "<i>(Agar aage channel nahi jodna hai to <code>skip</code> likhein)</i>",
            footer=BOT_NAME,
        ),
        reply_markup=cancel_kb(),
    )
    return USERBOT_CH2


async def userbot_ch2_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return USERBOT_CH2
    raw = msg.text.strip()
    if raw == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ Channel setup cancel ho gaya."))
        return ConversationHandler.END

    max_ch = int(context.user_data.get("editing_userbot_max_ch") or 2)
    if raw.lower() == "skip":
        ch2_title, ch2_link = "", ""
    else:
        ch2_link = raw if raw.startswith("http") else f"https://t.me/{raw.lstrip('@')}"
        ch2_title = raw.lstrip("@") if not raw.startswith("http") else "User Channel #2"

    context.user_data["editing_userbot_ch2"] = (ch2_title, ch2_link)

    if max_ch >= 4:
        await msg.reply_text(
            card(
                "👑",
                "Pro 4-Channel Setup • Step 3/4",
                f"✅ <b>Channel #2:</b> <code>{esc(ch2_link or 'Skipped')}</code>",
                "🎉 <b>Pro Plan Benefit:</b> Admin ke 2 Channels hat chuke hain — ab aap Channel #3 aur #4 bhi jod sakte hain!",
                "",
                "👉 <b>Ab apne 3rd Force-Join Channel ka Invite Link (https://t.me/...) ya @username bhejein:</b>",
                "<i>(Agar skip karna hai to <code>skip</code> likhein)</i>",
                footer=BOT_NAME,
            ),
            reply_markup=cancel_kb(),
        )
        return USERBOT_CH3

    bot_id = int(context.user_data.pop("editing_userbot_id", 0) or 0)
    ch1_title, ch1_link = context.user_data.pop("editing_userbot_ch1", ("User Channel #1", ""))
    context.user_data.pop("editing_userbot_ch2", None)
    context.user_data.pop("editing_userbot_max_ch", None)

    update_user_bot_channels(
        bot_db_id=bot_id,
        channel_1_title=ch1_title,
        channel_1_link=ch1_link,
        channel_2_title=ch2_title,
        channel_2_link=ch2_link,
    )
    ub = get_user_bot_by_id(bot_id) or {"bot_name": "My Bot", "id": bot_id}
    await msg.reply_text(
        card(
            "✅",
            "2 Force-Join Channels Updated!",
            f"🤖 <b>Bot:</b> {esc(ub.get('bot_name', 'My Bot'))}",
            f"1️⃣ <b>User Channel #1:</b> <code>{esc(ch1_link or 'None')}</code>",
            f"2️⃣ <b>User Channel #2:</b> <code>{esc(ch2_link or 'None')}</code>",
            "",
            "📢 <b>Ab aapke bot ke har share link par 2 Admin Channels + 2 Aapke Channels Force-Join me dikhenge!</b>",
            "💎 <i>Tip: <code>/Pro-plan</code> lene par Admin ke 2 Channels hat jayenge aur aap 4 apne Channels jod payenge!</i>",
            footer=BOT_NAME,
        ),
        reply_markup=kb(
            [btn("🟣 🤖 Open My Bot Home", f"userbot:open:{bot_id}", style=PURPLE)],
            [btn("🟢 📤 /user-upload", "userupload:start", style=GREEN)],
        ),
    )
    return ConversationHandler.END


async def userbot_ch3_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return USERBOT_CH3
    raw = msg.text.strip()
    if raw == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ Channel setup cancel ho gaya."))
        return ConversationHandler.END

    if raw.lower() == "skip":
        ch3_title, ch3_link = "", ""
    else:
        ch3_link = raw if raw.startswith("http") else f"https://t.me/{raw.lstrip('@')}"
        ch3_title = raw.lstrip("@") if not raw.startswith("http") else "User Channel #3"

    context.user_data["editing_userbot_ch3"] = (ch3_title, ch3_link)
    await msg.reply_text(
        card(
            "👑",
            "Pro 4-Channel Setup • Step 4/4",
            f"✅ <b>Channel #3:</b> <code>{esc(ch3_link or 'Skipped')}</code>",
            "",
            "👉 <b>Ab apne 4th Force-Join Channel ka Invite Link (https://t.me/...) ya @username bhejein:</b>",
            "<i>(Agar skip karna hai to <code>skip</code> likhein)</i>",
            footer=BOT_NAME,
        ),
        reply_markup=cancel_kb(),
    )
    return USERBOT_CH4


async def userbot_ch4_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg or not msg.text:
        return USERBOT_CH4
    raw = msg.text.strip()
    if raw == CANCEL_TEXT:
        await msg.reply_text(card("❌", "Cancelled", "◈ Channel setup cancel ho gaya."))
        return ConversationHandler.END

    bot_id = int(context.user_data.pop("editing_userbot_id", 0) or 0)
    ch1_title, ch1_link = context.user_data.pop("editing_userbot_ch1", ("User Channel #1", ""))
    ch2_title, ch2_link = context.user_data.pop("editing_userbot_ch2", ("User Channel #2", ""))
    ch3_title, ch3_link = context.user_data.pop("editing_userbot_ch3", ("User Channel #3", ""))
    context.user_data.pop("editing_userbot_max_ch", None)

    if raw.lower() == "skip":
        ch4_title, ch4_link = "", ""
    else:
        ch4_link = raw if raw.startswith("http") else f"https://t.me/{raw.lstrip('@')}"
        ch4_title = raw.lstrip("@") if not raw.startswith("http") else "User Channel #4"

    update_user_bot_channels(
        bot_db_id=bot_id,
        channel_1_title=ch1_title,
        channel_1_link=ch1_link,
        channel_2_title=ch2_title,
        channel_2_link=ch2_link,
        channel_3_title=ch3_title,
        channel_3_link=ch3_link,
        channel_4_title=ch4_title,
        channel_4_link=ch4_link,
    )
    ub = get_user_bot_by_id(bot_id) or {"bot_name": "My Bot", "id": bot_id}
    await msg.reply_text(
        card(
            "👑",
            "VIP Pro • 4 Force-Join Channels Updated!",
            f"🤖 <b>Bot:</b> {esc(ub.get('bot_name', 'My Bot'))}",
            f"1️⃣ <b>Your Channel #1:</b> <code>{esc(ch1_link or 'None')}</code>",
            f"2️⃣ <b>Your Channel #2:</b> <code>{esc(ch2_link or 'None')}</code>",
            f"3️⃣ <b>Your Channel #3:</b> <code>{esc(ch3_link or 'None')}</code>",
            f"4️⃣ <b>Your Channel #4:</b> <code>{esc(ch4_link or 'None')}</code>",
            "",
            "🎉 <b>Admin ke 2 Channels hata diye gaye hain — ab aapke bot par 100% AAPKE 4 Force-Join Channels chal rahe hain!</b>",
            footer=BOT_NAME,
        ),
        reply_markup=kb(
            [btn("🟣 🤖 Open My Bot Home", f"userbot:open:{bot_id}", style=PURPLE)],
            [btn("🟢 📤 /user-upload (♾️ Lifetime)", "userupload:start", style=GREEN)],
        ),
    )
    return ConversationHandler.END


async def userbot_router_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Opens the User's Created Bot Home Screen where Free users manage 2 channels and Pro users manage 4 channels."""
    q = update.callback_query
    if not q:
        return
    await q.answer()
    parts = (q.data or "").split(":")
    bot_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    ub = get_user_bot_by_id(bot_id)
    if not ub:
        all_ubs = get_user_bots()
        ub = all_ubs[0] if all_ubs else None
    if not ub:
        await q.message.reply_text(
            card("❌", "No User Bot Found", "◈ Pahle /BOT-build se apna bot banayein.")
        )
        return

    uid = update.effective_user.id if update.effective_user else int(ub.get("owner_user_id") or 0)
    has_pro = is_user_pro(uid) or bool(ub.get("owner_is_pro"))
    combined = get_combined_force_channels_for_user_bot(int(ub["id"]))
    ch_lines = [
        f"• <b>{esc(c['slot'])}:</b> {esc(c['title'])}" for c in combined
    ]
    ch_header = (
        "📢 <b>Force-Join Channels (👑 Pro Mode: 0 Admin + 4 Your Channels):</b>"
        if has_pro
        else "📢 <b>Force-Join Channels (2 Admin + 2 User Channels):</b>"
    )
    add_btn_label = (
        "🟣 ➕ Add 4 Channels (Pro Unlocked)"
        if has_pro
        else "🟠 ➕ Add Channel (Max 2)"
    )

    text = card(
        "🤖",
        f"My Bot Home • {ub['bot_name']}",
        f"🔗 <b>Bot Username:</b> @{esc(ub['bot_username'])}",
        "🟢 <b>Status:</b> 24/7 Online &amp; Active",
        f"👑 <b>Owner Plan:</b> {'YOUR PRO PLAN ACTIVE (Admin Channels Removed!)' if has_pro else 'Free Plan (2 Admin + 2 User Channels)'}",
        "",
        ch_header,
        "\n".join(ch_lines),
        "",
        "✨ <b>Allowed User Features:</b>",
        f"1️⃣ <b>{'Add 4 Own Channels (Admin 2 Removed!)' if has_pro else 'Add Channel (Max 2 Channels)'}</b>",
        "2️⃣ <b>/user-upload (Free: 7 Days · 💎 /Pro-plan: Lifetime)</b>",
        footer=ub["bot_name"],
    )
    rows = [
        [
            btn(add_btn_label, f"userbot:addch:{ub['id']}", style=PURPLE if has_pro else ORANGE),
            btn("🟢 📤 /user-upload", "userupload:start", style=GREEN),
        ],
        [
            btn(
                "👑 💎 /Pro-plan Active (VIP)" if has_pro else "💎 🔑 /Pro-plan (Unlock 4 Channels + Lifetime)",
                "proplan:start",
                style=GOLD,
            ),
        ],
    ]
    if not has_pro:
        rows.append([btn(f"🛒 💎 Buy Pro Key (@{PRO_STORE_BOT_USERNAME})", url=PRO_STORE_BOT_URL, style=ORANGE)])
    markup = kb(*rows)
    try:
        await q.message.edit_text(text, reply_markup=markup)
    except BadRequest:
        await q.message.reply_text(text, reply_markup=markup)


async def _configure_bot_commands(app: Application) -> None:
    commands = [
        BotCommand("start", "⚡ Instant Start (<1s)"),
        BotCommand("bot_build", "🦄 Create Your 24/7 Bot (/BOT-build)"),
        BotCommand("user_upload", "📤 User Upload (/user-upload)"),
        BotCommand("pro_plan", "💎 Unlock Unlimited Lifetime Upload (/Pro-plan)"),
        BotCommand("upload", "👑 Admin Lifetime Upload (/upload)"),
        BotCommand("group_upload", "📸 Group Image/File Upload (/group-upload)"),
        BotCommand("group_image_description", "🖼️ Group Banner (/Group-image-description)"),
        BotCommand("ad_group", "👥 Add Group/Channel 15m Loop (/ad-group)"),
        BotCommand("bot_build_description", "✨ Edit /BOT-build Description (Admin)"),
        BotCommand("start_features", "🎛️ Customize /start Features (Admin)"),
        BotCommand("addchannel", "➕ Add Force-Join Channel"),
        BotCommand("broadcast", "📣 Broadcast to All Users"),
        BotCommand("admin", "🛠 Colorful VIP Admin Panel"),
        BotCommand("help", "ℹ️ Help & Link Formats"),
        BotCommand("cancel", "❌ Cancel Operation"),
    ]
    try:
        me = await app.bot.get_me()
        app.bot_data["bot_username"] = me.username or "FILE_SHARE_00_bot"
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


def _all_conversation_entry_points() -> list[Any]:
    """
    All interactive command & callback entry points in one unified list.
    Using a single unified ConversationHandler with allow_reentry=True guarantees
    that if a user is mid-way through /user_upload and types /bot_build, /Pro-plan,
    or /start, it switches immediately without ever getting stuck!
    """
    return [
        # /start, /help, /admin, /start_features
        CommandHandler("start", start_cmd),
        MessageHandler(filters.Regex(r"(?i)^/start(\b|@|\s|$)"), start_cmd),
        CommandHandler("help", help_cmd),
        CommandHandler("admin", admin_cmd),
        CommandHandler("start_features", start_features_cmd),
        MessageHandler(filters.Regex(r"(?i)^/start[-_]?features(\b|@|$)"), start_features_cmd),
        CallbackQueryHandler(user_nav_cb, pattern=r"^user:(start|help)$"),
        # 1. Force-Join Channel
        CommandHandler("addchannel", addchannel_entry),
        CallbackQueryHandler(addchannel_entry, pattern=r"^adm:addch$"),
        # 2. Admin Lifetime Upload (/upload)
        CommandHandler("upload", upload_entry),
        CallbackQueryHandler(upload_entry, pattern=r"^adm:upload$"),
        # 3. /group-upload
        CommandHandler("group_upload", group_upload_entry),
        CommandHandler("groupupload", group_upload_entry),
        MessageHandler(filters.Regex(r"(?i)^/group[-_]?upload(\b|@|$)"), group_upload_entry),
        CallbackQueryHandler(group_upload_entry, pattern=r"^adm:grupload$"),
        # 4. /Group-image-description
        CommandHandler("group_image_description", group_banner_entry),
        CommandHandler("groupimagedescription", group_banner_entry),
        MessageHandler(
            filters.Regex(r"(?i)^/group[-_]?image[-_]?description(\b|@|$)"),
            group_banner_entry,
        ),
        CallbackQueryHandler(group_banner_entry, pattern=r"^adm:grpbanner$"),
        # 5. /ad-group
        CommandHandler("ad_group", ad_group_entry),
        CommandHandler("add_group", ad_group_entry),
        CommandHandler("adgroup", ad_group_entry),
        MessageHandler(filters.Regex(r"(?i)^/ad+[-_]?group(\b|@|$)"), ad_group_entry),
        CallbackQueryHandler(ad_group_entry, pattern=r"^adm:adgroup$"),
        # 6. /broadcast
        CommandHandler("broadcast", broadcast_entry),
        CallbackQueryHandler(broadcast_entry, pattern=r"^adm:bcast$"),
        # 7. /BOT-build (/bot_build, /bot-build, /BOT-build)
        CommandHandler("bot_build", bot_build_entry),
        CommandHandler("botbuild", bot_build_entry),
        MessageHandler(
            filters.Regex(r"(?i)^/bot[-_]?build(\b|@|\s|$)"),
            bot_build_entry,
        ),
        CallbackQueryHandler(bot_build_entry, pattern=r"^(adm:botbuild|botbuild:start)$"),
        CallbackQueryHandler(bot_build_continue_cb, pattern=r"^botbuild:continue$"),
        # 8. /BOT-build-description
        CommandHandler("bot_build_description", bot_build_desc_entry),
        CommandHandler("botbuilddescription", bot_build_desc_entry),
        MessageHandler(
            filters.Regex(r"(?i)^/bot[-_]?build[-_]?description(\b|@|\s|$)"),
            bot_build_desc_entry,
        ),
        CallbackQueryHandler(bot_build_desc_entry, pattern=r"^adm:botbuilddesc$"),
        # 9. /user-upload (/user_upload, /user-upload)
        CommandHandler("user_upload", user_upload_entry),
        CommandHandler("userupload", user_upload_entry),
        MessageHandler(
            filters.Regex(r"(?i)^/user[-_]?upload(\b|@|\s|$)"),
            user_upload_entry,
        ),
        CallbackQueryHandler(user_upload_entry, pattern=r"^userupload:start$"),
        # 10. /Pro-plan (/pro_plan, /pro-plan, /Pro-plan, /proplan)
        CommandHandler("pro_plan", pro_plan_entry),
        CommandHandler("proplan", pro_plan_entry),
        MessageHandler(
            filters.Regex(r"(?i)^/pro[-_]?plan(\b|@|\s|$)"),
            pro_plan_entry,
        ),
        CallbackQueryHandler(pro_plan_entry, pattern=r"^proplan:start$"),
        # 11. Admin set /Pro-plan Secret Key
        CommandHandler("pro_key", pro_key_admin_entry),
        MessageHandler(filters.Regex(r"(?i)^/pro[-_]?key(\b|@|\s|$)"), pro_key_admin_entry),
        CallbackQueryHandler(pro_key_admin_entry, pattern=r"^adm:prokey$"),
        # 12. User Bot Add 2 Channels interactive flow
        CallbackQueryHandler(userbot_addch_entry, pattern=r"^userbot:addch:"),
    ]


def _common_fallbacks() -> list[Any]:
    return [
        CommandHandler("cancel", cancel_cmd),
        CallbackQueryHandler(cancel_cb, pattern=r"^cancel$"),
        CommandHandler("start", start_cmd),
        CommandHandler("admin", admin_cmd),
        CommandHandler("help", help_cmd),
        CallbackQueryHandler(
            adm_router,
            pattern=r"^adm:(home|stats|channels|files|startcfg|previewuserstart|genprokey|resetprolink)$",
        ),
        CallbackQueryHandler(adm_router, pattern=r"^adm:toggle:"),
    ]


def _build_app(token: str | None = None) -> Application:
    active_token = (token or BOT_TOKEN).strip()
    defaults = Defaults(parse_mode=ParseMode.HTML)
    app = (
        Application.builder()
        .token(active_token)
        .defaults(defaults)
        .concurrent_updates(True)
        .updater(None)
        .post_init(_post_init)
        .build()
    )

    unified_conv = ConversationHandler(
        entry_points=_all_conversation_entry_points(),
        states={
            ADDCH_INPUT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, addchannel_input),
            ],
            UPLOAD_MEDIA: [
                MessageHandler(filters.ALL & ~filters.COMMAND, upload_media_received),
            ],
            UPLOAD_ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, upload_name_received),
            ],
            GRPUPLOAD_MEDIA: [
                MessageHandler(filters.ALL & ~filters.COMMAND, group_upload_media_received),
            ],
            GRPUPLOAD_GROUP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, group_upload_group_received),
            ],
            GRPUPLOAD_ITEM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, group_upload_name_received),
            ],
            GRPBANNER_IMAGE: [
                MessageHandler(filters.ALL & ~filters.COMMAND, group_banner_image_received),
            ],
            GRPBANNER_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, group_banner_desc_received),
            ],
            ADGROUP_INPUT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, ad_group_input),
            ],
            BCAST_INPUT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_received),
            ],
            BOTBUILD_WAIT_TOKEN: [
                CallbackQueryHandler(bot_build_continue_cb, pattern=r"^botbuild:continue$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot_build_token_received),
            ],
            BOTBUILDDESC_WAIT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bot_build_desc_received),
            ],
            USERUPLOAD_MEDIA: [
                MessageHandler(filters.ALL & ~filters.COMMAND, user_upload_media_received),
            ],
            USERUPLOAD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, user_upload_name_received),
            ],
            USERBOT_CH1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, userbot_ch1_received),
            ],
            USERBOT_CH2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, userbot_ch2_received),
            ],
            USERBOT_CH3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, userbot_ch3_received),
            ],
            USERBOT_CH4: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, userbot_ch4_received),
            ],
            PROPLAN_WAIT_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pro_plan_key_received),
            ],
            PROPLAN_ADMIN_SET_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, pro_key_admin_received),
            ],
        },
        fallbacks=_common_fallbacks(),
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )

    app.add_handler(unified_conv)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))

    app.add_handler(CallbackQueryHandler(verify_cb, pattern=r"^verify:"))
    app.add_handler(CallbackQueryHandler(delete_channel_cb, pattern=r"^delch:"))
    app.add_handler(CallbackQueryHandler(delete_file_cb, pattern=r"^delfile:"))
    app.add_handler(CallbackQueryHandler(view_file_cb, pattern=r"^viewfile:"))
    app.add_handler(CallbackQueryHandler(send_file_admin_cb, pattern=r"^sendfile:"))
    app.add_handler(CallbackQueryHandler(userbot_router_cb, pattern=r"^userbot:open:"))
    app.add_handler(CallbackQueryHandler(user_nav_cb, pattern=r"^user:(start|help)$"))
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
        save_user(987654321, "Rahul Kumar", "rahul_vip")
        save_channel(
            -1001987654321,
            "Premium File Vault Updates #1",
            "PremiumVaultUpdates",
            "https://t.me/PremiumVaultUpdates",
        )
        save_channel(
            -1001987654322,
            "Official Backup Channel #2",
            "PremiumVaultBackup",
            "https://t.me/PremiumVaultBackup",
        )
        save_file(
            tg_file_id="BQACAgUAAxkBAAIBZ2X_demo_masterclass_pack",
            file_type="document",
            file_name="Premium_Vault_Starter_Bundle_v2.zip",
            caption="Exclusive Premium File Vault Starter Bundle — Lifetime Admin Protected",
            created_by=admin_uid,
            custom_name="StarterBundle",
            group_name="",
            random_code="482915",
            uploader_role="admin",
        )
        save_file(
            tg_file_id="AgACAgUAAxkBAAIB_group_banner_hd",
            file_type="photo",
            file_name="VIP_Group_Poster_4K.jpg",
            caption="Permanent Group Image Upload — Never Auto-Deletes",
            created_by=admin_uid,
            custom_name="Poster4K",
            group_name="VIPGroup",
            random_code="739204",
            uploader_role="admin",
        )
        save_file(
            tg_file_id="https://t.me/PremiumVaultUpdates",
            file_type="link",
            file_name="VIP Mega Cloud Folder Link",
            caption="Direct Cloud Link unlocked via Start button",
            created_by=admin_uid,
            custom_name="MegaCloud",
            group_name="",
            random_code="5928",
            external_url="https://t.me/PremiumVaultUpdates",
            uploader_role="admin",
        )
        save_file(
            tg_file_id="BQACAgUAAxkBAAIB_user_upload_sample",
            file_type="document",
            file_name="Rahul_User_Upload_Notes.pdf",
            caption="Uploaded via /user-upload (⚠️ Auto-Deletes in 7 Days / 1 Week)",
            created_by=987654321,
            custom_name="RahulNotes",
            group_name="",
            random_code="619204",
            uploader_role="user",
        )
        save_group_banner_config(
            banner_file_id="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800",
            description="🔥 Official VIP Vault Group! Har 15 minute me latest file & direct link updates yahan milengi.",
            banner_type="photo",
        )
        save_managed_group(
            chat_id=-1001555666777,
            title="VIP File Share Discussion Group",
            username="VIPFileDiscussion",
            invite_link="https://t.me/VIPFileDiscussion",
            interval_minutes=15,
            added_by=admin_uid,
        )
        save_bot_builder_config(
            description=DEFAULT_BOT_BUILD_DESCRIPTION,
            allow_bot_build=True,
            allow_user_upload=True,
            allow_user_two_channels=True,
            allow_pro_plan=True,
            pro_plan_secret_key=DEFAULT_PRO_PLAN_SECRET_KEY,
            show_start_help=True,
            start_welcome_text=DEFAULT_START_WELCOME_TEXT,
            user_file_expiry_days=7,
        )
        save_user_bot(
            owner_user_id=987654321,
            owner_name="Rahul Kumar",
            bot_token="7123456789:AAH1234567890abcdefGHIJKLMNOPQRSTUV",
            bot_username="RahulUnicorn_bot",
            bot_name="🦄 Rahul Fast Vault Bot",
            channel_1_title="Rahul Tech Channel #1",
            channel_1_link="https://t.me/RahulTechChannel1",
            channel_2_title="Rahul Movies Channel #2",
            channel_2_link="https://t.me/RahulMoviesChannel2",
        )
    elif stats["user_bots"] == 0:
        save_user(987654321, "Rahul Kumar", "rahul_vip")
        save_bot_builder_config()
        save_user_bot(
            owner_user_id=987654321,
            owner_name="Rahul Kumar",
            bot_token="7123456789:AAH1234567890abcdefGHIJKLMNOPQRSTUV",
            bot_username="RahulUnicorn_bot",
            bot_name="🦄 Rahul Fast Vault Bot",
            channel_1_title="Rahul Tech Channel #1",
            channel_1_link="https://t.me/RahulTechChannel1",
            channel_2_title="Rahul Movies Channel #2",
            channel_2_link="https://t.me/RahulMoviesChannel2",
        )


async def _run_bot_lifecycle() -> None:
    """
    Runs the 24/7 Telegram Bot + 15-Minute Group Banner Scheduler Loop.
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

    # Start 15-minute group banner auto-post & auto-delete scheduler
    banner_scheduler_task = asyncio.create_task(_group_banner_scheduler_loop(app, stop_event))

    webhook_base = resolve_webhook_base_url()
    if webhook_base:
        webhook_url = f"{webhook_base}/telegram-webhook"
        try:
            await app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False,
            )
            BOT_RUNTIME_STATUS["mode"] = "webhook_live"
            BOT_RUNTIME_STATUS["bot_running"] = True
            BOT_RUNTIME_STATUS["webhook_url"] = webhook_url
            BOT_RUNTIME_STATUS["webhook_registrations"] = (
                int(BOT_RUNTIME_STATUS.get("webhook_registrations", 0)) + 1
            )
            BOT_RUNTIME_STATUS["last_webhook_registered_at"] = now_iso()
            logger.info(
                "⚡ Bot started in 24/7 WEBHOOK mode: %s (<1s response!)",
                webhook_url,
            )

            async def _webhook_watchdog() -> None:
                for delay in (5.0, 12.0):
                    await asyncio.sleep(delay)
                    if stop_event.is_set():
                        return
                    try:
                        await app.bot.set_webhook(
                            url=webhook_url,
                            allowed_updates=Update.ALL_TYPES,
                            drop_pending_updates=False,
                        )
                    except Exception:
                        pass
                last_full_register = time.monotonic()
                while not stop_event.is_set():
                    await asyncio.sleep(30.0)
                    if stop_event.is_set():
                        break
                    try:
                        now_m = time.monotonic()
                        # Every 5 minutes (300s), unconditionally re-register webhook URL with Telegram API
                        if (now_m - last_full_register) >= KEEP_ALIVE_INTERVAL_SECONDS:
                            last_full_register = now_m
                            await app.bot.set_webhook(
                                url=webhook_url,
                                allowed_updates=Update.ALL_TYPES,
                                drop_pending_updates=False,
                            )
                            BOT_RUNTIME_STATUS["webhook_registrations"] = (
                                int(BOT_RUNTIME_STATUS.get("webhook_registrations", 0)) + 1
                            )
                            BOT_RUNTIME_STATUS["last_webhook_registered_at"] = now_iso()
                            logger.info(
                                "💓 5-Minute Keep-Alive Heartbeat: Registered webhook %s with Telegram API",
                                webhook_url,
                            )
                        else:
                            info = await app.bot.get_webhook_info()
                            if getattr(info, "url", "") != webhook_url:
                                await app.bot.set_webhook(
                                    url=webhook_url,
                                    allowed_updates=Update.ALL_TYPES,
                                    drop_pending_updates=False,
                                )
                                BOT_RUNTIME_STATUS["webhook_registrations"] = (
                                    int(BOT_RUNTIME_STATUS.get("webhook_registrations", 0)) + 1
                                )
                                BOT_RUNTIME_STATUS["last_webhook_registered_at"] = now_iso()
                    except Exception:
                        pass

            watchdog_task = asyncio.create_task(_webhook_watchdog())
            await stop_event.wait()
            watchdog_task.cancel()
        except TelegramError as e:
            logger.warning("Webhook setup notice (%s); switching to direct fast polling.", e)
            webhook_base = ""

    if not webhook_base:
        BOT_RUNTIME_STATUS["mode"] = "polling_live"
        BOT_RUNTIME_STATUS["bot_running"] = True
        await _custom_polling_loop(app, stop_event)

    banner_scheduler_task.cancel()
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
    start_keep_alive_daemon(port=port)

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

    http_server = None
    try:
        from app import create_control_center_server

        http_server = create_control_center_server(
            port=port, acquire_lock=False, start_bot_thread=False
        )
        threading.Thread(
            target=http_server.serve_forever,
            kwargs={"poll_interval": 0.05},
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

