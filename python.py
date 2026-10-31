#!/usr/bin/env python3
# =====================================================================
#   ✦  𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗙𝗜𝗟𝗘 𝗩𝗔𝗨𝗟𝗧  —  TELEGRAM FILE SHARE BOT  (SINGLE FILE)  ✦
# =====================================================================
#  SETUP
#   1) Neeche BOT_TOKEN aur ADMIN_IDS bharo
#   2) pip install -U "python-telegram-bot>=21,<23"
#   3) python python.py
#
#  CHANNEL ADD KARNE KE 4 AASAAN TARIKE (private + public dono)
#   ➤ /addchannel  ->  "Select Channel" button  ->  channel chuno
#                      (bot khud admin ban jata hai)
#   ➤ Bot ko kisi bhi channel me Admin bana do -> bot khud detect karega
#   ➤ @username  ya  -100... ID bhejo
#   ➤ Channel ka koi message forward karo
#
#  NOTE: Colored buttons (blue/green/red) ke liye Telegram app latest
#        hona chahiye. Purane app me buttons normal dikhenge, kaam same.
# =====================================================================

BOT_TOKEN = "9284478108:AAGpA4bLpH8I81sdAgEj5oKSJSjIn-yx3ew"   # ya environment variable BOT_TOKEN
ADMIN_IDS = [8917638509]                   # apni numeric Telegram ID(s)
BOT_NAME = "FILE_SHARE_00_bot"           # bot ka brand naam
DB_PATH = "bot_data.db"

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

BOT_TOKEN = os.getenv("BOT_TOKEN", BOT_TOKEN)

# ConversationHandler ki harmless per_message warning band (bot par koi asar nahi)
warnings.filterwarnings("ignore", message=".*per_message.*")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("premium-vault")


# =====================================================================
#  1) ✨ THEME  —  stylish fonts, premium cards, colored buttons
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

# Telegram button colors: primary = blue, success = green, danger = red
BLUE, GREEN, RED = "primary", "success", "danger"

_SMALL = dict(zip("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"))


def bold(text: str) -> str:
    """Stylish bold font:  Hello 123  ->  𝗛𝗲𝗹𝗹𝗼 𝟭𝟮𝟯"""
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
    """Stylish small caps:  Powered by  ->  ᴘᴏᴡᴇʀᴇᴅ ʙʏ"""
    return "".join(_SMALL.get(ch, ch) for ch in str(text).lower())


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def short(text, limit: int = 30) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def card(icon: str, title: str, *body: str, footer: str = "") -> str:
    """Premium framed message. `title` plain text do (escape card khud karta hai)."""
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
    """Inline button with optional color style."""
    kwargs = {}
    if style:
        kwargs["api_kwargs"] = {"style": style}
    if url:
        return InlineKeyboardButton(text, url=url, **kwargs)
    return InlineKeyboardButton(text, callback_data=data, **kwargs)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([list(r) for r in rows if r])


def style_for(callback_data: str) -> str:
    """Style used when rebuilding a keyboard from an existing message."""
    cd = callback_data or ""
    if cd.startswith("del_") or cd == "cancel":
        return RED
    if cd in ("adm:addch", "adm:upload"):
        return GREEN
    return BLUE


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


# ---- "Select Channel" keyboard (private + public dono chunne ke liye) --
CANCEL_TEXT = "❌ Cancel"


def select_chat_keyboard():
    """Telegram ka native chat-picker. Admin apni list se channel chunta hai
    aur bot khud us channel me admin ban jata hai (invite permission ke saath)."""
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
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
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
    except Exception as e:  # purana PTB version
        logger.warning("Select-chat keyboard unavailable: %s", e)
        return None


