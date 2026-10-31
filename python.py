#!/usr/bin/env python3
# =====================================================================
#   ✦  𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗙𝗜𝗟𝗘 𝗩𝗔𝗨𝗟𝗧  —  TELEGRAM FILE SHARE BOT  ✦
# =====================================================================
#  SETUP
#   1) .env file banao (BOT_TOKEN, ADMIN_IDS, BOT_NAME, DB_PATH)
#   2) pip install -U -r requirements.txt
#   3) python python.py
# =====================================================================

# =====================================================================
#  IMPORTS
# =====================================================================
import asyncio
import html
import logging
import os
import sqlite3
import threading
import warnings
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()  # .env file load karta hai

from telegram import (
    BotCommand,
    BotCommandScopeChat,
    ChatAdministratorRights,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestChat,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
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

# =====================================================================
#  ⚙️ CONFIG (from .env / environment)
# =====================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]
BOT_NAME = os.getenv("BOT_NAME", "Premium File Vault").strip() or "Premium File Vault"
DB_PATH = os.getenv("DB_PATH", "bot_data.db").strip() or "bot_data.db"

# Validation
if not BOT_TOKEN or "PASTE" in BOT_TOKEN.upper():
    raise SystemExit("❌ BOT_TOKEN missing! .env file me BOT_TOKEN daalo.")
if not ADMIN_IDS:
    raise SystemExit("❌ ADMIN_IDS missing! .env file me apni numeric Telegram ID daalo.")

warnings.filterwarnings("ignore", message=".*per_message.*")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("premium-vault")

logger.info("🚀 Bot starting | Admin IDs: %s | DB: %s", ADMIN_IDS, DB_PATH)

# =====================================================================
#  1) ✨ THEME
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


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def short(text, limit: int = 30) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def card(icon: str, title: str, *body: str, footer: str = "") -> str:
    out = [TOP, f"{icon}  {esc(bold(title.upper()))}", TOP]
    if body:
        out += ["", *body]
    if footer:
        out += ["", f"<i>✧ {esc(smallcaps(footer))} ✧</i>"]
    return "\n".join(out)


def progress_bar(done: int, total: int, slots: int = 10) -> str:
    if total <= 0:
        return ""
    filled = round(done / total * slots)
    if done < total:
        filled = min(filled, slots - 1)
    if done > 0:
        filled = max(filled, 1)
    return "▰" * filled + "▱" * (slots - filled)


def btn(text: str, data: str = None, url: str = None, style: str = None):
    kwargs = {}
    if style:
        kwargs["api_kwargs"] = {"style": style}
    if url:
        return InlineKeyboardButton(text, url=url, **kwargs)
    return InlineKeyboardButton(text, callback_data=data, **kwargs)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([list(r) for r in rows if r])


def cancel_kb() -> InlineKeyboardMarkup:
    return kb([btn("❌ Cancel", "cancel", style=RED)])


def panel_kb() -> InlineKeyboardMarkup:
    return kb(
        [btn("➕ Add Channel", "adm:addch", style=GREEN),
         btn("📢 Channels", "adm:channels", style=BLUE)],
        [btn("📤 Upload File", "adm:upload", style=GREEN),
         btn("📂 My Files", "adm:files", style=BLUE)],
        [btn("📣 Broadcast", "adm:bcast", style=RED),
         btn("📊 Stats", "adm:stats", style=BLUE)],
    )


def home_kb() -> InlineKeyboardMarkup:
    return kb([btn("🛠 Admin Panel", "adm:home", style=BLUE)])


CANCEL_TEXT = "❌ Cancel"


def select_chat_keyboard():
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
            request_id=1, chat_is_channel=True,
            user_administrator_rights=rights, bot_administrator_rights=rights,
        )
        group_req = KeyboardButtonRequestChat(
            request_id=2, chat_is_channel=False,
            user_administrator_rights=rights, bot_administrator_rights=rights,
        )
        return ReplyKeyboardMarkup(
            [
                [KeyboardButton("📢 Select Channel", request_chat=channel_req),
                 KeyboardButton("👥 Select Group", request_chat=group_req)],
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
#  2) 🗄️ DATABASE (with auto-heal)
# =====================================================================
conn = None
db_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    """DB init karta hai. Agar purana DB corrupt hai to auto-heal karta hai."""
    global conn

    # ---- Corruption auto-heal ----
    if os.path.exists(DB_PATH):
        try:
            test = _connect_db()
            test.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
            test.close()
            conn = _connect_db()
        except sqlite3.DatabaseError as e:
            logger.error("⚠️ DB corrupt detected (%s) — recreating fresh DB", e)
            backup = DB_PATH + f".corrupt.{int(datetime.now().timestamp())}"
            try:
                os.rename(DB_PATH, backup)
                logger.info("Old corrupt DB backed up to: %s", backup)
            except OSError:
                try:
                    os.remove(DB_PATH)
                except OSError:
                    pass
            conn = _connect_db()
    else:
        conn = _connect_db()

    # ---- Schema ----
    with db_lock:
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


def save_user(user) -> None:
    with db_lock:
        conn.execute(
            """
            INSERT INTO users (user_id, first_name, username, started_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                username = excluded.username
            """,
            (user.id, user.first_name or "", user.username or "", now_iso()),
        )
        conn.commit()


def get_user_ids() -> list:
    with db_lock:
        return [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]


def save_channel(chat_id, title, username, invite_link) -> None:
    with db_lock:
        conn.execute(
            """
            INSERT INTO channels (chat_id, title, username, invite_link, added_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username,
                invite_link = excluded.invite_link
            """,
            (chat_id, title or "", username or "", invite_link, now_iso()),
        )
        conn.commit()


def get_channels() -> list:
    with db_lock:
        return conn.execute("SELECT * FROM channels ORDER BY id ASC").fetchall()


def get_channel_by_id(channel_db_id: int):
    with db_lock:
        return conn.execute(
            "SELECT * FROM channels WHERE id = ?", (channel_db_id,)
        ).fetchone()


def delete_channel(channel_db_id: int) -> None:
    with db_lock:
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_db_id,))
        conn.commit()


