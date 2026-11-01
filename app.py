#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import python as bot_core

STATIC_DIR = Path(__file__).resolve().parent / "static"

DASHBOARD_PASSWORD: str = (
    os.getenv(
        "DASHBOARD_PASSWORD",
        "FREE00000000GHGGHGHGHGH444555Kishan1122@8441",
    ).strip()
    or "FREE00000000GHGGHGHGHGH444555Kishan1122@8441"
)


def verify_dashboard_password(candidate: str | None) -> bool:
    if not candidate:
        return False
    return hmac.compare_digest(candidate.strip(), DASHBOARD_PASSWORD)


def build_full_state() -> dict[str, Any]:
    bot_uname = bot_core.BOT_RUNTIME_STATUS.get("bot_username") or "PremiumFileVaultBot"
    channels = [dict(r) for r in bot_core.get_channels()]
    files = []
    for r in bot_core.get_files(limit=50):
        item = dict(r)
        item["share_link"] = bot_core.file_link(bot_uname, item["id"])
        item["icon"] = bot_core.FILE_ICONS.get(item["file_type"], "📄")
        files.append(item)
    users = [dict(r) for r in bot_core.get_users(limit=50)]
    return {
        "config": bot_core.get_config_summary(),
        "stats": bot_core.get_stats(),
        "channels": channels,
        "files": files,
        "users": users,
    }