# =====================================================================
#  2) 🗄️ DATABASE
# =====================================================================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
db_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
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
        # purane database ke liye migration (downloads column)
        try:
            conn.execute("ALTER TABLE files ADD COLUMN downloads INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        conn.commit()


# ---- users ----------------------------------------------------------
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


# ---- channels -------------------------------------------------------
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


def is_force_channel(chat_id: int) -> bool:
    with db_lock:
        row = conn.execute("SELECT 1 FROM channels WHERE chat_id = ?", (chat_id,)).fetchone()
    return row is not None


def delete_channel(channel_db_id: int) -> None:
    with db_lock:
        conn.execute("DELETE FROM channels WHERE id = ?", (channel_db_id,))
        conn.commit()


# ---- files ----------------------------------------------------------
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


def get_files(limit: int = 20) -> list:
    with db_lock:
        return conn.execute("SELECT * FROM files ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def delete_file(file_db_id: int) -> None:
    with db_lock:
        conn.execute("DELETE FROM files WHERE id = ?", (file_db_id,))
        conn.commit()


def add_download(file_db_id: int) -> None:
    with db_lock:
        conn.execute("UPDATE files SET downloads = downloads + 1 WHERE id = ?", (file_db_id,))
        conn.commit()


# ---- pending (user ne kaunsi file maangi thi) -------------------------
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
        return conn.execute("SELECT * FROM pending WHERE user_id = ?", (user_id,)).fetchone()


def delete_pending(user_id: int) -> None:
    with db_lock:
        conn.execute("DELETE FROM pending WHERE user_id = ?", (user_id,))
        conn.commit()


# ---- stats ----------------------------------------------------------
def get_stats() -> dict:
    with db_lock:
        return {
            "channels": conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0],
            "files": conn.execute("SELECT COUNT(*) FROM files").fetchone()[0],
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "downloads": conn.execute("SELECT COALESCE(SUM(downloads), 0) FROM files").fetchone()[0],
        }


# =====================================================================
#  3) 🧰 CORE HELPERS
# =====================================================================
def is_admin(user_or_id) -> bool:
    uid = getattr(user_or_id, "id", user_or_id)
    try:
        return int(uid) in ADMIN_IDS
    except (TypeError, ValueError):
        return False


async def guard_admin(update: Update) -> bool:
    """True agar admin hai, warna denied message bhejta hai."""
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
    """Message/callback dono me kaam karne wala reply."""
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


def is_private_invite(text: str) -> bool:
    """t.me/+xxxx ya t.me/joinchat/xxxx  (isse channel resolve nahi hota)."""
    t = (text or "").strip()
    return "t.me/+" in t or "t.me/joinchat" in t


def parse_chat_identifier(text: str):
    """@username / t.me/username / -100... ID ko Telegram identifier me badalta hai."""
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


async def send_chunks(context, chat_id: int, header: str, items: list, markup=None) -> None:
    """Lambi list ko 4096 limit ke andar tod kar bhejta hai."""
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
    """[(channel_row, joined_bool), ...] — har channel ka live status."""
    result = []
    for ch in get_channels():
        joined = True
        try:
            member = await context.bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            status = str(member.status)
            joined = status in JOINED_STATUSES or (
                status == "restricted" and bool(getattr(member, "is_member", False))
            )
        except TelegramError as e:
            # bot check nahi kar paaya (admin hata diya gaya ho sakta hai) -> user ko block mat karo
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
            card("❌", "File Not Found", "◈ File delete ho chuki hai ya link purana hai."),
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
            card("⚠️", "Send Failed",
                 "◈ File bhejne me error aaya.",
                 "◈ Admin se file dobara upload karwayein."),
        )
        return False


def verified_text() -> str:
    return card(
        "🎉", "Verified",
        "✅ Sab channels join ho gaye!",
        "📦 File bhej raha hoon... <b>enjoy!</b> ✨",
        footer=BOT_NAME,
    )


# =====================================================================
#  5) 👤 USER HANDLERS
# =====================================================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user, msg = update.effective_user, update.effective_message

    if update.effective_chat.type != "private":
        await msg.reply_text(card("💬", "Private Chat Only", "◈ Ye bot private chat me use karein."))
        return

    save_user(user)
    payload = context.args[0] if context.args else ""

    # ---- file link khola gaya -----------------------------------------
    if payload.startswith("file_"):
        try:
            file_db_id = int(payload.split("_", 1)[1])
        except ValueError:
            await msg.reply_text(card("❌", "Invalid Link", "◈ Ye file link galat hai."))
            return

        if not get_file(file_db_id):
            await msg.reply_text(
                card("❌", "File Not Found", "◈ File nahi mili.", "◈ Link expire ho sakta hai.")
            )
            return

        save_pending(user.id, file_db_id)
        status = await channel_status(context, user.id)

        if not pending_channels(status):
            await msg.reply_text(verified_text())
            await send_file(context, user.id, file_db_id)
            return

        await msg.reply_text(
            force_sub_text(status), reply_markup=force_sub_keyboard(status, file_db_id)
        )
        return

    # ---- normal /start ------------------------------------------------
    name = short(user.first_name or "Friend", 18)
    text = card(
        "👑", f"Welcome {name}",
        "➤ Admin ka diya <b>file link</b> kholiye",
        "➤ Required channels <b>join</b> kariye",
        "➤ <b>Verify</b> button dabaiye",
        "➤ File turant aapko mil jayegi 🎁",
        footer=BOT_NAME,
    )
    markup = None
    if is_admin(user):
        text += "\n\n🛠 <b>Admin?</b> Panel neeche se kholiye 👇"
        markup = home_kb()
    await msg.reply_text(text, reply_markup=markup)


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.effective_message.reply_text(
        card("🆔", "Your Telegram ID", f"◈ <code>{user.id}</code>", "<i>Tap karke copy karein.</i>")
    )