def save_file(tg_file_id, file_type, file_name, caption, created_by) -> int:
    with db_lock:
        cur = conn.execute(
            """
            INSERT INTO files (tg_file_id, file_type, file_name, caption, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tg_file_id, file_type, file_name or "", caption or "", created_by, now_iso()),
        )
        conn.commit()
        return cur.lastrowid


def get_file(file_db_id: int):
    with db_lock:
        return conn.execute("SELECT * FROM files WHERE id = ?", (file_db_id,)).fetchone()


def get_files(limit: int = 15) -> list:
    with db_lock:
        return conn.execute(
            "SELECT * FROM files ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def delete_file(file_db_id: int) -> None:
    with db_lock:
        conn.execute("DELETE FROM files WHERE id = ?", (file_db_id,))
        conn.commit()


def add_download(file_db_id: int) -> None:
    with db_lock:
        conn.execute(
            "UPDATE files SET downloads = downloads + 1 WHERE id = ?", (file_db_id,)
        )
        conn.commit()


def save_pending(user_id: int, file_db_id: int) -> None:
    with db_lock:
        conn.execute(
            """
            INSERT INTO pending (user_id, file_id, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                file_id = excluded.file_id,
                created_at = excluded.created_at
            """,
            (user_id, file_db_id, now_iso()),
        )
        conn.commit()


def get_pending(user_id: int):
    with db_lock:
        return conn.execute(
            "SELECT * FROM pending WHERE user_id = ?", (user_id,)
        ).fetchone()


def delete_pending(user_id: int) -> None:
    with db_lock:
        conn.execute("DELETE FROM pending WHERE user_id = ?", (user_id,))
        conn.commit()


def get_stats() -> dict:
    with db_lock:
        return {
            "channels": conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0],
            "files": conn.execute("SELECT COUNT(*) FROM files").fetchone()[0],
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "downloads": conn.execute(
                "SELECT COALESCE(SUM(downloads), 0) FROM files"
            ).fetchone()[0],
        }


# =====================================================================
#  3) 🧰 HELPERS
# =====================================================================
def is_admin(user_or_id) -> bool:
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


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, markup=None):
    return await context.bot.send_message(
        chat_id=update.effective_chat.id, text=text, reply_markup=markup
    )


async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    uname = context.application.bot_data.get("bot_username")
    if not uname:
        uname = (await context.bot.get_me()).username
        context.application.bot_data["bot_username"] = uname
    return uname


def file_link(username: str, file_db_id: int) -> str:
    return f"https://t.me/{username}?start=file_{file_db_id}"


def parse_chat_identifier(text: str):
    t = (text or "").strip()
    if not t or " " in t:
        return None
    if t.lstrip("-").isdigit():
        return int(t)
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if t.startswith(prefix):
            t = t[len(prefix):].split("/")[0].split("?")[0]
            break
    if not t:
        return None
    return t if t.startswith("@") else "@" + t


async def send_chunks(context, chat_id: int, header: str, items: list, markup=None):
    chunks, cur = [], header
    for item in items:
        if len(cur) + len(item) + 1 > 3500:
            chunks.append(cur)
            cur = ""
        cur += "\n" + item
    chunks.append(cur)
    for i, chunk in enumerate(chunks):
        last = i == len(chunks) - 1
        await context.bot.send_message(
            chat_id=chat_id, text=chunk, reply_markup=markup if last else None
        )


# =====================================================================
#  4) 🔒 FORCE-JOIN + FILE DELIVERY
# =====================================================================
JOINED_STATUSES = ("creator", "administrator", "member")


async def channel_status(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> list:
    result = []
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


def pending_channels(status: list) -> list:
    return [ch for ch, ok in status if not ok]


def force_sub_text(status: list) -> str:
    total = len(status)
    done = sum(1 for _, ok in status if ok)
    lines = []
    for i, (ch, ok) in enumerate(status, 1):
        mark = "✅" if ok else "❌"
        lines.append(f"{mark} <b>{i}. {esc(ch['title'])}</b>")
    return card(
        "🔒", "Access Locked",
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


def force_sub_keyboard(status: list, file_db_id: int) -> InlineKeyboardMarkup:
    rows = [
        [btn(f"📢 Join • {short(ch['title'], 26)}", url=ch["invite_link"], style=BLUE)]
        for ch in pending_channels(status)
    ]
    rows.append([btn("✅ Verify & Get File", f"verify:{file_db_id}", style=GREEN)])
    return kb(*rows)


def build_caption(row) -> str:
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


async def send_file(context: ContextTypes.DEFAULT_TYPE, chat_id: int, file_db_id: int) -> bool:
    row = get_file(file_db_id)
    if not row:
        await context.bot.send_message(
            chat_id,
            card("❌", "File Not Found",
                 "◈ File delete ho chuki hai ya link purana hai."),
        )
        return False

    method, arg = SEND_METHODS.get(row["file_type"], SEND_METHODS["document"])
    try:
        await getattr(context.bot, method)(
            chat_id=chat_id, caption=build_caption(row), **{arg: row["tg_file_id"]}
        )
        add_download(file_db_id)
        delete_pending(chat_id)
        return True
    except TelegramError as e:
        logger.exception("File send failed: %s", e)
        await context.bot.send_message(
            chat_id,
            card("❌", "Send Failed",
                 "◈ File bhejne me error aayi.",
                 f"<code>{esc(str(e))}</code>"),
        )
        return False


# =====================================================================
#  5) 🎯 COMMAND HANDLERS
# =====================================================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    args = context.args or []

    # Deep link: /start file_<id>
    if args and args[0].startswith("file_"):
        try:
            file_db_id = int(args[0][5:])
        except ValueError:
            await reply(update, context, card("❌", "Bad Link", "◈ Invalid link."))
            return

        row = get_file(file_db_id)
        if not row:
            await reply(update, context, card("❌", "File Not Found",
                                              "◈ File delete ho chuki hai."))
            return

        save_pending(update.effective_user.id, file_db_id)
        status = await channel_status(context, update.effective_user.id)
        pending = pending_channels(status)

        if pending:
            await reply(update, context,
                        force_sub_text(status),
                        markup=force_sub_keyboard(status, file_db_id))
        else:
            await reply(update, context,
                        card("✅", "Sending File", "◈ File bheji ja rahi hai…"))
            await send_file(context, update.effective_chat.id, file_db_id)
        return

    # Normal start
    if is_admin(update.effective_user):
        text = card(
            "🎁", f"Welcome to {BOT_NAME}",
            f"👤 <b>{esc(update.effective_user.first_name or 'Admin')}</b>",
            "",
            "◈ Aap <b>admin</b> hain. Neeche se option chunein 👇",
            footer=BOT_NAME,
        )
        await reply(update, context, text, markup=panel_kb())
    else:
        text = card(
            "🎁", f"Welcome to {BOT_NAME}",
            f"👤 <b>{esc(update.effective_user.first_name or 'User')}</b>",
            "",
            "◈ File receive karne ke liye <b>link</b> open karein.",
            footer=BOT_NAME,
        )
        await reply(update, context, text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)
    text = card(
        "ℹ️", "Help",
        "<b>📢 Add Channel</b> — /addchannel",
        "<b>📤 Upload File</b> — /upload",
        "<b>📣 Broadcast</b> — /broadcast",
        "<b>📂 My Files</b> — Admin Panel se",
        "<b>📊 Stats</b> — Admin Panel se",
        "",
        "<i>File link format:</i>",
        "<code>https://t.me/&lt;bot&gt;?start=file_&lt;id&gt;</code>",
        footer=BOT_NAME,
    )
    markup = panel_kb() if is_admin(update.effective_user) else None
    await reply(update, context, text, markup=markup)


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return
    await reply(
        update, context,
        card("🛠", "Admin Panel", "◈ Welcome back!", footer=BOT_NAME),
        markup=panel_kb(),
    )


# =====================================================================
#  6) 🛠 ADMIN CALLBACK ROUTER
# =====================================================================
async def adm_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await guard_admin(update):
        return
    await q.answer()

    data = q.data
    if data == "adm:home":
        await q.edit_message_text(
            card("🛠", "Admin Panel", "◈ Welcome back!", footer=BOT_NAME),
            reply_markup=panel_kb(),
        )

    elif data == "adm:stats":
        s = get_stats()
        text = card(
            "📊", "Bot Statistics",
            f"📢 <b>Channels:</b>  {s['channels']}",
            f"📂 <b>Files:</b>  {s['files']}",
            f"👥 <b>Users:</b>  {s['users']}",
            f"⬇️ <b>Downloads:</b>  {s['downloads']}",
            footer=BOT_NAME,
        )
        await q.edit_message_text(
            text, reply_markup=kb([btn("🛠 Back", "adm:home", style=BLUE)])
        )

    elif data == "adm:channels":
        await list_channels_cb(update, context)

    elif data == "adm:files":
        await my_files_cb(update, context)


async def list_channels_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    channels = get_channels()

    if not channels:
        await q.edit_message_text(
            card("📢", "Channels", "◈ Koi channel add nahi hua."),
            reply_markup=kb(
                [btn("➕ Add Channel", "adm:addch", style=GREEN)],
                [btn("🛠 Back", "adm:home", style=BLUE)],
            ),
        )
        return

    lines = []
    for ch in channels:
        uname = f"@{ch['username']}" if ch["username"] else "🔒 private"
        lines.append(f"• <b>{esc(ch['title'])}</b>  {uname}")

    text = card(
        "📢", "Channels",
        f"<b>Total:</b> {len(channels)}",
        "",
        "\n".join(lines),
        footer=BOT_NAME,
    )
    del_btns = [
        btn(f"🗑 #{ch['id']}", f"delch:{ch['id']}", style=RED) for ch in channels
    ]
    rows = [del_btns[i:i + 4] for i in range(0, len(del_btns), 4)]
    rows.append([btn("➕ Add Channel", "adm:addch", style=GREEN),
                 btn("🛠 Back", "adm:home", style=BLUE)])
    await q.edit_message_text(text, reply_markup=kb(*rows))


async def my_files_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    files = get_files(limit=15)

    if not files:
        await q.edit_message_text(
            card("📂", "My Files", "◈ Abhi tak koi file upload nahi hui."),
            reply_markup=kb(
                [btn("📤 Upload File", "adm:upload", style=GREEN)],
                [btn("🛠 Back", "adm:home", style=BLUE)],
            ),
        )
        return

    lines = []
    for f in files:
        icon = FILE_ICONS.get(f["file_type"], "📄")
        name = short(f["file_name"] or f"file #{f['id']}", 32)
        lines.append(f"{icon} <b>#{f['id']}</b>  {esc(name)}  ⬇️ {f['downloads']}")

    text = card(
        "📂", "My Files",
        f"<b>Recent {len(files)}</b>",
        "",
        "\n".join(lines),
        footer=BOT_NAME,
    )
    del_btns = [
        btn(f"🗑 #{f['id']}", f"delfile:{f['id']}", style=RED) for f in files
    ]
    rows = [del_btns[i:i + 4] for i in range(0, len(del_btns), 4)]
    rows.append([btn("📤 Upload File", "adm:upload", style=GREEN),
                 btn("🛠 Back", "adm:home", style=BLUE)])
    await q.edit_message_text(text, reply_markup=kb(*rows))


async def delete_channel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await guard_admin(update):
        return
    ch_db_id = int(q.data.split(":")[1])
    row = get_channel_by_id(ch_db_id)
    delete_channel(ch_db_id)
    await q.answer("🗑 Channel removed!", show_alert=True)
    await list_channels_cb(update, context)


async def delete_file_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await guard_admin(update):
        return
    file_db_id = int(q.data.split(":")[1])
    delete_file(file_db_id)
    await q.answer("🗑 File deleted!", show_alert=True)
    await my_files_cb(update, context)


# =====================================================================
#  7) 🔐 VERIFY (force-join)
# =====================================================================
async def verify_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q.data.startswith("verify:"):
        return
    await q.answer("🔍 Checking…")

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
            card("✅", "Verified!",
                 "◈ Sab channels joined.",
                 "📤 File bheji ja rahi hai…",
                 footer=BOT_NAME)
        )
    except BadRequest:
        pass

    await send_file(context, q.message.chat_id, file_db_id)


# =====================================================================
#  8) ➕ ADD CHANNEL (conversation)
# =====================================================================
ADDCH_INPUT = 1


async def addchannel_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    markup = select_chat_keyboard()
    text = card(
        "➕", "Add Channel",
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


async def _resolve_and_save_channel(context, chat_obj, fallback_id=None):
    """Chat object se channel resolve karke save karta hai."""
    chat_id = chat_obj.id if chat_obj else fallback_id
    if not chat_id:
        return None, "❌ Chat identify nahi hua."

    try:
        full = await context.bot.get_chat(chat_id)
    except TelegramError as e:
        return None, f"❌ Chat access nahi mila: <code>{esc(str(e))}</code>"

    invite = full.invite_link
    if not invite:
        try:
            invite = await context.bot.export_chat_invite_link(chat_id)
        except TelegramError:
            invite = None
    if not invite and full.username:
        invite = f"https://t.me/{full.username}"
    if not invite:
        return None, (
            "❌ Invite link nahi mila. Bot ko channel me <b>admin</b> banao "
            "(invite users permission ke saath)."
        )

    save_channel(chat_id, full.title or "", full.username or "", invite)
    return full, None


async def addchannel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return ADDCH_INPUT

    # Cancel
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
            await msg.reply_text(
                f"❌ Chat info nahi mila: <code>{esc(str(e))}</code>"
            )
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

    full, error = await _resolve_and_save_channel(context, chat_obj)
    if error:
        await msg.reply_text(error)
        return ADDCH_INPUT

    await msg.reply_text(
        card(
            "✅", "Channel Added",
            f"📢 <b>{esc(full.title)}</b>",
            f"🆔 <code>{full.id}</code>",
            f"🔗 <a href='{esc(full.invite_link or '')}'>Invite Link</a>",
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
#  9) 📤 UPLOAD FILE (conversation)
# =====================================================================
UPLOAD_INPUT = 1


async def upload_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    await reply(
        update, context,
        card(
            "📤", "Upload File",
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


async def upload_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return UPLOAD_INPUT

    ft = fid = fname = None

    if msg.document:
        ft, fid = "document", msg.document.file_id
        fname = msg.document.file_name or ""
    elif msg.video:
        ft, fid = "video", msg.video.file_id
        fname = msg.video.file_name or ""
    elif msg.photo:
        ft, fid = "photo", msg.photo[-1].file_id
    elif msg.audio:
        ft, fid = "audio", msg.audio.file_id
        fname = msg.audio.file_name or ""
    elif msg.voice:
        ft, fid = "voice", msg.voice.file_id
    elif msg.animation:
        ft, fid = "animation", msg.animation.file_id
        fname = msg.animation.file_name or ""

    if not ft:
        await msg.reply_text(
            "❌ Sirf file/video/photo/audio/voice/animation bhejo.",
            reply_markup=cancel_kb(),
        )
        return UPLOAD_INPUT

    caption = msg.caption or ""
    file_db_id = save_file(fid, ft, fname, caption, update.effective_user.id)
    username = await get_bot_username(context)
    link = file_link(username, file_db_id)

    await msg.reply_text(
        card(
            "✅", "File Uploaded",
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
            [btn("📂 My Files", "adm:files", style=BLUE),
             btn("📤 Upload Another", "adm:upload", style=GREEN)],
            [btn("🛠 Panel", "adm:home", style=BLUE)],
        ),
    )
    return ConversationHandler.END


# =====================================================================
#  10) 📣 BROADCAST (conversation)
# =====================================================================
BCAST_INPUT = 1


async def broadcast_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()

    total = len(get_user_ids())
    await reply(
        update, context,
        card(
            "📣", "Broadcast",
            f"◈ <b>{total}</b> users ko message bhejna hai.",
            "",
            "Koi bhi message bhejo (text/photo/video/file).",
            "<i>Sab users ko waisa hi copy hoga.</i>",
            footer=BOT_NAME,
        ),
        markup=cancel_kb(),
    )
    return BCAST_INPUT


async def broadcast_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return BCAST_INPUT

    user_ids = get_user_ids()
    if not user_ids:
        await msg.reply_text(card("📣", "Broadcast", "◈ Koi user nahi hai abhi."))
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
            await asyncio.sleep(e.retry_after + 1)
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
                    card("⏳", "Broadcasting…",
                         f"◈ {i} / {len(user_ids)}",
                         f"✅ Sent: {sent}  ❌ Failed: {failed}")
                )
            except BadRequest:
                pass
            await asyncio.sleep(1)

    await status_msg.edit_text(
        card(
            "✅", "Broadcast Complete",
            f"✅ <b>Sent:</b> {sent}",
            f"❌ <b>Failed:</b> {failed}",
            f"👥 <b>Total:</b> {len(user_ids)}",
            footer=BOT_NAME,
        ),
        reply_markup=kb([btn("🛠 Panel", "adm:home", style=BLUE)]),
    )
    return ConversationHandler.END


# =====================================================================
#  11) ❌ CANCEL
# =====================================================================
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            card("❌", "Cancelled", "◈ Operation cancel ho gaya."),
            reply_markup=ReplyKeyboardRemove(),
        )
    return ConversationHandler.END


async def cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Cancelled")
    try:
        await q.message.edit_text(
            card("❌", "Cancelled", "◈ Operation cancel ho gaya.")
        )
    except BadRequest:
        pass
    return ConversationHandler.END


# =====================================================================
#  12) 🤝 CHANNEL EVENT HANDLERS
# =====================================================================
async def chat_join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    if not req:
        return
    try:
        await context.bot.approve_chat_join_request(
            chat_id=req.chat.id, user_id=req.from_user.id
        )
        logger.info("Join approved: user=%s chat=%s",
                    req.from_user.id, req.chat.id)
        try:
            await context.bot.send_message(
                req.from_user.id,
                card(
                    "✅", "Request Approved",
                    "◈ Aap channel me add ho gaye.",
                    "Ab bot me wapas aakar <b>Verify</b> dabayein.",
                    footer=BOT_NAME,
                ),
            )
        except TelegramError:
            pass
    except TelegramError as e:
        logger.exception("Join approve failed: %s", e)


async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        invite = chat.invite_link
        if not invite:
            try:
                invite = await context.bot.export_chat_invite_link(chat.id)
            except TelegramError:
                invite = None
        if not invite and chat.username:
            invite = f"https://t.me/{chat.username}"
        if invite:
            save_channel(chat.id, chat.title or "", chat.username or "", invite)
            logger.info("Auto-added channel: %s", chat.id)
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        card(
                            "✅", "Channel Auto-Added",
                            f"📢 <b>{esc(chat.title)}</b>",
                            f"🆔 <code>{chat.id}</code>",
                            footer=BOT_NAME,
                        ),
                    )
                except TelegramError:
                    pass

    if not is_admin_now and was_admin:
        with db_lock:
            row = conn.execute(
                "SELECT id FROM channels WHERE chat_id = ?", (chat.id,)
            ).fetchone()
        if row:
            delete_channel(row["id"])
            logger.info("Removed channel (bot demoted): %s", chat.id)


async def forwarded_channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin koi channel message forward kare -> auto add."""
    msg = update.message
    if not msg or not msg.forward_from_chat:
        return
    if not is_admin(update.effective_user):
        return

    chat = msg.forward_from_chat
    if chat.type != "channel":
        return

    full, error = await _resolve_and_save_channel(context, chat)
    if error:
        await msg.reply_text(error)
        return

    await msg.reply_text(
        card(
            "✅", "Channel Added",
            f"📢 <b>{esc(full.title)}</b>",
            f"🆔 <code>{full.id}</code>",
            footer=BOT_NAME,
        ),
        reply_markup=panel_kb(),
    )


# =====================================================================
#  13) 🚨 ERROR HANDLER
# =====================================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Update error:", exc_info=context.error)
    if isinstance(context.error, RetryAfter):
        await asyncio.sleep(context.error.retry_after)
        return
    if isinstance(context.error, (BadRequest, Forbidden)):
        return


# =====================================================================
#  14) 🚀 MAIN
# =====================================================================
async def _post_init(app: Application):
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
        await app.bot.set_my_commands(commands)
        for admin_id in ADMIN_IDS:
            try:
                await app.bot.set_my_commands(
                    commands, scope=BotCommandScopeChat(chat_id=admin_id)
                )
            except TelegramError:
                pass
    except TelegramError as e:
        logger.warning("Commands set failed: %s", e)


def _build_app() -> Application:
    defaults = Defaults(parse_mode=ParseMode.HTML)
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .defaults(defaults)
        .post_init(_post_init)
        .build()
    )

    # --- Conversations ---
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
        fallbacks=[
            CommandHandler("cancel", cancel_cmd),
            CallbackQueryHandler(cancel_cb, pattern=r"^cancel$"),
        ],
        per_chat=True,
        per_user=True,
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
        fallbacks=[
            CommandHandler("cancel", cancel_cmd),
            CallbackQueryHandler(cancel_cb, pattern=r"^cancel$"),
        ],
        per_chat=True,
        per_user=True,
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
        fallbacks=[
            CommandHandler("cancel", cancel_cmd),
            CallbackQueryHandler(cancel_cb, pattern=r"^cancel$"),
        ],
        per_chat=True,
        per_user=True,
    )

    app.add_handler(addchannel_conv)
    app.add_handler(upload_conv)
    app.add_handler(broadcast_conv)

    # --- Commands ---
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))

    # --- Callbacks ---
    app.add_handler(CallbackQueryHandler(verify_cb, pattern=r"^verify:"))
    app.add_handler(CallbackQueryHandler(delete_channel_cb, pattern=r"^delch:"))
    app.add_handler(CallbackQueryHandler(delete_file_cb, pattern=r"^delfile:"))
    app.add_handler(CallbackQueryHandler(adm_router, pattern=r"^adm:"))

    # --- Channel events ---
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


def main():
    init_db()
    logger.info("Database initialized: %s", DB_PATH)
    app = _build_app()
    logger.info("Starting bot in polling mode…")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
