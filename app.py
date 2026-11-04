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
        "SJEIDB@@@1272737SJWHSH2727",
    ).strip()
    or "SJEIDB@@@1272737SJWHSH2727"
)


def verify_dashboard_password(candidate: str | None) -> bool:
    if not candidate:
        return False
    return hmac.compare_digest(candidate.strip(), DASHBOARD_PASSWORD)


def build_full_state() -> dict[str, Any]:
    bot_uname = (
        bot_core.BOT_RUNTIME_STATUS.get("bot_username") or "FILE_SHARE_00_bot"
    )
    channels = [dict(r) for r in bot_core.get_channels()]
    files = []
    for r in bot_core.get_files(limit=60):
        item = dict(r)
        item["share_link"] = bot_core.file_link(bot_uname, item)
        item["safe_link"] = bot_core.file_tg_safe_link(bot_uname, item)
        item["icon"] = bot_core.FILE_ICONS.get(item["file_type"], "📄")
        item["uploader_role"] = item.get("uploader_role") or "admin"
        item["is_permanent"] = item["uploader_role"] != "user"
        files.append(item)
    users = [dict(r) for r in bot_core.get_users(limit=50)]
    managed_groups = [dict(r) for r in bot_core.get_managed_groups()]
    return {
        "config": bot_core.get_config_summary(),
        "stats": bot_core.get_stats(),
        "channels": channels,
        "files": files,
        "users": users,
        "group_banner": bot_core.get_group_banner_config(),
        "managed_groups": managed_groups,
        "bot_builder": bot_core.get_bot_builder_config(),
        "user_bots": bot_core.get_user_bots(),
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
    bot_uname = (
        bot_core.BOT_RUNTIME_STATUS.get("bot_username") or "FILE_SHARE_00_bot"
    )

    if action == "start":
        s = bot_core.get_stats()
        bcfg = bot_core.get_bot_builder_config()
        user_bots = bot_core.get_user_bots()
        first_ub = user_bots[0] if user_bots else None
        has_pro = bot_core.is_user_pro(user_id)
        if is_adm and not payload.get("force_user_view"):
            used_by = int(bcfg.get("pro_key_used_by") or 0)
            link_badge = "🟢 Ready (Single-Use)" if used_by == 0 else f"🔴 Used by {used_by}"
            msg_html = bot_core.card(
                "⚡",
                f"VIP Control Panel • {bot_core.BOT_NAME}",
                f"👑 <b>Admin:</b> {bot_core.esc(first_name)} (Lifetime Storage Forever)",
                "🟢 <b>Status:</b> 24/7 Live · Instant &lt;1s Fast Response",
                f"🦄 <b>/BOT-build Cloned Bots:</b> {s.get('user_bots', 0)} Online (Free: 2+2 · Pro: 4 Own Channels)",
                f"💎 <b>Pro Users:</b> {s.get('pro_users', 0)}   |   🔗 <b>Pro Link:</b> {link_badge}",
                f"🛒 <b>Store Bot:</b> @{bot_core.PRO_STORE_BOT_USERNAME}",
                f"📂 <b>Permanent Vault:</b> {s['files']}   |   ⏳ <b>User 7d Uploads:</b> {s.get('user_uploads', 0)}",
                f"👥 <b>15m Ad Groups:</b> {s['groups']}   |   📢 <b>Channels:</b> {s['channels']}",
                "",
                "◈ Neeche ke <b>Real Colorful Buttons</b> chunein 👇",
                footer=bot_core.BOT_NAME,
            )
            buttons = [
                [
                    {
                        "text": "🎛️ ⚙️ Customize /start & Pro Link",
                        "action": "tab:botbuild",
                        "color": "gold",
                    },
                    {
                        "text": "💎 🔑 /Pro-plan Preview",
                        "action": "sim:pro_plan",
                        "color": "gold",
                    },
                ],
                [
                    {
                        "text": "🟢 📤 Upload File / Link (Lifetime)",
                        "action": "tab:files",
                        "color": "success",
                    },
                    {
                        "text": "🟣 📸 /group-upload",
                        "action": "sim:group_upload",
                        "color": "purple",
                    },
                ],
                [
                    {
                        "text": "🦄 🤖 /BOT-build (User Builder)",
                        "action": "sim:bot_build",
                        "color": "purple",
                    },
                    {
                        "text": "✨ 📝 /BOT-build-description",
                        "action": "tab:botbuild",
                        "color": "gold",
                    },
                ],
                [
                    {
                        "text": "🩷 🖼️ /Group-image-description",
                        "action": "sim:group_banner",
                        "color": "pink",
                    },
                    {
                        "text": "🩵 👥 /ad-group (15m Loop)",
                        "action": "sim:ad_group",
                        "color": "cyan",
                    },
                ],
                [
                    {
                        "text": "🟠 📤 /user-upload",
                        "action": "sim:user_upload",
                        "color": "amber",
                    },
                    {
                        "text": f"🦄 🏠 {first_ub['bot_name'] if first_ub else 'User Bot Home'}",
                        "action": "sim:user_bot_home",
                        "color": "primary",
                    },
                ],
                [
                    {
                        "text": "🦄 🔗 Test Pro Link Click (Activate VIP)",
                        "action": "sim:pro_link_activate",
                        "color": "gold",
                    },
                    {
                        "text": "💎 📊 Live Fast Stats",
                        "action": "sim:stats",
                        "color": "primary",
                    },
                ],
            ]
        else:
            feature_bullets = []
            buttons = []
            if bcfg.get("allow_bot_build", True):
                ch_rule = (
                    "4 Aapke Channels (Admin Channels Removed!)"
                    if has_pro
                    else "2 Admin + 2 Aapke Channels"
                )
                feature_bullets.append(
                    f"• <code>/BOT-build</code> — 🦄 Apna khud ka 24/7 Bot banayein ({ch_rule})."
                )
                buttons.append(
                    [
                        {
                            "text": "🦄 🤖 /BOT-build (Create Your 24/7 Bot)",
                            "action": "sim:bot_build",
                            "color": "purple",
                        }
                    ]
                )
                if first_ub and bcfg.get("allow_user_two_channels", True):
                    max_c = 4 if has_pro else 2
                    buttons.append(
                        [
                            {
                                "text": f"🟣 🏠 {first_ub['bot_name']} (Home)",
                                "action": "sim:user_bot_home",
                                "color": "purple",
                            },
                            {
                                "text": f"🟠 ➕ Add {max_c} Channels",
                                "action": "tab:botbuild",
                                "color": "amber",
                            },
                        ]
                    )
            if bcfg.get("allow_user_upload", True):
                if has_pro:
                    feature_bullets.append(
                        "• <code>/user-upload</code> — 👑 <b>VIP Pro Active:</b> Unlimited Lifetime Permanent File &amp; Link Upload!"
                    )
                    buttons.append(
                        [
                            {
                                "text": "🟢 📤 /user-upload (♾️ Lifetime Unlimited)",
                                "action": "sim:user_upload",
                                "color": "success",
                            }
                        ]
                    )
                else:
                    days = bcfg.get("user_file_expiry_days", 7)
                    feature_bullets.append(
                        f"• <code>/user-upload</code> — 📤 Apna File/Link upload karein (⚠️ Free user: {days} Days auto-delete)."
                    )
                    buttons.append(
                        [
                            {
                                "text": f"🟢 📤 /user-upload ({days}-Day Validity)",
                                "action": "sim:user_upload",
                                "color": "success",
                            }
                        ]
                    )
            if bcfg.get("allow_pro_plan", True):
                if has_pro:
                    feature_bullets.append(
                        "• <code>/Pro-plan</code> — 👑 <b>YOUR PRO PLAN ACTIVE!</b> (Lifetime Upload + 4 Channels Unlocked)."
                    )
                    buttons.append(
                        [
                            {
                                "text": "👑 💎 /Pro-plan Status (Active • 4 Channels)",
                                "action": "sim:pro_plan",
                                "color": "gold",
                            }
                        ]
                    )
                else:
                    feature_bullets.append(
                        f"• <code>/Pro-plan</code> — 🔑 Secret Key daal kar <b>Lifetime Upload + 4 Channels</b> unlock karein (Buy Key: @{bot_core.PRO_STORE_BOT_USERNAME})!"
                    )
                    buttons.append(
                        [
                            {
                                "text": "💎 🔑 /Pro-plan (Unlock Lifetime + 4 Channels)",
                                "action": "sim:pro_plan",
                                "color": "gold",
                            }
                        ]
                    )
                    buttons.append(
                        [
                            {
                                "text": f"🛒 💎 Buy Pro Key (@{bot_core.PRO_STORE_BOT_USERNAME})",
                                "action": "url:https://t.me/Krishna_Zx_Store_bot",
                                "color": "amber",
                            }
                        ]
                    )
            plan_badge = (
                "👑 <b>Plan Status:</b> YOUR PRO PLAN ACTIVE (♾️ Lifetime Upload + 4 Own Channels)"
                if has_pro
                else f"⏳ <b>Plan Status:</b> Free Plan (7-Day Upload · 2+2 Channels · Buy Pro: @{bot_core.PRO_STORE_BOT_USERNAME})"
            )
            welcome_line = bcfg.get("start_welcome_text") or bot_core.DEFAULT_START_WELCOME_TEXT
            msg_html = bot_core.card(
                "🦄",
                f"Welcome to {bot_core.BOT_NAME}",
                f"👤 <b>Hello {bot_core.esc(first_name)}!</b>",
                f"✨ <b>{bot_core.esc(welcome_line)}</b>",
                plan_badge,
                "",
                "🌈 <b>Available Features on /start (Configured by Admin):</b>",
                *(feature_bullets or ["• ⚡ Share links par click karke instant files unlock karein!"]),
                footer=bot_core.BOT_NAME,
            )
        return {
            "message_html": msg_html,
            "buttons": buttons,
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "stats":
        s = bot_core.get_stats()
        cfg = bot_core.get_group_banner_config()
        msg_html = bot_core.card(
            "📊",
            "24/7 Live Bot Statistics",
            f"📢 <b>Channels:</b>  {s['channels']}",
            f"📂 <b>Permanent Vault Items:</b>  {s['files']}",
            f"🌐 <b>Direct Links:</b>  {s['links']}",
            f"📸 <b>Group Uploads (/group-upload):</b>  {s['group_uploads']}",
            f"👥 <b>15m Auto-Banner Groups (/ad-group):</b>  {s['groups']}",
            f"🖼️ <b>Banner Verified:</b>  {'✅ Yes' if cfg['verified'] else '❌ No'}",
            f"👤 <b>Users:</b>  {s['users']}",
            f"⬇️ <b>Downloads:</b>  {s['downloads']}",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🟢 🔄 Refresh Stats",
                        "action": "sim:stats",
                        "color": "success",
                    },
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    },
                ]
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "group_banner":
        cfg = bot_core.get_group_banner_config()
        msg_html = bot_core.card(
            "🖼️",
            "/Group-image-description Verified",
            "📸 <b>Step 1 (Image):</b> Uploaded &amp; Permanently Saved",
            f"📝 <b>Step 2 (Description):</b> {bot_core.esc(cfg.get('description') or 'Official Group & Channel Banner')}",
            "✅ <b>Verification Status:</b> 100% Verified!",
            "",
            "🔄 <b>Group &amp; Channel Behavior:</b> Jab aap <code>/ad-group</code> se bot ko kisi <b>Group ya Channel</b> me jodeinge, "
            "jaise hi jayega <b>pehle turant post kar dega</b>, fir pura <b>15 Minute</b> post rahega (2 minute nahi, 15 minute!), "
            "uske baad purana delete karke naya post bhejega!",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🩵 👥 Activate in Group/Channel (/ad-group)",
                        "action": "sim:ad_group",
                        "color": "cyan",
                    },
                    {
                        "text": "🩷 ⚙️ Edit in Group Banner Tab",
                        "action": "tab:groups",
                        "color": "pink",
                    },
                ],
                [
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    }
                ],
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "ad_group":
        groups = bot_core.get_managed_groups()
        cfg = bot_core.get_group_banner_config()
        if groups:
            g = dict(groups[0])
            bot_core.update_managed_group_post_state(
                int(g["id"]), (int(g.get("last_message_id") or 100) + 1)
            )
            g = dict(bot_core.get_managed_group_by_id(int(g["id"])))
            grp_title = g["title"]
            rotations = g["send_count"]
        else:
            grp_title = "VIP File Share Group & Channel"
            rotations = 1

        msg_html = bot_core.card(
            "👥",
            "/ad-group • Group & Channel 15-Minute Auto Banner",
            "👑 <b>Added By:</b> Admin Only (Works in Group &amp; Channel Both!)",
            f"📢 <b>Active Group/Channel:</b> {bot_core.esc(grp_title)}",
            f"🖼️ <b>Banner Description:</b> {bot_core.esc(cfg.get('description') or 'VIP Vault Banner')}",
            "🚀 <b>First Action:</b> Jaise hi jodenge, turant pehle Banner + Description post karega!",
            "⏱️ <b>Stay Time:</b> Strictly <b>15 Minutes</b> (2 minute nahi, pura 15 minute post rahega!)",
            f"🔄 <b>15m Rotations Sent:</b> #{rotations} (After 15m: Old Deleted ➜ Fresh Post Sent!)",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🟢 🔄 Simulate Next 15m Rotation",
                        "action": "sim:ad_group",
                        "color": "success",
                    },
                    {
                        "text": "🩵 👥 Manage Groups Tab",
                        "action": "tab:groups",
                        "color": "cyan",
                    },
                ],
                [
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    }
                ],
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "group_upload":
        files = bot_core.get_files(limit=30)
        grp_file = next(
            (dict(f) for f in files if dict(f).get("group_name")),
            dict(files[0]) if files else None,
        )
        if grp_file:
            link = bot_core.file_link(bot_uname, grp_file)
            gname = grp_file.get("group_name") or "VIPGroup"
            cname = grp_file.get("custom_name") or "Poster4K"
            rcode = grp_file.get("random_code") or "739204"
        else:
            gname, cname, rcode = "VIPGroup", "Poster4K", "739204"
            link = f"https://t.me/{bot_uname}?start={gname}?{cname}={rcode}"

        msg_html = bot_core.card(
            "📸",
            "/group-upload • Permanent Link Generated",
            f"👥 <b>Group Name:</b> <code>{bot_core.esc(gname)}</code>",
            f"🏷️ <b>Image/File Name:</b> <code>{bot_core.esc(cname)}</code>",
            f"🔢 <b>4-6 Digit Code:</b> <code>{bot_core.esc(rcode)}</code>",
            "♾️ <b>Permanent Vault:</b> Kabhi auto-delete nahi hoga (Admin delete only)",
            "",
            "🔗 <b>Generated Group Upload Link:</b>",
            f"<code>{bot_core.esc(link)}</code>",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🟣 🚀 Test Opening This Link",
                        "action": f"verify:{grp_file['id'] if grp_file else 1}",
                        "color": "purple",
                    },
                    {
                        "text": "🟢 📸 Upload New in Vault Tab",
                        "action": "tab:files",
                        "color": "success",
                    },
                ],
                [
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    }
                ],
            ],
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
            palette = ["primary", "purple", "amber", "cyan", "pink", "gold"]
            emojis = ["🔵", "🟣", "🟠", "🩵", "🩷", "🟡"]
            buttons = [
                [
                    {
                        "text": f"{emojis[i % 6]} 📢 Join • {bot_core.short(ch['title'], 24)}",
                        "action": f"join:{ch['id']}",
                        "color": palette[i % len(palette)],
                    }
                ]
                for i, ch in enumerate(pending)
            ]
            buttons.append(
                [
                    {
                        "text": "🟢 ✅ Verify & Unlock Instantly (<1s)",
                        "action": f"verify:{target_id}",
                        "color": "success",
                    }
                ]
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
        updated_row["share_link"] = bot_core.file_link(bot_uname, updated_row)
        updated_row["safe_link"] = bot_core.file_tg_safe_link(bot_uname, updated_row)
        updated_row["caption_html"] = bot_core.build_caption(updated_row)
        is_link_type = updated_row.get("file_type") == "link" or bool(
            updated_row.get("external_url")
        )
        msg_html = bot_core.card(
            "🌐" if is_link_type else "✅",
            "Instant <1s Delivered (Permanent Vault)!",
            f"🏷️ <b>Name:</b> <code>{bot_core.esc(updated_row.get('custom_name') or updated_row.get('file_name'))}</code>",
            f"🔢 <b>4-6 Digit Code:</b> <code>{bot_core.esc(updated_row.get('random_code') or target_id)}</code>",
            f"🔗 <b>Link:</b> <code>{bot_core.esc(updated_row['share_link'])}</code>",
            "♾️ <b>Permanent Status:</b> Saved Forever (Until Admin Deletes)",
            footer=bot_core.BOT_NAME,
        )
        sim_btns = [
            [
                {
                    "text": "🔵 🛠 Back to VIP Admin Panel",
                    "action": "sim:start",
                    "color": "primary",
                }
            ]
        ]
        return {
            "message_html": msg_html,
            "buttons": sim_btns,
            "delivered_file": updated_row,
            "state": build_full_state(),
        }

    if action == "broadcast":
        user_ids = bot_core.get_user_ids()
        msg_html = bot_core.card(
            "✅",
            "Broadcast Complete",
            f"💬 <b>Message:</b> {bot_core.esc(broadcast_text or 'New file & link uploaded to Premium File Vault!')}",
            f"✅ <b>Sent:</b> {len(user_ids)}",
            "❌ <b>Failed:</b> 0",
            f"👥 <b>Total:</b> {len(user_ids)}",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    }
                ]
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "bot_build":
        cfg = bot_core.get_bot_builder_config()
        msg_html = bot_core.card(
            "🦄",
            "/BOT-build • Unicorn Premium Bot Builder",
            "✨ <b>Kya aap apna khud ka 24/7 Fast Bot create karna chahte hain?</b>",
            "",
            f"<blockquote>{bot_core.esc(cfg.get('description') or bot_core.DEFAULT_BOT_BUILD_DESCRIPTION)}</blockquote>",
            "",
            "🟢 <b>Features You Get:</b>",
            "  • ⚡ <b>24/7 Online &amp; &lt;1s Instant Start Reply</b>",
            "  • 📢 <b>2 Apne Channels + 2 Hamare (Admin) Force-Join Channels</b>",
            "  • 📤 <b>/user-upload</b> (⚠️ 1 Hafta / 7 Days Auto-Expiry)",
            "",
            "👇 Apna bot banane ke liye neeche <b>Continue</b> par click karein:",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🟢 🦄 Continue to Build Bot 👉",
                        "action": "sim:bot_build_continue",
                        "color": "success",
                    }
                ],
                [
                    {
                        "text": "✨ 📝 Edit /BOT-build-description (Admin)",
                        "action": "tab:botbuild",
                        "color": "gold",
                    },
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    },
                ],
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "bot_build_continue":
        msg_html = bot_core.card(
            "🦄",
            "Enter @BotFather Token • Unicorn Premium Setup",
            "✨ <b>Step 2 of 2 • Instant Bot Verification</b>",
            "",
            "🦄 👇 <b>Bot Token daalein <code>@BotFather</code> se lekar:</b>",
            "<code>7123456789:AAH_your_botfather_token_here</code>",
            "",
            "⚡ Token daalte hi aapka bot <b>1 second me verify</b> hokar <b>24/7 Online</b> ho jayega aur aapke Home Screen par aapke Bot ka naam aa jayega!",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🦄 ✅ Verify Token & Open My Bot Home Screen",
                        "action": "sim:user_bot_home",
                        "color": "purple",
                    }
                ],
                [
                    {
                        "text": "🟣 ⚙️ Open /BOT-build Tab in Panel",
                        "action": "tab:botbuild",
                        "color": "pink",
                    },
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    },
                ],
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "user_bot_home":
        user_bots = bot_core.get_user_bots()
        ub = user_bots[0] if user_bots else {
            "id": 1,
            "owner_user_id": user_id,
            "bot_name": "🦄 Rahul VIP File Bot",
            "bot_username": "RahulVIPFile_bot",
            "channel_1_title": "Rahul Main Channel",
            "channel_1_link": "https://t.me/RahulMainChannel",
            "channel_2_title": "Rahul Backup Channel",
            "channel_2_link": "https://t.me/RahulBackupChannel",
            "channel_3_title": "",
            "channel_3_link": "",
            "channel_4_title": "",
            "channel_4_link": "",
        }
        has_pro = bot_core.is_user_pro(user_id) or bool(ub.get("owner_is_pro"))
        combined = bot_core.get_combined_force_channels_for_user_bot(int(ub.get("id") or 1))
        ch_lines = [
            f"  • 📢 <b>{bot_core.esc(c['slot'])}:</b> {bot_core.esc(c['title'])}"
            for c in combined
        ]
        rule_title = (
            "📢 <b>Force-Join Rule (👑 Pro Mode: 0 Admin + 4 Your Channels):</b>"
            if has_pro
            else "📢 <b>Force-Join Rule (2 Admin + 2 User Channels):</b>"
        )
        msg_html = bot_core.card(
            "🦄",
            f"Home Screen • {ub.get('bot_name')}",
            f"🤖 <b>Bot Username:</b> @{bot_core.esc(ub.get('bot_username'))}",
            "🟢 <b>Status:</b> 24/7 Online &amp; Active (&lt;1s Fast Start)",
            f"👑 <b>Owner Plan:</b> {'YOUR PRO PLAN ACTIVE (Admin Channels Removed!)' if has_pro else 'Free Plan (2 Admin + 2 User Channels)'}",
            "",
            rule_title,
            *ch_lines,
            "",
            "✨ <b>Allowed User Features:</b>",
            f"  • ➕ <b>{'Add 4 Own Channels (Admin 2 Removed!)' if has_pro else 'Add Channel (Max 2 Channels)'}</b>",
            "  • 📤 <b>/user-upload</b> (Free: 7 Days · 💎 /Pro-plan: Lifetime)",
            footer=ub.get("bot_name") or bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🟣 ➕ Add 4 Channels (Pro Unlocked)" if has_pro else "🟠 ➕ Add Channel (Max 2)",
                        "action": "tab:botbuild",
                        "color": "purple" if has_pro else "amber",
                    },
                    {
                        "text": "🟢 📤 /user-upload",
                        "action": "sim:user_upload",
                        "color": "success",
                    },
                ],
                [
                    {
                        "text": "👑 💎 /Pro-plan Active (VIP)" if has_pro else "💎 🔑 /Pro-plan (Unlock 4 Channels + Lifetime)",
                        "action": "sim:pro_plan",
                        "color": "gold",
                    },
                    {
                        "text": "🔵 🛠 Back to Main Bot",
                        "action": "sim:start",
                        "color": "primary",
                    },
                ],
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "user_upload":
        has_pro = bot_core.is_user_pro(user_id)
        if has_pro:
            msg_html = bot_core.card(
                "👑",
                "/user-upload • VIP Pro Lifetime Unlimited Vault",
                "🦄✨💎 <b>YOUR PRO PLAN ACTIVE!</b> 💎✨🦄",
                "",
                "♾️ <b>Lifetime Permanent Storage:</b>",
                "<blockquote>Aapki upload ki gayi har File, Image, Video ya Direct Link <b>LIFETIME</b> ke liye permanent save rahegi — kabhi auto-delete nahi hogi!</blockquote>",
                "",
                "📢 <b>Pro 4-Channel Force-Join:</b> Aapke bot par Admin ke 2 Channels hata diye gaye hain — sirf aapke <b>4 Force-Join Channels</b> dikhenge!",
                footer=bot_core.BOT_NAME,
            )
        else:
            msg_html = bot_core.card(
                "📤",
                "/user-upload • User 1-Week Cloud Upload",
                "🦄 <b>User Exclusive Upload Feature</b>",
                "",
                "⚠️ <b>CHETAVANI (7-Day Auto-Delete Warning):</b>",
                "<blockquote>Aapki upload ki gayi file ya link sirf <b>1 Hafta (7 Days)</b> tak save rahegi! 7 din poore hote hi yeh automatically delete ho jayegi. (Unlimited Lifetime Upload + 4 Channels ke liye <code>/Pro-plan</code> unlock karein).</blockquote>",
                "",
                "📢 <b>Start Verification:</b> Jab koi user aapke link par Start dabayega, use <b>2 Hamare (Admin) Channels + 2 Aapke Channels</b> join karne honge!",
                footer=bot_core.BOT_NAME,
            )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🟢 📤 Upload File in Vault Tab",
                        "action": "tab:files",
                        "color": "success",
                    },
                    {
                        "text": "💎 🔑 /Pro-plan (Lifetime + 4 Channels)",
                        "action": "sim:pro_plan",
                        "color": "gold",
                    },
                ],
                [
                    {
                        "text": "🦄 🏠 Open User Bot Home",
                        "action": "sim:user_bot_home",
                        "color": "purple",
                    },
                    {
                        "text": "🔵 🛠 Back to VIP Panel",
                        "action": "sim:start",
                        "color": "primary",
                    },
                ],
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "pro_plan":
        has_pro = bot_core.is_user_pro(user_id)
        if has_pro and not is_adm:
            msg_html, _ = bot_core.build_pro_plan_activated_card_and_kb(user_id)
            return {
                "message_html": msg_html,
                "banner_url": bot_core.DEFAULT_PRO_BANNER_URL,
                "buttons": [
                    [
                        {
                            "text": "🟣 ➕ Add 4 Own Channels (Admin Removed!)",
                            "action": "tab:botbuild",
                            "color": "purple",
                        },
                        {
                            "text": "🟢 📤 /user-upload (♾️ Lifetime)",
                            "action": "sim:user_upload",
                            "color": "success",
                        },
                    ],
                    [
                        {
                            "text": "🔵 🏠 Back to /start",
                            "action": "sim:start",
                            "color": "primary",
                        }
                    ],
                ],
                "delivered_file": None,
                "state": build_full_state(),
            }

        bcfg = bot_core.get_bot_builder_config()
        pro_link = bcfg.get("pro_activation_link") or bot_core.get_pro_plan_activation_link()
        msg_html = bot_core.card(
            "🦄",
            "/Pro-plan • Unlock VIP Lifetime + 4 Channels!",
            "✨ <b>Kya aap Lifetime Unlimited Upload + Apne Bot me 4 Force-Join Channels unlock karna chahte hain?</b>",
            "",
            "🔥 <b>/Pro-plan VIP Benefits:</b>",
            "• ♾️ <b>Lifetime Permanent Vault:</b> Aapki files kabhi delete nahi hongi!",
            "• 📢 <b>4 Own Force-Join Channels:</b> Admin ke 2 Channels hat jayenge aur aap apne <b>4 Force-Join Channels</b> jod payenge!",
            "• 🚀 <b>Unlimited Uploads &amp; &lt;1s Instant Delivery</b>",
            f"• 🛒 <b>Buy Secret Key / Link:</b> @{bot_core.PRO_STORE_BOT_USERNAME}",
            "",
            "🔑 <b>Activate karne ke liye Secret Key daalein ya One-Click Activation Link par click karein:</b>",
            footer=bot_core.BOT_NAME,
        )
        return {
            "message_html": msg_html,
            "buttons": [
                [
                    {
                        "text": "🦄 🔗 Click Pro Activation Link (Instant VIP)",
                        "action": "sim:pro_link_activate",
                        "color": "gold",
                    }
                ],
                [
                    {
                        "text": f"🛒 💎 Buy Pro Key (@{bot_core.PRO_STORE_BOT_USERNAME})",
                        "action": f"url:{bot_core.PRO_STORE_BOT_URL}",
                        "color": "amber",
                    },
                    {
                        "text": "🔵 🛠 Back to /start",
                        "action": "sim:start",
                        "color": "primary",
                    },
                ],
            ],
            "delivered_file": None,
            "state": build_full_state(),
        }

    if action == "pro_link_activate":
        bcfg = bot_core.get_bot_builder_config()
        entered_key = str(
            payload.get("secret_key")
            or bcfg.get("pro_plan_secret_key")
            or bot_core.DEFAULT_PRO_PLAN_SECRET_KEY
        ).strip()
        target_uid = int(payload.get("target_user_id") or 987654321)
        ok, feedback = bot_core.activate_user_pro_plan(
            user_id=target_uid,
            entered_key=entered_key,
            first_name=first_name,
            username=first_name.lower().replace(" ", "_"),
        )
        if not ok:
            msg_html = bot_core.card(
                "⚠️",
                "Single-Use Pro Link Already Claimed!",
                feedback,
                "",
                f"🛒 <b>Buy New Key:</b> @{bot_core.PRO_STORE_BOT_USERNAME}",
                "👑 <b>Admin Tip:</b> Bot Builder tab se 'Reset Single-Use Link' ya 'Generate New Key' dabayein!",
                footer=bot_core.BOT_NAME,
            )
            return {
                "message_html": msg_html,
                "buttons": [
                    [
                        {
                            "text": "🎛️ 🔄 Reset / Generate Key in Admin Tab",
                            "action": "tab:botbuild",
                            "color": "gold",
                        },
                        {
                            "text": "🔵 🏠 Back to /start",
                            "action": "sim:start",
                            "color": "primary",
                        },
                    ]
                ],
                "delivered_file": None,
                "state": build_full_state(),
            }

        msg_html, _ = bot_core.build_pro_plan_activated_card_and_kb(target_uid)
        return {
            "message_html": msg_html,
            "banner_url": bot_core.DEFAULT_PRO_BANNER_URL,
            "buttons": [
                [
                    {
                        "text": "🟣 ➕ Add 4 Own Channels (Admin 2 Removed!)",
                        "action": "tab:botbuild",
                        "color": "purple",
                    },
                    {
                        "text": "🟢 📤 /user-upload (♾️ Lifetime)",
                        "action": "sim:user_upload",
                        "color": "success",
                    },
                ],
                [
                    {
                        "text": "🦄 🏠 Open My Pro Bot Home",
                        "action": "sim:user_bot_home",
                        "color": "gold",
                    },
                    {
                        "text": "🔵 🏠 Back to /start",
                        "action": "sim:start",
                        "color": "primary",
                    },
                ],
            ],
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
</head>
<body>
  <h1>Premium File Vault</h1>
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

        # 1. Telegram Webhook Receiver (Instant <1s dispatch, No Password)
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

        if not self._is_authorized():
            self._send_json(
                {"detail": "Unauthorized — Vault Password required"}, status=401
            )
            return

        # 3. 5-Minute Keep-Alive Webhook Registration Trigger
        if path == "/api/keepalive":
            custom_url = str(body.get("webhook_url") or "").strip() or None
            hb = bot_core.register_webhook_heartbeat(base_url=custom_url)
            state = build_full_state()
            state["heartbeat"] = hb
            self._send_json(state)
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
                webhook_url=body.get("webhook_url"),
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

        # Bulk Delete Selected Files from 'Permanent Vault Items' table
        if path == "/api/files/bulk-delete":
            raw_ids = body.get("file_ids") or []
            if not isinstance(raw_ids, list) or not raw_ids:
                self._send_json(
                    {"detail": "Kam se kam 1 file select karein bulk delete ke liye."},
                    status=400,
                )
                return
            deleted_count = bot_core.delete_files_bulk(raw_ids)
            state = build_full_state()
            state["deleted_count"] = deleted_count
            self._send_json(state)
            return

        if path == "/api/files":
            custom_name = str(body.get("custom_name") or body.get("file_name") or "").strip()
            fname = str(body.get("file_name") or custom_name).strip()
            group_name = str(body.get("group_name") or "").strip()
            ftype = str(body.get("file_type") or "document").strip()
            caption = str(body.get("caption") or "").strip()
            external_url = str(body.get("external_url") or "").strip()
            tg_id = str(body.get("tg_file_id") or "").strip()
            random_digits = int(body.get("random_digits") or 6)
            uploader_role = str(body.get("uploader_role") or "admin").strip().lower()

            if not custom_name and not fname:
                self._send_json(
                    {"detail": "File / Link ka Naam (Custom Name) zaroori hai."},
                    status=400,
                )
                return

            if ftype == "link":
                if not external_url and tg_id.startswith(("http://", "https://", "t.me/")):
                    external_url = tg_id
                if not external_url:
                    self._send_json(
                        {"detail": "Direct Link (https://...) daalna zaroori hai."},
                        status=400,
                    )
                    return
                if external_url.startswith("t.me/"):
                    external_url = f"https://{external_url}"
                tg_id = external_url

            if not tg_id:
                tg_id = f"BQACAgUAAxkBAAI_{bot_core.clean_slug_part(custom_name or fname)}"

            admin_id = bot_core.ADMIN_IDS[0] if bot_core.ADMIN_IDS else 123456789
            new_id = bot_core.save_file(
                tg_file_id=tg_id,
                file_type=ftype,
                file_name=fname or custom_name,
                caption=caption,
                created_by=admin_id if uploader_role != "user" else 555666777,
                custom_name=custom_name or fname,
                group_name=group_name,
                random_digits=random_digits,
                external_url=external_url,
                uploader_role=uploader_role,
            )
            state = build_full_state()
            state["created_file_id"] = new_id
            self._send_json(state)
            return

        if path == "/api/bot-builder/config":
            desc = body.get("description")
            allow_build = body.get("allow_bot_build")
            allow_upload = body.get("allow_user_upload")
            allow_two_ch = body.get("allow_user_two_channels")
            allow_pro = body.get("allow_pro_plan")
            show_help = body.get("show_start_help")
            welcome_text = body.get("start_welcome_text")
            secret_key = body.get("pro_plan_secret_key")
            reset_single_use = bool(body.get("reset_single_use"))
            expiry_days = body.get("user_file_expiry_days")
            bot_core.save_bot_builder_config(
                description=str(desc) if desc is not None else None,
                allow_bot_build=bool(allow_build) if allow_build is not None else None,
                allow_user_upload=bool(allow_upload) if allow_upload is not None else None,
                allow_user_two_channels=bool(allow_two_ch) if allow_two_ch is not None else None,
                user_file_expiry_days=int(expiry_days) if expiry_days is not None else None,
                allow_pro_plan=bool(allow_pro) if allow_pro is not None else None,
                pro_plan_secret_key=str(secret_key) if secret_key is not None else None,
                show_start_help=bool(show_help) if show_help is not None else None,
                start_welcome_text=str(welcome_text) if welcome_text is not None else None,
                reset_single_use=reset_single_use,
            )
            self._send_json(build_full_state())
            return

        if path == "/api/pro-plan/generate-key":
            cfg = bot_core.generate_new_pro_plan_key()
            state = build_full_state()
            state["generated_key"] = cfg.get("pro_plan_secret_key")
            state["pro_activation_link"] = cfg.get("pro_activation_link")
            self._send_json(state)
            return

        if path == "/api/pro-plan/reset-link":
            bot_core.reset_pro_plan_single_use_link()
            self._send_json(build_full_state())
            return

        if path == "/api/pro-plan/activate":
            uid = int(body.get("user_id") or 987654321)
            entered_key = str(body.get("secret_key") or "").strip()
            fname = str(body.get("first_name") or "VIP User").strip()
            ok, feedback = bot_core.activate_user_pro_plan(
                user_id=uid, entered_key=entered_key, first_name=fname
            )
            if not ok:
                self._send_json({"detail": feedback, "activated": False}, status=400)
                return
            state = build_full_state()
            state["activated"] = True
            state["message"] = feedback
            self._send_json(state)
            return

        if path == "/api/users/pro":
            uid = int(body.get("user_id") or 0)
            is_pro_flag = bool(body.get("is_pro", True))
            if not uid:
                self._send_json({"detail": "Valid user_id required"}, status=400)
                return
            bot_core.set_user_pro_status(uid, is_pro_flag)
            self._send_json(build_full_state())
            return

        if path == "/api/user-bots":
            owner_name = str(body.get("owner_name") or "VIP User").strip()
            owner_id = int(body.get("owner_user_id") or 555666777)
            bot_token = str(body.get("bot_token") or "").strip()
            bot_name = str(body.get("bot_name") or "").strip()
            bot_username = str(body.get("bot_username") or "").strip()
            c1_title = str(body.get("channel_1_title") or "").strip()
            c1_link = str(body.get("channel_1_link") or "").strip()
            c2_title = str(body.get("channel_2_title") or "").strip()
            c2_link = str(body.get("channel_2_link") or "").strip()
            c3_title = str(body.get("channel_3_title") or "").strip()
            c3_link = str(body.get("channel_3_link") or "").strip()
            c4_title = str(body.get("channel_4_title") or "").strip()
            c4_link = str(body.get("channel_4_link") or "").strip()

            if not bot_core.validate_bot_token(bot_token):
                self._send_json(
                    {
                        "detail": "Sahi @BotFather Token daalein (e.g. 7123456789:AAH_your_bot_token_here)."
                    },
                    status=400,
                )
                return

            ub_id = bot_core.save_user_bot(
                owner_user_id=owner_id,
                owner_name=owner_name,
                bot_token=bot_token,
                bot_username=bot_username,
                bot_name=bot_name,
                channel_1_title=c1_title,
                channel_1_link=c1_link,
                channel_2_title=c2_title,
                channel_2_link=c2_link,
                channel_3_title=c3_title,
                channel_3_link=c3_link,
                channel_4_title=c4_title,
                channel_4_link=c4_link,
            )
            state = build_full_state()
            state["created_user_bot_id"] = ub_id
            self._send_json(state)
            return

        if path == "/api/user-bots/channels":
            bot_id = int(body.get("bot_id") or 0)
            c1_title = str(body.get("channel_1_title") or "").strip()
            c1_link = str(body.get("channel_1_link") or "").strip()
            c2_title = str(body.get("channel_2_title") or "").strip()
            c2_link = str(body.get("channel_2_link") or "").strip()
            c3_title = body.get("channel_3_title")
            c3_link = body.get("channel_3_link")
            c4_title = body.get("channel_4_title")
            c4_link = body.get("channel_4_link")
            updated = bot_core.update_user_bot_channels(
                bot_db_id=bot_id,
                channel_1_title=c1_title,
                channel_1_link=c1_link,
                channel_2_title=c2_title,
                channel_2_link=c2_link,
                channel_3_title=str(c3_title).strip() if c3_title is not None else None,
                channel_3_link=str(c3_link).strip() if c3_link is not None else None,
                channel_4_title=str(c4_title).strip() if c4_title is not None else None,
                channel_4_link=str(c4_link).strip() if c4_link is not None else None,
            )
            if not updated:
                self._send_json({"detail": "User bot not found"}, status=404)
                return
            self._send_json(build_full_state())
            return

        if path == "/api/group-banner":
            banner_fid = str(body.get("banner_file_id") or "").strip()
            desc = str(body.get("description") or "").strip()
            btype = str(body.get("banner_type") or "photo").strip()
            if not banner_fid or not desc:
                self._send_json(
                    {
                        "detail": "/Group-image-description ke liye Banner Image aur Description dono zaroori hain."
                    },
                    status=400,
                )
                return
            bot_core.save_group_banner_config(banner_fid, desc, btype)
            self._send_json(build_full_state())
            return

        if path == "/api/groups":
            title = str(body.get("title") or "").strip()
            username = str(body.get("username") or "").strip()
            invite = str(body.get("invite_link") or "").strip()
            try:
                chat_id = int(body.get("chat_id"))
            except (TypeError, ValueError):
                self._send_json(
                    {"detail": "Group ya Channel ka numeric Chat ID (e.g. -100123456789) zaroori hai."},
                    status=400,
                )
                return
            if not title:
                self._send_json({"detail": "Group ya Channel ka Name zaroori hai."}, status=400)
                return

            admin_id = bot_core.ADMIN_IDS[0] if bot_core.ADMIN_IDS else 123456789
            gid = bot_core.save_managed_group(
                chat_id=chat_id,
                title=title,
                username=username,
                invite_link=invite,
                interval_minutes=15,
                added_by=admin_id,
            )
            # Post immediately first upon joining/adding!
            bot_core.update_managed_group_post_state(gid, 1001)
            ptb_app, bot_loop = bot_core.get_active_bot_app()
            if ptb_app is not None and bot_loop is not None:
                try:
                    asyncio.run_coroutine_threadsafe(
                        bot_core.send_and_rotate_group_banner(ptb_app.bot, gid),
                        bot_loop,
                    )
                except Exception:
                    pass
            self._send_json(build_full_state())
            return

        if path == "/api/groups/rotate":
            gid = int(body.get("group_id") or 0)
            row = bot_core.get_managed_group_by_id(gid)
            if not row:
                self._send_json({"detail": "Group not found"}, status=404)
                return
            next_msg_id = int(dict(row).get("last_message_id") or 1000) + 1
            bot_core.update_managed_group_post_state(gid, next_msg_id)
            ptb_app, bot_loop = bot_core.get_active_bot_app()
            if ptb_app is not None and bot_loop is not None:
                try:
                    asyncio.run_coroutine_threadsafe(
                        bot_core.send_and_rotate_group_banner(ptb_app.bot, gid),
                        bot_loop,
                    )
                except Exception:
                    pass
            self._send_json(build_full_state())
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

        if path.startswith("/api/groups/"):
            try:
                gid = int(path.split("/")[-1])
                bot_core.delete_managed_group(gid)
                self._send_json(build_full_state())
                return
            except ValueError:
                self._send_json({"detail": "Invalid group ID"}, status=400)
                return

        if path.startswith("/api/user-bots/"):
            try:
                ubid = int(path.split("/")[-1])
                bot_core.delete_user_bot(ubid)
                self._send_json(build_full_state())
                return
            except ValueError:
                self._send_json({"detail": "Invalid user bot ID"}, status=400)
                return

        self._send_json({"detail": "Not found"}, status=404)


def create_control_center_server(
    port: int = 3000, acquire_lock: bool = False, start_bot_thread: bool = True
) -> VaultHTTPServer:
    bot_core.init_db()
    bot_core.seed_demo_data_if_empty()
    if acquire_lock:
        bot_core.acquire_single_instance_lock()
    bot_core.start_keep_alive_daemon(port=port)
    if start_bot_thread:
        bot_core.ensure_bot_background_thread()
    server = VaultHTTPServer(("0.0.0.0", port), VaultRequestHandler)
    bot_core.logger.info(
        "🌐 Premium File Vault Control Center (24/7 Fast + 5m Keep-Alive) listening on http://0.0.0.0:%d",
        port,
    )
    return server


def run_control_center_server(port: int = 3000, acquire_lock: bool = False) -> None:
    server = create_control_center_server(port=port, acquire_lock=acquire_lock)
    server.serve_forever(poll_interval=0.05)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    run_control_center_server(port=port, acquire_lock=True)