def handle_simulate(payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get("action") or "start")
    user_id = int(payload.get("user_id") or 123456789)
    first_name = str(payload.get("first_name") or "Admin")
    file_id_raw = payload.get("file_id")
    joined_ids = {
        int(x)
        for x in (payload.get("joined_channel_ids") or [])
        if str(x).lstrip("-").isdigit()
    }
    broadcast_text = str(payload.get("broadcast_text") or "")

    bot_core.save_user(user_id, first_name, first_name.lower().replace(" ", "_"))
    channels = bot_core.get_channels()
    status_list = [
        (ch, int(ch["id"]) in joined_ids or int(ch["chat_id"]) in joined_ids)
        for ch in channels
    ]
    pending = bot_core.pending_channels(status_list)
    is_adm = bot_core.is_admin(user_id)
    bot_uname = bot_core.BOT_RUNTIME_STATUS.get("bot_username") or "PremiumFileVaultBot"

    if action == "start":
        if is_adm:
            msg_html = bot_core.card(
                "🎁",
                f"Welcome to {bot_core.BOT_NAME}",
                f"👤 <b>{bot_core.esc(first_name)}</b>",
                "",
                "◈ Aap <b>admin</b> hain. Neeche se option chunein 👇",
                footer=bot_core.BOT_NAME,
            )
            buttons = [
                [
                    {"text": "➕ Add Channel", "action": "tab:channels"},
                    {"text": "📢 Channels", "action": "tab:channels"},
                ],
                [
                    {"text": "📤 Upload File", "action": "tab:files"},
                    {"text": "📂 My Files", "action": "tab:files"},
                ],
                [
                    {"text": "📣 Broadcast", "action": "sim:broadcast"},
                    {"text": "📊 Stats", "action": "sim:stats"},
                ],
            ]
        else:
            msg_html = bot_core.card(
                "🎁",
                f"Welcome to {bot_core.BOT_NAME}",
                f"👤 <b>{bot_core.esc(first_name)}</b>",
                "",
                "◈ File receive karne ke liye <b>share link</b> open karein.",
                footer=bot_core.BOT_NAME,
            )
            buttons = []
        return {
            "message_html": msg_html,
            "buttons": buttons,
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "stats":
        s = bot_core.get_stats()
        msg_html = bot_core.card(
            "📊",
            "Bot Statistics",
            f"📢 <b>Channels:</b>  {s['channels']}",
            f"📂 <b>Files:</b>  {s['files']}",
            f"👥 <b>Users:</b>  {s['users']}",
            f"⬇️ <b>Downloads:</b>  {s['downloads']}",
            f"⏳ <b>Pending Verifications:</b>  {s['pending']}",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [[{"text": "🛠 Back to Admin Panel", "action": "sim:start"}]],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action in ("deep_link", "verify"):
        files = bot_core.get_files(limit=10)
        target_id = (
            int(file_id_raw) if file_id_raw else (int(files[0]["id"]) if files else 0)
        )
        row = bot_core.get_file(target_id)
        if not row:
            msg_html = bot_core.card(
                "❌",
                "File Not Found",
                "◈ File delete ho chuki hai ya abhi koi file upload nahi hui.",
            )
            return {
                "message_html": msg_html,
                "buttons": [],
                "delivered_file": None,
                "state": build_full_state(),
            }

        bot_core.save_pending(user_id, target_id)
        if pending:
            msg_html = bot_core.force_sub_text(status_list)
            buttons = [
                [
                    {
                        "text": f"📢 Join • {bot_core.short(ch['title'], 26)}",
                        "action": f"join:{ch['id']}",
                    }
                ]
                for ch in pending
            ]
            buttons.append(
                [{"text": "✅ Verify & Get File", "action": f"verify:{target_id}"}]
            )
            return {
                "message_html": msg_html,
                "buttons": buttons,
                "delivered_file": None,
                "state": build_full_state(),
            }

        bot_core.add_download(target_id)
        bot_core.delete_pending(user_id)
        updated_row = dict(bot_core.get_file(target_id))
        updated_row["share_link"] = bot_core.file_link(bot_uname, target_id)
        updated_row["caption_html"] = bot_core.build_caption(updated_row)
        msg_html = bot_core.card(
            "✅",
            "Verified & Delivered!",
            "◈ Sab required channels joined hain.",
            f"📤 <b>{bot_core.esc(updated_row['file_name'] or f'File #{target_id}')}</b> bhej di gayi hai!",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [],
            "delivered_file": updated_row,
            "state": build_full_state(),
        }

    if action == "broadcast":
        user_ids = bot_core.get_user_ids()
        msg_html = bot_core.card(
            "✅",
            "Broadcast Complete",
            f"💬 <b>Message:</b> {bot_core.esc(broadcast_text or 'New file uploaded to Premium File Vault!')}",
            f"✅ <b>Sent:</b> {len(user_ids)}",
            "❌ <b>Failed:</b> 0",
            f"👥 <b>Total:</b> {len(user_ids)}",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [[{"text": "🛠 Admin Panel", "action": "sim:start"}]],
            "delivered_file": None,
            "state": build_full_state(),
        }

    raise ValueError(f"Unknown action: {action}")


FALLBACK_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Premium File Vault — Protected Control Center</title>
  <style>
    body { margin:0; font-family: system-ui, -apple-system, sans-serif; background:#070b14; color:#f8fafc; display:flex; align-items:center; justify-content:center; min-height:100vh; }
    .card { background:#0f172a; border:1px solid rgba(56,189,248,0.28); border-radius:18px; padding:32px; width:100%; max-width:420px; box-shadow:0 24px 60px rgba(0,0,0,0.65); text-align:center; }
    h1 { margin:0 0 8px; font-size:22px; }
    p { margin:0 0 20px; color:#94a3b8; font-size:14px; }
    input { width:100%; box-sizing:border-box; padding:12px 14px; border-radius:10px; border:1px solid #334155; background:#090d16; color:#fff; font-size:14px; margin-bottom:12px; }
    button { width:100%; padding:12px; border-radius:10px; border:none; background:linear-gradient(135deg,#38bdf8,#0284c7); color:#04101d; font-weight:700; cursor:pointer; font-size:14px; }
    .err { color:#f43f5e; font-size:13px; margin-bottom:10px; display:none; }
    .dash { display:none; text-align:left; margin-top:16px; border-top:1px solid #1e293b; padding-top:16px; font-size:13px; color:#cbd5e1; }
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size:36px;margin-bottom:10px;">🔐</div>
    <h1>Premium File Vault</h1>
    <p>Enter Vault Master Password to unlock Control Center</p>
    <div id="err" class="err">❌ Galat password! Sahi Vault Password daalein.</div>
    <div id="form">
      <input id="pw" type="password" placeholder="Enter Vault Master Password..." />
      <button onclick="unlock()">🔓 Unlock Control Center</button>
    </div>
    <div id="dash" class="dash"></div>
  </div>
  <script>
    async function unlock() {
      const pw = document.getElementById('pw').value.trim();
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password: pw})
      });
      const data = await res.json();
      if (!res.ok || !data.authenticated) {
        document.getElementById('err').style.display = 'block';
        return;
      }
      document.getElementById('err').style.display = 'none';
      document.getElementById('form').style.display = 'none';
      const d = document.getElementById('dash');
      d.style.display = 'block';
      d.innerHTML = '<b>✅ Vault Unlocked</b><br><br>' +
        '<b>Bot Name:</b> ' + (data.state?.config?.bot_name || '') + '<br>' +
        '<b>Database:</b> ' + (data.state?.config?.db_path || 'bot_data.db') + '<br>' +
        '<b>Channels:</b> ' + (data.state?.stats?.channels ?? 0) + ' | <b>Files:</b> ' + (data.state?.stats?.files ?? 0) + ' | <b>Users:</b> ' + (data.state?.stats?.users ?? 0);
    }
  </script>
</body>
</html>
"""


class VaultHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class VaultRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, content: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(content)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _is_authorized(self) -> bool:
        header_pw = self.headers.get("X-Vault-Password", "")
        return verify_dashboard_password(header_pw)

    def do_HEAD(self) -> None:
        """
        Render's port detector & load-balancer readiness probe sends HTTP HEAD /
        requests. Always respond 200 OK immediately so deploys succeed in <2s.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Allow", "GET, HEAD, POST, DELETE, OPTIONS")
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # Public health check endpoints for Render & uptime monitors (no password)
        if path in (
            "/api/health",
            "/health",
            "/healthz",
            "/ping",
            "/status",
            "/ready",
            "/live",
        ):
            self._send_json(
                {
                    "status": "ok",
                    "bot_name": bot_core.BOT_NAME,
                    "db_path": bot_core.DB_PATH,
                    "stats": bot_core.get_stats(),
                    "runtime": bot_core.BOT_RUNTIME_STATUS,
                }
            )
            return

        if path == "/api/state":
            if not self._is_authorized():
                self._send_json(
                    {"detail": "Unauthorized — Vault Password required"}, status=401
                )
                return
            self._send_json(build_full_state())
            return

        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            target = (STATIC_DIR / rel).resolve()
            if str(target).startswith(str(STATIC_DIR)) and target.is_file():
                ctype, _ = mimetypes.guess_type(str(target))
                content = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(content)
                return
            self._send_json({"detail": "Static asset not found"}, status=404)
            return

        if path.startswith("/api/"):
            self._send_json({"detail": "Not found"}, status=404)
            return

        # Serve index.html (or built-in fallback HTML if static/ folder wasn't deployed) with 200 OK
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            self._send_html(index_file.read_bytes(), status=200)
        else:
            self._send_html(FALLBACK_INDEX_HTML.encode("utf-8"), status=200)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json()
        except Exception:
            self._send_json({"detail": "Invalid JSON payload"}, status=400)
            return

        # 1. Telegram Webhook Receiver (for Render Web Services — Zero Conflict, No Password!)
        if path == "/telegram-webhook":
            ptb_app, bot_loop = bot_core.get_active_bot_app()
            if ptb_app is not None and bot_loop is not None:
                try:
                    update_obj = bot_core.Update.de_json(body, ptb_app.bot)
                    if update_obj is not None:
                        asyncio.run_coroutine_threadsafe(
                            ptb_app.update_queue.put(update_obj), bot_loop
                        )
                except Exception as e:
                    bot_core.logger.warning("Webhook update error: %s", e)
            self._send_json({"ok": True})
            return

        # 2. Website Password Login Endpoint
        if path == "/api/login":
            pw = str(body.get("password") or "")
            if verify_dashboard_password(pw):
                self._send_json({"authenticated": True, "state": build_full_state()})
            else:
                self._send_json(
                    {
                        "authenticated": False,
                        "detail": "❌ Galat password! Sahi Vault Password daalein.",
                    },
                    status=401,
                )
            return

        # All other /api/* endpoints require website password authentication
        if not self._is_authorized():
            self._send_json(
                {"detail": "Unauthorized — Vault Password required"}, status=401
            )
            return

        if path == "/api/config":
            admin_ids_raw = body.get("admin_ids")
            bot_name_raw = body.get("bot_name")
            if admin_ids_raw is not None and not bot_core.parse_admin_ids(
                admin_ids_raw
            ):
                self._send_json(
                    {
                        "detail": "ADMIN_IDS me kam se kam ek numeric Telegram ID honi chahiye (e.g. 123456789)."
                    },
                    status=400,
                )
                return
            if bot_name_raw is not None and not str(bot_name_raw).strip():
                self._send_json(
                    {"detail": "BOT_NAME khali nahi ho sakta."}, status=400
                )
                return

            bot_core.save_env_config(
                bot_token=body.get("bot_token"),
                admin_ids=admin_ids_raw,
                bot_name=bot_name_raw,
                db_path=body.get("db_path"),
            )
            self._send_json(build_full_state())
            return

        if path == "/api/channels":
            title = str(body.get("title") or "").strip()
            invite = str(body.get("invite_link") or "").strip()
            username = str(body.get("username") or "").strip()
            try:
                chat_id = int(body.get("chat_id"))
            except (TypeError, ValueError):
                self._send_json(
                    {"detail": "Valid numeric Chat ID zaroori hai."}, status=400
                )
                return

            if not title:
                self._send_json({"detail": "Channel title zaroori hai."}, status=400)
                return
            if not invite.startswith(("https://t.me/", "http://t.me/", "tg://")):
                self._send_json(
                    {"detail": "Invite link https://t.me/... se shuru hona chahiye."},
                    status=400,
                )
                return

            bot_core.save_channel(chat_id, title, username, invite)
            self._send_json(build_full_state())
            return

        if path == "/api/files":
            fname = str(body.get("file_name") or "").strip()
            ftype = str(body.get("file_type") or "document").strip()
            caption = str(body.get("caption") or "").strip()
            tg_id = str(body.get("tg_file_id") or "").strip()
            if not fname:
                self._send_json({"detail": "File name zaroori hai."}, status=400)
                return
            if not tg_id:
                tg_id = f"BQACAgUAAxkBAAI_{fname[:16].replace(' ', '_')}"
            admin_id = bot_core.ADMIN_IDS[0] if bot_core.ADMIN_IDS else 123456789
            new_id = bot_core.save_file(tg_id, ftype, fname, caption, admin_id)
            state = build_full_state()
            state["created_file_id"] = new_id
            self._send_json(state)
            return

        if path == "/api/simulate":
            try:
                result = handle_simulate(body)
                self._send_json(result)
            except Exception as e:
                self._send_json({"detail": str(e)}, status=400)
            return

        self._send_json({"detail": "Not found"}, status=404)

    def do_DELETE(self) -> None:
        if not self._is_authorized():
            self._send_json(
                {"detail": "Unauthorized — Vault Password required"}, status=401
            )
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/channels/"):
            try:
                cid = int(path.split("/")[-1])
                bot_core.delete_channel(cid)
                self._send_json(build_full_state())
                return
            except ValueError:
                self._send_json({"detail": "Invalid channel ID"}, status=400)
                return

        if path.startswith("/api/files/"):
            try:
                fid = int(path.split("/")[-1])
                bot_core.delete_file(fid)
                self._send_json(build_full_state())
                return
            except ValueError:
                self._send_json({"detail": "Invalid file ID"}, status=400)
                return

        self._send_json({"detail": "Not found"}, status=404)


def create_control_center_server(
    port: int = 3000, acquire_lock: bool = False
) -> VaultHTTPServer:
    bot_core.init_db()
    bot_core.seed_demo_data_if_empty()
    if acquire_lock:
        bot_core.acquire_single_instance_lock()
    server = VaultHTTPServer(("0.0.0.0", port), VaultRequestHandler)
    bot_core.logger.info(
        "🌐 Premium File Vault Control Center (Password Protected) listening on http://0.0.0.0:%d",
        port,
    )
    return server


def run_control_center_server(port: int = 3000, acquire_lock: bool = False) -> None:
    server = create_control_center_server(port=port, acquire_lock=acquire_lock)
    server.serve_forever(poll_interval=0.1)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    run_control_center_server(port=port, acquire_lock=True)