async def verify_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    try:
        file_db_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer()
        return

    if not get_file(file_db_id):
        await query.answer("❌ File nahi mili ya delete ho gayi.", show_alert=True)
        return

    status = await channel_status(context, user_id)
    left = pending_channels(status)

    if not left:
        await query.answer("🎉 Verified!")
        try:
            await query.edit_message_text(verified_text())
        except TelegramError:
            pass
        await send_file(context, user_id, file_db_id)
        return

    await query.answer(f"❌ Abhi {len(left)} channel join karna baaki hai!", show_alert=True)
    try:
        await query.edit_message_text(
            force_sub_text(status), reply_markup=force_sub_keyboard(status, file_db_id)
        )
    except BadRequest:
        pass  # message not modified


async def join_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force-join channel ki join request auto-approve + file auto-send."""
    req = update.chat_join_request
    user_id = req.from_user.id
    dm_chat = getattr(req, "user_chat_id", None) or user_id

    if not is_force_channel(req.chat.id):
        return  # sirf apne force-join channels ki requests approve karte hain

    try:
        await context.bot.approve_chat_join_request(chat_id=req.chat.id, user_id=user_id)
        logger.info("Join request approved user=%s chat=%s", user_id, req.chat.id)
    except TelegramError as e:
        logger.warning("Join request approve failed: %s", e)
        return

    pending = get_pending(user_id)
    if not pending:
        return

    status = await channel_status(context, user_id)
    left = pending_channels(status)
    try:
        if not left:
            await context.bot.send_message(dm_chat, verified_text())
            await send_file(context, dm_chat, pending["file_id"])
        else:
            await context.bot.send_message(
                dm_chat,
                card(
                    "✅", "Request Approved",
                    f"◈ <b>{esc(req.chat.title)}</b> join ho gaya!",
                    f"◈ Abhi <b>{len(left)}</b> channel baaki hai.",
                    "Baaki join karke <b>Verify</b> dabayein 👇",
                ),
                reply_markup=force_sub_keyboard(status, pending["file_id"]),
            )
    except TelegramError as e:
        logger.warning("Auto message failed: %s", e)


# =====================================================================
#  6) 🛠️ ADMIN PANEL + LISTS
# =====================================================================
def panel_text() -> str:
    return card(
        "🛠", "Admin Control Room",
        "◈ /addchannel ➜ Channel / group jodein",
        "◈ /channels ➜ Channel list + remove",
        "◈ /upload ➜ File upload + share link",
        "◈ /files ➜ File list + delete",
        "◈ /broadcast ➜ Sabko message bhejein",
        "◈ /stats ➜ Statistics",
        "◈ /cancel ➜ Koi bhi process cancel",
        "",
        "👇 <b>Ya neeche ke buttons use karein</b>",
        footer=BOT_NAME,
    )


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return
    await reply(update, context, panel_text(), panel_kb())


async def stats_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_stats()
    await reply(
        update, context,
        card(
            "📊", "Bot Statistics",
            f"◈ 📢 Channels  ➜  <b>{s['channels']}</b>",
            f"◈ 📂 Files  ➜  <b>{s['files']}</b>",
            f"◈ 👥 Users  ➜  <b>{s['users']}</b>",
            f"◈ 📥 Downloads  ➜  <b>{s['downloads']}</b>",
            footer=BOT_NAME,
        ),
        home_kb(),
    )


async def channels_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_channels()
    if not rows:
        await reply(
            update, context,
            card("📢", "No Channels", "◈ Abhi koi force-join channel add nahi hai."),
            kb([btn("➕ Add Channel", "adm:addch", style=GREEN)]),
        )
        return

    items, buttons = [], []
    for i, ch in enumerate(rows, 1):
        items.append(
            f"\n❖ <b>{i}. {esc(ch['title'])}</b>\n"
            f"   🆔 <code>{ch['chat_id']}</code>\n"
            f"   🔗 <code>{esc(ch['invite_link'])}</code>"
        )
        buttons.append(btn(f"🗑 {i}. {short(ch['title'], 16)}", f"del_ch:{ch['id']}", style=RED))

    grid = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    grid.append([btn("➕ Add Channel", "adm:addch", style=GREEN),
                 btn("🛠 Panel", "adm:home", style=BLUE)])

    header = card("📢", f"Force-Join Channels ({len(rows)})")
    await send_chunks(context, update.effective_chat.id, header, items, kb(*grid))


async def files_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_files(limit=20)
    if not rows:
        await reply(
            update, context,
            card("📂", "No Files", "◈ Abhi koi file upload nahi hui."),
            kb([btn("📤 Upload File", "adm:upload", style=GREEN)]),
        )
        return

    username = await get_bot_username(context)
    items, buttons = [], []
    for row in rows:
        title = row["caption"] or row["file_name"] or f"File #{row['id']}"
        icon = FILE_ICONS.get(row["file_type"], "📄")
        items.append(
            f"\n❖ {icon} <b>#{row['id']} • {esc(short(title, 40))}</b>\n"
            f"   📥 Downloads ➜ <b>{row['downloads']}</b>\n"
            f"   🔗 <code>{file_link(username, row['id'])}</code>"
        )
        buttons.append(btn(f"🗑 Delete #{row['id']}", f"del_file:{row['id']}", style=RED))

    grid = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    grid.append([btn("📤 Upload File", "adm:upload", style=GREEN),
                 btn("🛠 Panel", "adm:home", style=BLUE)])

    header = card("📂", f"Uploaded Files ({len(rows)})")
    await send_chunks(context, update.effective_chat.id, header, items, kb(*grid))


async def channels_cmd(update, context):
    if await guard_admin(update):
        await channels_view(update, context)


async def files_cmd(update, context):
    if await guard_admin(update):
        await files_view(update, context)


async def stats_cmd(update, context):
    if await guard_admin(update):
        await stats_view(update, context)


async def admin_nav_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel ke navigation buttons: home / channels / files / stats."""
    if not await guard_admin(update):
        return
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    if action == "home":
        await reply(update, context, panel_text(), panel_kb())
    elif action == "channels":
        await channels_view(update, context)
    elif action == "files":
        await files_view(update, context)
    elif action == "stats":
        await stats_view(update, context)


async def _drop_button(query, callback_data: str) -> None:
    """Delete ke baad message se wo button hata do (baaki keyboard same rahe)."""
    markup = query.message.reply_markup if query.message else None
    if not markup:
        return
    rows = []
    for row in markup.inline_keyboard:
        new_row = []
        for b in row:
            if b.callback_data == callback_data:
                continue
            if b.url:
                new_row.append(btn(b.text, url=b.url, style=BLUE))
            else:
                new_row.append(btn(b.text, b.callback_data, style=style_for(b.callback_data)))
        if new_row:
            rows.append(new_row)
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows) if rows else None)
    except TelegramError:
        pass


async def delete_channel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return
    query = update.callback_query
    try:
        channel_db_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer()
        return
    delete_channel(channel_db_id)
    await query.answer("🗑 Channel remove ho gaya!", show_alert=False)
    await _drop_button(query, query.data)


async def delete_file_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return
    query = update.callback_query
    try:
        file_db_id = int(query.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer()
        return
    delete_file(file_db_id)
    await query.answer("🗑 File delete ho gayi!", show_alert=False)
    await _drop_button(query, query.data)


# =====================================================================
#  7) ➕ ADD CHANNEL  —  private + public, 4 aasaan tareeke
# =====================================================================
AC_WAIT, AC_LINK = range(2)


async def try_register_channel(context: ContextTypes.DEFAULT_TYPE, chat, retries: int = 3):
    """Channel ko force-join list me jodta hai.
    Returns: ("ok", link) | ("need_link", None) | ("not_admin", None)"""
    me = await context.bot.get_me()

    bot_status = ""
    for attempt in range(retries):
        try:
            member = await context.bot.get_chat_member(chat_id=chat.id, user_id=me.id)
            bot_status = str(member.status)
        except TelegramError:
            bot_status = ""
        if bot_status in ("administrator", "creator"):
            break
        if attempt < retries - 1:
            await asyncio.sleep(1.2)  # Select button se bot ko admin banne me thoda time lagta hai

    if bot_status not in ("administrator", "creator"):
        return "not_admin", None

    title = chat.title or chat.username or str(chat.id)
    link = None
    try:
        link_obj = await context.bot.create_chat_invite_link(
            chat_id=chat.id, creates_join_request=True, name="ForceSub"
        )
        link = link_obj.invite_link
    except TelegramError as e:
        logger.warning("Invite link create failed: %s", e)
        if chat.username:
            link = f"https://t.me/{chat.username}"  # public channel fallback

    if link:
        save_channel(chat.id, title, chat.username, link)
        return "ok", link
    return "need_link", None


def channel_added_view(chat_id, title, link, auto: bool = False):
    total = len(get_channels())
    lines = [
        f"◈ 📢 <b>{esc(title)}</b>",
        f"◈ 🆔 <code>{chat_id}</code>",
        f"◈ 🔗 <code>{esc(link)}</code>",
        f"◈ 📊 Total channels ➜ <b>{total}</b>",
    ]
    if auto:
        lines.append("◈ ⚡ Bot ko admin banate hi <b>auto-detect</b> ho gaya")
    text = card(
        "✅", "Channel Added", *lines,
        footer="ab har file link par ye channel join karna padega",
    )
    markup = kb(
        [btn("➕ Add Another", "adm:addch", style=GREEN),
         btn("📢 Channels", "adm:channels", style=BLUE)],
        [btn("🛠 Admin Panel", "adm:home", style=BLUE)],
    )
    return text, markup


async def addch_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.pop("pending_channel", None)

    text = card(
        "📢", "Add Channel / Group",
        "➤ <b>Sabse aasan:</b> neeche <b>Select Channel</b> dabayein, apna channel "
        "chunein — bot khud admin ban jayega ✨",
        "",
        "➤ Ya channel me <b>bot ko Admin banayein</b> — bot khud detect kar lega",
        "",
        "➤ Ya bhejein: <code>@username</code>  •  <code>-100…</code> ID  •  "
        "channel ka <b>forwarded message</b>",
        "",
        "<blockquote>🔐 Private aur 🌐 Public — dono chalenge</blockquote>",
    )
    markup = select_chat_keyboard() or cancel_kb()
    await reply(update, context, text, markup)
    return AC_WAIT


async def _ac_fail(msg, title: str, *lines: str):
    await msg.reply_text(
        card("❌", title, *lines),
        reply_markup=select_chat_keyboard() or cancel_kb(),
    )
    return AC_WAIT


async def _fetch_chat(context, ident, tries: int = 3):
    last_err = None
    for attempt in range(tries):
        try:
            return await context.bot.get_chat(ident), None
        except TelegramError as e:
            last_err = e
            if attempt < tries - 1:
                await asyncio.sleep(1.2)
    return None, last_err


async def addch_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if (msg.text or "").strip() == CANCEL_TEXT:
        return await cancel_cmd(update, context)

    ident = None
    shared = getattr(msg, "chat_shared", None)
    origin = getattr(msg, "forward_origin", None)
    fchat = (
        getattr(origin, "chat", None)
        or getattr(origin, "sender_chat", None)
        or getattr(msg, "forward_from_chat", None)
    )

    if shared is not None:
        ident = shared.chat_id                      # "Select Channel" button
    elif fchat is not None:
        ident = fchat.id                            # forwarded message
    elif msg.text:
        if is_private_invite(msg.text):
            return await _ac_fail(
                msg, "Private Invite Link",
                "◈ Private invite link se channel pehchana nahi ja sakta.",
                "",
                "✨ Neeche <b>Select Channel</b> dabayein",
                "✨ ya channel ka koi <b>message forward</b> karein",
                "✨ ya bot ko channel me <b>Admin</b> banayein",
            )
        ident = parse_chat_identifier(msg.text)

    if ident is None:
        return await _ac_fail(
            msg, "Channel Not Found",
            "◈ Channel identify nahi hua.",
            "◈ Select button dabayein, ya <code>@username</code> / <code>-100…</code> ID / "
            "forwarded message bhejein.",
        )

    working = await msg.reply_text(
        card("⏳", "Checking", "◈ Channel verify ho raha hai, thoda ruko..."),
        reply_markup=ReplyKeyboardRemove(),
    )

    async def _clear_working():
        try:
            await working.delete()
        except TelegramError:
            pass

    chat, err = await _fetch_chat(context, ident)
    if chat is None:
        await _clear_working()
        return await _ac_fail(
            msg, "Chat Not Found",
            f"◈ {esc(err)}",
            "◈ Bot us channel me hona chahiye. Select Channel button sabse safe hai.",
        )

    if chat.type not in ("channel", "supergroup"):
        await _clear_working()
        return await _ac_fail(
            msg, "Wrong Chat Type",
            "◈ Sirf <b>channel</b> ya <b>supergroup</b> add ho sakta hai.",
            "◈ Normal group ho to pehle use supergroup banayein.",
        )

    result, link = await try_register_channel(context, chat)

    if result == "ok":
        text, markup = channel_added_view(chat.id, chat.title or chat.username or chat.id, link)
        try:
            await working.edit_text(text, reply_markup=markup)
        except TelegramError:
            await msg.reply_text(text, reply_markup=markup)
        return ConversationHandler.END

    if result == "need_link":
        await _clear_working()
        context.user_data["pending_channel"] = {
            "chat_id": chat.id,
            "title": chat.title or chat.username or str(chat.id),
            "username": chat.username,
        }
        await msg.reply_text(
            card("⚠️", "Invite Link Needed",
                 "◈ Bot invite link create nahi kar paya.",
                 "◈ Channel ka invite link bhejein: <code>https://t.me/…</code>",
                 "",
                 "<i>Note: Auto-approve sirf bot-created join-request link par chalta hai.</i>"),
            reply_markup=cancel_kb(),
        )
        return AC_LINK

    await _clear_working()
    return await _ac_fail(
        msg, "Bot Is Not Admin",
        "◈ Bot is channel me <b>admin</b> nahi hai.",
        "",
        "✨ Aasan tareeka: <b>Select Channel</b> dabakar chunein — bot khud admin ban jayega",
        "✨ ya channel settings me bot ko Admin banayein "
        "(<b>Invite Users via Link</b> permission ke saath)",
    )


async def addch_link_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    link = (msg.text or "").strip()
    if link.startswith("t.me/"):
        link = "https://" + link

    if not link.startswith(("https://t.me/", "http://t.me/")):
        await msg.reply_text(
            card("❌", "Invalid Link", "◈ Valid link bhejein: <code>https://t.me/…</code>"),
            reply_markup=cancel_kb(),
        )
        return AC_LINK

    data = context.user_data.pop("pending_channel", None)
    if not data:
        await msg.reply_text(card("⌛", "Session Expired", "◈ /addchannel dobara shuru karein."))
        return ConversationHandler.END

    save_channel(data["chat_id"], data["title"], data.get("username"), link)
    text, markup = channel_added_view(data["chat_id"], data["title"], link)
    await msg.reply_text(text, reply_markup=markup)
    return ConversationHandler.END


async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot ko kisi channel me Admin banate hi channel auto-add (sirf bot-admin ke liye)."""
    change = update.my_chat_member
    if change is None:
        return
    chat = change.chat
    if chat.type not in ("channel", "supergroup"):
        return

    new_status = str(change.new_chat_member.status)
    old_status = str(change.old_chat_member.status)
    actor = change.from_user

    # ---- bot ko admin banaya gaya ----------------------------------------
    if new_status == "administrator" and old_status != "administrator":
        if not is_admin(actor):
            return
        result, link = await try_register_channel(context, chat, retries=1)
        try:
            if result == "ok":
                text, markup = channel_added_view(
                    chat.id, chat.title or chat.username or chat.id, link, auto=True
                )
                await context.bot.send_message(actor.id, text, reply_markup=markup)
            elif result == "need_link":
                await context.bot.send_message(
                    actor.id,
                    card("⚠️", "Invite Link Needed",
                         f"◈ <b>{esc(chat.title)}</b> me bot admin hai, par invite link nahi ban paya.",
                         "◈ Bot ko <b>Invite Users via Link</b> permission dein, ya /addchannel se link dein."),
                )
        except TelegramError as e:
            logger.warning("Auto-add DM failed: %s", e)
        return

    # ---- bot hata diya gaya / admin se utara gaya -------------------------
    lost = new_status in ("left", "kicked") or (
        old_status == "administrator" and new_status != "administrator"
    )
    if lost and is_force_channel(chat.id):
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    card("⚠️", "Bot Lost Access",
                         f"◈ <b>{esc(chat.title)}</b> me bot ka admin access chala gaya.",
                         "◈ Jab tak bot admin nahi hoga, is channel ka join-check kaam nahi karega.",
                         "◈ Bot ko dobara admin banayein."),
                )
            except TelegramError:
                pass


# =====================================================================
#  8) 📤 UPLOAD FILE
# =====================================================================
UP_FILE, UP_CAPTION = range(2, 4)


def extract_media(msg):
    """(tg_file_id, type, name) ya None."""
    if msg.animation:
        return msg.animation.file_id, "animation", msg.animation.file_name or "animation.mp4"
    if msg.document:
        return msg.document.file_id, "document", msg.document.file_name or "document"
    if msg.video:
        return msg.video.file_id, "video", msg.video.file_name or "video.mp4"
    if msg.photo:
        return msg.photo[-1].file_id, "photo", "photo.jpg"
    if msg.audio:
        return msg.audio.file_id, "audio", msg.audio.file_name or "audio.mp3"
    if msg.voice:
        return msg.voice.file_id, "voice", "voice.ogg"
    return None


async def upload_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.pop("upload_file", None)
    await reply(
        update, context,
        card(
            "📤", "Upload File",
            "◈ 📄 Document  •  🎬 Video  •  🖼️ Photo",
            "◈ 🎵 Audio  •  🎙️ Voice  •  🎞️ GIF",
            "",
            "Jo file share karni hai wo <b>abhi bhejein</b> 👇",
        ),
        cancel_kb(),
    )
    return UP_FILE


async def upload_file_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    media = extract_media(msg)
    if not media:
        await msg.reply_text(
            card("❌", "Unsupported", "◈ Sirf Document / Video / Photo / Audio / Voice / GIF bhejein."),
            reply_markup=cancel_kb(),
        )
        return UP_FILE

    tg_file_id, ftype, fname = media
    context.user_data["upload_file"] = {
        "tg_file_id": tg_file_id, "file_type": ftype, "file_name": fname,
    }
    await msg.reply_text(
        card(
            "✅", "File Received",
            f"◈ {FILE_ICONS.get(ftype, '📄')} <b>{esc(short(fname, 40))}</b>",
            "",
            "Ab <b>caption / title</b> bhejein ✍️",
            "ya neeche <b>Skip</b> dabayein.",
        ),
        reply_markup=kb([btn("⏭ Skip Caption", "skip_caption", style=BLUE),
                         btn("❌ Cancel", "cancel", style=RED)]),
    )
    return UP_CAPTION


async def _finalize_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, caption: str):
    data = context.user_data.pop("upload_file", None)
    if not data:
        await reply(update, context, card("⌛", "Session Expired", "◈ /upload dobara shuru karein."))
        return ConversationHandler.END

    file_db_id = save_file(
        tg_file_id=data["tg_file_id"],
        file_type=data["file_type"],
        file_name=data["file_name"],
        caption=caption,
        created_by=update.effective_user.id,
    )
    username = await get_bot_username(context)
    link = file_link(username, file_db_id)

    await reply(
        update, context,
        card(
            "🎉", "File Saved",
            f"◈ 🆔 File ID ➜ <code>{file_db_id}</code>",
            f"◈ {FILE_ICONS.get(data['file_type'], '📄')} {esc(short(data['file_name'], 40))}",
            "",
            "🔗 <b>Share link</b> (tap to copy):",
            f"<code>{link}</code>",
            footer="user link kholte hi pehle channels join karega, phir file milegi",
        ),
        kb(
            [btn("📤 Upload More", "adm:upload", style=GREEN),
             btn("📂 My Files", "adm:files", style=BLUE)],
            [btn("🛠 Admin Panel", "adm:home", style=BLUE)],
        ),
    )
    return ConversationHandler.END


async def upload_caption_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _finalize_upload(update, context, (update.effective_message.text or "").strip())


async def upload_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    return await _finalize_upload(update, context, "")


# =====================================================================
#  9) 📣 BROADCAST
# =====================================================================
BC_MSG, BC_CONFIRM = range(4, 6)


async def bcast_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard_admin(update):
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.pop("bc", None)
    await reply(
        update, context,
        card(
            "📣", "Broadcast",
            f"◈ Total users ➜ <b>{len(get_user_ids())}</b>",
            "",
            "Jo message sabko bhejna hai wo <b>abhi bhejein</b> "
            "(text / photo / video / kuch bhi) 👇",
        ),
        cancel_kb(),
    )
    return BC_MSG


async def bcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    context.user_data["bc"] = (msg.chat_id, msg.message_id)
    await msg.reply_text(
        card(
            "⚠️", "Confirm Broadcast",
            f"◈ Ye message <b>{len(get_user_ids())}</b> users ko jayega.",
            "◈ Pakka bhejna hai?",
        ),
        reply_markup=kb([btn("🚀 Yes, Send", "bc_yes", style=GREEN),
                         btn("❌ Cancel", "cancel", style=RED)]),
    )
    return BC_CONFIRM


async def bcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = context.user_data.pop("bc", None)
    if not data:
        await query.edit_message_text(card("⌛", "Session Expired", "◈ /broadcast dobara shuru karein."))
        return ConversationHandler.END

    await query.edit_message_text(
        card("🚀", "Broadcast Started",
             "◈ Background me bhej raha hoon...",
             "◈ Khatam hone par report milegi 📊")
    )
    context.application.create_task(run_broadcast(context.bot, update.effective_chat.id, data))
    return ConversationHandler.END


async def run_broadcast(bot, admin_chat: int, data: tuple) -> None:
    from_chat, message_id = data
    ok = failed = 0
    for uid in get_user_ids():
        for _attempt in range(2):
            try:
                await bot.copy_message(chat_id=uid, from_chat_id=from_chat, message_id=message_id)
                ok += 1
                break
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except (Forbidden, BadRequest):
                failed += 1
                break
            except TelegramError:
                failed += 1
                break
        await asyncio.sleep(0.05)

    try:
        await bot.send_message(
            admin_chat,
            card(
                "📊", "Broadcast Report",
                f"◈ ✅ Sent  ➜  <b>{ok}</b>",
                f"◈ ❌ Failed  ➜  <b>{failed}</b>",
                footer="failed = user ne bot block kiya ho sakta hai",
            ),
            reply_markup=home_kb(),
        )
    except TelegramError:
        pass


# =====================================================================
#  10) ❌ CANCEL / ERROR / STARTUP
# =====================================================================
async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ("pending_channel", "upload_file", "bc"):
        context.user_data.pop(key, None)
    if update.callback_query:
        await update.callback_query.answer("Cancelled")
    sent = await reply(
        update, context,
        card("❌", "Cancelled", "◈ Process cancel ho gaya."),
        ReplyKeyboardRemove(),
    )
    if is_admin(update.effective_user):
        try:
            await sent.edit_reply_markup(reply_markup=home_kb())
        except TelegramError:
            pass
    return ConversationHandler.END


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception", exc_info=context.error)


async def post_init(app: Application) -> None:
    me = await app.bot.get_me()
    app.bot_data["bot_username"] = me.username

    await app.bot.set_my_commands([
        BotCommand("start", "✨ Start / file link kholein"),
        BotCommand("id", "🆔 Meri Telegram ID"),
    ])

    admin_commands = [
        BotCommand("start", "✨ Start"),
        BotCommand("admin", "🛠 Admin panel"),
        BotCommand("addchannel", "➕ Channel add karein"),
        BotCommand("channels", "📢 Channels list"),
        BotCommand("upload", "📤 File upload"),
        BotCommand("files", "📂 Files list"),
        BotCommand("broadcast", "📣 Broadcast"),
        BotCommand("stats", "📊 Stats"),
        BotCommand("cancel", "❌ Cancel"),
    ]
    for admin_id in ADMIN_IDS:
        try:
            await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(admin_id))
        except TelegramError:
            pass  # admin ne abhi tak bot start nahi kiya

    logger.info("✦ Bot started as @%s", me.username)


def build_app() -> Application:
    defaults = Defaults(
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    app = Application.builder().token(BOT_TOKEN).defaults(defaults).post_init(post_init).build()

    admin_filter = filters.User(user_id=ADMIN_IDS)
    cancel_fallbacks = [
        CommandHandler("cancel", cancel_cmd),
        CallbackQueryHandler(cancel_cmd, pattern=r"^cancel$"),
    ]

    # ---- join request (auto-approve) + bot admin auto-detect ----------
    app.add_handler(ChatJoinRequestHandler(join_request_handler))
    app.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    # ---- conversations ------------------------------------------------
    app.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("addchannel", addch_entry, filters=admin_filter),
            CallbackQueryHandler(addch_entry, pattern=r"^adm:addch$"),
        ],
        states={
            AC_WAIT: [MessageHandler(filters.ALL & ~filters.COMMAND, addch_receive)],
            AC_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, addch_link_receive)],
        },
        fallbacks=cancel_fallbacks,
        allow_reentry=True,
    ))

    app.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("upload", upload_entry, filters=admin_filter),
            CallbackQueryHandler(upload_entry, pattern=r"^adm:upload$"),
        ],
        states={
            UP_FILE: [MessageHandler(filters.ALL & ~filters.COMMAND, upload_file_receive)],
            UP_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, upload_caption_receive),
                CommandHandler("skip", upload_skip),
                CallbackQueryHandler(upload_skip, pattern=r"^skip_caption$"),
            ],
        },
        fallbacks=cancel_fallbacks,
        allow_reentry=True,
    ))

    app.add_handler(ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", bcast_entry, filters=admin_filter),
            CallbackQueryHandler(bcast_entry, pattern=r"^adm:bcast$"),
        ],
        states={
            BC_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, bcast_receive)],
            BC_CONFIRM: [CallbackQueryHandler(bcast_confirm, pattern=r"^bc_yes$")],
        },
        fallbacks=cancel_fallbacks,
        allow_reentry=True,
    ))

    # ---- commands -----------------------------------------------------
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("channels", channels_cmd))
    app.add_handler(CommandHandler("files", files_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))

    # ---- buttons ------------------------------------------------------
    app.add_handler(CallbackQueryHandler(verify_cb, pattern=r"^verify:\d+$"))
    app.add_handler(CallbackQueryHandler(admin_nav_cb, pattern=r"^adm:(home|channels|files|stats)$"))
    app.add_handler(CallbackQueryHandler(delete_channel_cb, pattern=r"^del_ch:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_file_cb, pattern=r"^del_file:\d+$"))

    app.add_error_handler(on_error)
    return app


def main() -> None:
    if not BOT_TOKEN or "PASTE_YOUR_BOT_TOKEN" in BOT_TOKEN:
        raise SystemExit(
            "\n❌ BOT_TOKEN abhi placeholder hai.\n"
            "python.py kholkar upar BOT_TOKEN me BotFather ka token daalein.\n"
        )
    if not ADMIN_IDS or ADMIN_IDS == [123456789]:
        logger.warning("⚠️ ADMIN_IDS me example ID hai — apni real numeric ID daalein "
                       "(bot me /id bhejkar mil jayegi).")

    init_db()

    # Python 3.14+ me event loop khud nahi banta -> pehle bana do
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = build_app()
    logger.info("✦ Polling start...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
