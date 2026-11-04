import asyncio
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

import app as web_app
import python as bot_core


class PremiumFileVaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_db = str(Path(self.tmp_dir.name) / "bot_data.db")
        bot_core.init_db(self.test_db)

    def tearDown(self):
        if bot_core.conn is not None:
            bot_core.conn.close()
            bot_core.conn = None
        self.tmp_dir.cleanup()

    def test_dashboard_password_verification(self):
        req_file = Path(__file__).resolve().parent / "requirements.txt"
        self.assertTrue(req_file.is_file(), "requirements.txt must exist for Render")
        self.assertIn("python-telegram-bot", req_file.read_text(encoding="utf-8"))
        self.assertFalse(web_app.verify_dashboard_password(""))
        self.assertFalse(web_app.verify_dashboard_password(None))
        self.assertFalse(web_app.verify_dashboard_password("wrong_password_123"))
        self.assertTrue(
            web_app.verify_dashboard_password("SJEIDB@@@1272737SJWHSH2727")
        )

    def test_webhook_url_detection_and_5m_keepalive_heartbeat(self):
        self.assertEqual(bot_core.KEEP_ALIVE_INTERVAL_SECONDS, 300)
        old_render = os.environ.get("RENDER_EXTERNAL_URL")
        old_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
        old_poll = os.environ.get("USE_POLLING")
        try:
            os.environ.pop("USE_POLLING", None)
            os.environ["RENDER_EXTERNAL_URL"] = "https://upload-file-shar-link-bot.onrender.com/"
            self.assertEqual(
                bot_core.resolve_webhook_base_url(),
                "https://upload-file-shar-link-bot.onrender.com",
            )
            self.assertEqual(
                bot_core.resolve_keepalive_webhook_target(),
                "https://upload-file-shar-link-bot.onrender.com/telegram-webhook",
            )
            hb = bot_core.register_webhook_heartbeat(
                bot_token="",
                base_url="https://upload-file-shar-link-bot.onrender.com",
            )
            self.assertTrue(hb["ok"])
            self.assertTrue(hb["keep_alive_active"])
            self.assertEqual(hb["interval_seconds"], 300)
            self.assertEqual(
                hb["webhook_url"],
                "https://upload-file-shar-link-bot.onrender.com/telegram-webhook",
            )
        finally:
            if old_render is None:
                os.environ.pop("RENDER_EXTERNAL_URL", None)
            else:
                os.environ["RENDER_EXTERNAL_URL"] = old_render
            if old_host is None:
                os.environ.pop("RENDER_EXTERNAL_HOSTNAME", None)
            else:
                os.environ["RENDER_EXTERNAL_HOSTNAME"] = old_host
            if old_poll is None:
                os.environ.pop("USE_POLLING", None)
            else:
                os.environ["USE_POLLING"] = old_poll

    def test_config_and_token_validation(self):
        self.assertFalse(bot_core.validate_bot_token(""))
        self.assertFalse(bot_core.validate_bot_token("1234567890:ABC..."))
        self.assertFalse(bot_core.validate_bot_token("YOUR_BOT_TOKEN_HERE"))
        self.assertTrue(
            bot_core.validate_bot_token("7123456789:AAH1234567890abcdefGHIJKLMNOPQRSTUV")
        )
        self.assertEqual(
            bot_core.parse_admin_ids("12345, 67890, invalid, 12345"), [12345, 67890]
        )

    def test_db_path_fallback_for_unwritable_mount(self):
        resolved = bot_core.resolve_db_path("/nonexistent_root_mount_xyz/bot_data.db")
        self.assertTrue(resolved.endswith("bot_data.db"))

    def test_custom_link_formats_and_permanent_storage(self):
        # 1. Standard upload with custom name + 6-digit random number: ?start=NAME?RANDOM
        fid1 = bot_core.save_file(
            tg_file_id="BQACAgUAAxkBAAI_course",
            file_type="document",
            file_name="KishanCourse.zip",
            caption="Permanent Course Pack",
            created_by=123456789,
            custom_name="KishanCourse",
            random_digits=6,
        )
        row1 = dict(bot_core.get_file(fid1))
        self.assertEqual(row1["is_permanent"], 1)
        self.assertTrue(row1["random_code"].isdigit())
        self.assertEqual(len(row1["random_code"]), 6)
        link1 = bot_core.file_link("FILE_SHARE_00_bot", row1)
        self.assertEqual(
            link1,
            f"https://t.me/FILE_SHARE_00_bot?start=KishanCourse?{row1['random_code']}",
        )
        self.assertIsNotNone(
            bot_core.resolve_file_by_start_token(f"KishanCourse?{row1['random_code']}")
        )
        self.assertIsNotNone(
            bot_core.resolve_file_by_start_token(f"KishanCourse__{row1['random_code']}")
        )

        # 2. /group-upload format: ?start=GroupName?Name=RANDOM (with 4-digit random code)
        fid2 = bot_core.save_file(
            tg_file_id="AgACAgUAAxkBAAI_group_img",
            file_type="photo",
            file_name="Poster4K.jpg",
            caption="Group Upload Permanent Image",
            created_by=123456789,
            custom_name="Poster4K",
            group_name="VIPGroup",
            random_digits=4,
        )
        row2 = dict(bot_core.get_file(fid2))
        self.assertEqual(len(row2["random_code"]), 4)
        link2 = bot_core.file_link("FILE_SHARE_00_bot", row2)
        self.assertEqual(
            link2,
            f"https://t.me/FILE_SHARE_00_bot?start=VIPGroup?Poster4K={row2['random_code']}",
        )
        resolved2 = bot_core.resolve_file_by_start_token(
            f"VIPGroup?Poster4K={row2['random_code']}"
        )
        self.assertIsNotNone(resolved2)
        self.assertEqual(int(resolved2["id"]), fid2)

        # 3. Direct Link upload (file_type='link')
        fid3 = bot_core.save_file(
            tg_file_id="https://t.me/PremiumVaultUpdates",
            file_type="link",
            file_name="MegaFolder",
            caption="Direct Cloud Link",
            created_by=123456789,
            custom_name="MegaFolder",
            external_url="https://t.me/PremiumVaultUpdates",
        )
        row3 = dict(bot_core.get_file(fid3))
        self.assertEqual(row3["file_type"], "link")
        self.assertEqual(row3["external_url"], "https://t.me/PremiumVaultUpdates")

    def test_group_banner_and_ad_group_15m_for_groups_and_channels(self):
        cfg = bot_core.save_group_banner_config(
            "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800",
            "Official 15m Group & Channel Banner",
            "photo",
        )
        self.assertTrue(cfg["verified"])

        # Add a Group and a Channel; both must have strict 15-minute stay interval (never 2m)
        gid1 = bot_core.save_managed_group(
            chat_id=-100111222333,
            title="VIP Discussion Group",
            interval_minutes=2,  # Even if 2 is passed, must enforce 15 minutes!
            added_by=123456789,
        )
        gid2 = bot_core.save_managed_group(
            chat_id=-100444555666,
            title="VIP Main Channel",
            interval_minutes=15,
            added_by=123456789,
        )
        g1 = dict(bot_core.get_managed_group_by_id(gid1))
        g2 = dict(bot_core.get_managed_group_by_id(gid2))
        self.assertEqual(g1["interval_minutes"], 15)
        self.assertEqual(g2["interval_minutes"], 15)

        # Test immediate post + 15m rotation deletion of old message
        deleted_msgs = []
        sent_msgs = []

        class DummyBot:
            async def delete_message(self, chat_id, message_id):
                deleted_msgs.append((chat_id, message_id))

            async def send_photo(self, chat_id, photo, caption, reply_markup):
                msg_id = 500 + len(sent_msgs)
                sent_msgs.append((chat_id, msg_id, photo))
                return SimpleNamespace(message_id=msg_id)

        async def _run_rotations():
            # First post on join (no old message to delete yet)
            await bot_core.send_and_rotate_group_banner(DummyBot(), gid1)
            # Second post after 15 minutes (deletes message 500, sends 501)
            await bot_core.send_and_rotate_group_banner(DummyBot(), gid1)

        asyncio.run(_run_rotations())
        self.assertEqual(len(sent_msgs), 2)
        self.assertEqual(deleted_msgs, [(-100111222333, 500)])
        updated_g1 = dict(bot_core.get_managed_group_by_id(gid1))
        self.assertEqual(updated_g1["last_message_id"], 501)
        self.assertEqual(updated_g1["send_count"], 2)

    def test_database_crud_operations(self):
        bot_core.save_user(111222333, "Kishan", "kishan_dev")
        self.assertIn(111222333, bot_core.get_user_ids())

        ch_id = bot_core.save_channel(
            -10099887766, "Main Vault Channel", "@MainVault", "https://t.me/MainVault"
        )
        self.assertGreater(ch_id, 0)
        channels = bot_core.get_channels()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]["username"], "MainVault")

        f_id = bot_core.save_file(
            "BQACAgUAAxkBAAI_test",
            "document",
            "vault_pack.zip",
            "Premium Pack",
            111222333,
        )
        self.assertGreater(f_id, 0)
        f_row = bot_core.get_file(f_id)
        self.assertIsNotNone(f_row)
        self.assertEqual(f_row["downloads"], 0)

        bot_core.save_pending(111222333, f_id)
        self.assertIsNotNone(bot_core.get_pending(111222333))
        bot_core.add_download(f_id)
        bot_core.delete_pending(111222333)
        self.assertIsNone(bot_core.get_pending(111222333))
        self.assertEqual(bot_core.get_file(f_id)["downloads"], 1)

        stats = bot_core.get_stats()
        self.assertEqual(stats["channels"], 1)
        self.assertEqual(stats["files"], 1)
        self.assertEqual(stats["users"], 1)
        self.assertEqual(stats["downloads"], 1)

        self.assertTrue(bot_core.delete_file(f_id))
        self.assertTrue(bot_core.delete_channel(ch_id))
        self.assertEqual(bot_core.get_stats()["files"], 0)
        self.assertEqual(bot_core.get_stats()["channels"], 0)

    def test_helpers_and_force_sub_builders(self):
        self.assertEqual(
            bot_core.parse_chat_identifier("https://t.me/MyChannel"), "@MyChannel"
        )
        self.assertEqual(bot_core.parse_chat_identifier("-100123456"), -100123456)
        self.assertIsNone(bot_core.parse_chat_identifier("https://t.me/+privateHash"))
        self.assertEqual(
            bot_core.file_link("@TestBot", 42), "https://t.me/TestBot?start=file_42"
        )
        self.assertEqual(len(bot_core.progress_bar(1, 2, 10)), 10)

        button = bot_core.btn("Verify", data="verify:1", style=bot_core.GREEN)
        self.assertEqual(button.text, "Verify")
        self.assertEqual(button.callback_data, "verify:1")

    def test_conflict_error_handler_graceful_recovery(self):
        initial_conflicts = int(bot_core.BOT_RUNTIME_STATUS.get("conflict_count", 0))
        ctx = SimpleNamespace(
            error=bot_core.Conflict(
                "Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
            )
        )

        async def _run():
            await bot_core.error_handler(None, ctx)

        asyncio.run(_run())
        self.assertEqual(
            int(bot_core.BOT_RUNTIME_STATUS["conflict_count"]),
            initial_conflicts + 1,
        )
        self.assertIn("Conflict:", bot_core.BOT_RUNTIME_STATUS["last_error"])

    def test_render_http_head_get_and_keepalive_endpoints(self):
        server = web_app.VaultHTTPServer(("127.0.0.1", 0), web_app.VaultRequestHandler)
        port = server.server_address[1]
        t = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        t.start()
        try:
            # 1. HEAD / -> 200 OK
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request("HEAD", "/")
            res = conn.getresponse()
            self.assertEqual(res.status, 200)
            conn.close()

            # 2. GET /healthz -> 200 OK
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request("GET", "/healthz")
            res = conn.getresponse()
            self.assertEqual(res.status, 200)
            conn.close()

            # 3. GET /api/state without password -> 401
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request("GET", "/api/state")
            res = conn.getresponse()
            self.assertEqual(res.status, 401)
            conn.close()

            # 4. GET /api/state with website password -> 200
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request(
                "GET",
                "/api/state",
                headers={"X-Vault-Password": "SJEIDB@@@1272737SJWHSH2727"},
            )
            res = conn.getresponse()
            self.assertEqual(res.status, 200)
            conn.close()

            # 5. POST /api/keepalive -> 200 and returns 5-minute heartbeat status
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request(
                "POST",
                "/api/keepalive",
                body=json.dumps({"webhook_url": "https://vault-bot.onrender.com"}),
                headers={
                    "Content-Type": "application/json",
                    "X-Vault-Password": "SJEIDB@@@1272737SJWHSH2727",
                },
            )
            res = conn.getresponse()
            self.assertEqual(res.status, 200)
            payload = json.loads(res.read().decode("utf-8"))
            self.assertTrue(payload["heartbeat"]["keep_alive_active"])
            self.assertEqual(payload["heartbeat"]["interval_seconds"], 300)
            conn.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_bulk_delete_user_upload_expiry_and_bot_build_2_plus_2_channels(self):
        # 1. Admin Lifetime vs User 7-Day Expiry (/user-upload)
        f_admin = bot_core.save_file(
            tg_file_id="BQACAgUAAxk_admin",
            file_type="document",
            file_name="AdminLifetime.zip",
            caption="Lifetime File",
            created_by=123456789,
            custom_name="AdminLifetime",
            uploader_role="admin",
        )
        f_user1 = bot_core.save_file(
            tg_file_id="BQACAgUAAxk_user1",
            file_type="document",
            file_name="UserWeek1.zip",
            caption="User 7-Day File",
            created_by=555666777,
            custom_name="UserWeek1",
            uploader_role="user",
        )
        f_user2 = bot_core.save_file(
            tg_file_id="BQACAgUAAxk_user2",
            file_type="document",
            file_name="UserWeek2.zip",
            caption="User 7-Day File 2",
            created_by=555666777,
            custom_name="UserWeek2",
            uploader_role="user",
        )
        r_admin = dict(bot_core.get_file(f_admin))
        r_user1 = dict(bot_core.get_file(f_user1))
        self.assertEqual(r_admin["is_permanent"], 1)
        self.assertEqual(r_admin["uploader_role"], "admin")
        self.assertEqual(r_admin["expires_at"], "")
        self.assertEqual(r_user1["is_permanent"], 0)
        self.assertEqual(r_user1["uploader_role"], "user")
        self.assertTrue(r_user1["expires_at"])

        # 2. Bulk Delete Selected Files
        deleted_cnt = bot_core.delete_files_bulk([f_user1, f_user2])
        self.assertEqual(deleted_cnt, 2)
        self.assertIsNone(bot_core.get_file(f_user1))
        self.assertIsNone(bot_core.get_file(f_user2))
        self.assertIsNotNone(bot_core.get_file(f_admin))

        # 3. /BOT-build-description & /BOT-build + 2 Admin Channels + 2 User Channels (Free user)
        bot_core.save_channel(
            -1001110001, "Official Admin Ch 1", "AdminCh1", "https://t.me/AdminCh1"
        )
        bot_core.save_channel(
            -1001110002, "Official Admin Ch 2", "AdminCh2", "https://t.me/AdminCh2"
        )
        cfg = bot_core.save_bot_builder_config(
            description="🦄 Custom Unicorn /BOT-build Description",
            allow_bot_build=True,
            allow_user_upload=True,
            allow_user_two_channels=True,
        )
        self.assertIn("Unicorn", cfg["description"])

        ub_id = bot_core.save_user_bot(
            owner_user_id=555666777,
            owner_name="Rahul",
            bot_token="7123456789:AAH1234567890abcdefGHIJKLMNOPQRSTUV",
            channel_1_title="Rahul Ch 1",
            channel_1_link="https://t.me/RahulCh1",
            channel_2_title="Rahul Ch 2",
            channel_2_link="https://t.me/RahulCh2",
        )
        self.assertGreater(ub_id, 0)
        combined_free = bot_core.get_combined_force_channels_for_user_bot(ub_id)
        # Free User: 2 Admin Channels + 2 User Channels = 4 combined channels on /start
        self.assertEqual(len(combined_free), 4)
        self.assertEqual(sum(1 for c in combined_free if c["owner"] == "admin"), 2)
        self.assertEqual(sum(1 for c in combined_free if c["owner"] == "user"), 2)

    def test_single_use_pro_plan_link_and_4_channel_upgrade(self):
        # Verify default key is FILE-SHARE-YU6J-IEHU-828H
        bcfg = bot_core.get_bot_builder_config()
        self.assertEqual(bcfg["pro_plan_secret_key"], "FILE-SHARE-YU6J-IEHU-828H")
        self.assertEqual(
            bcfg["pro_activation_link"],
            f"https://t.me/{bot_core.BOT_RUNTIME_STATUS['bot_username']}?start=FILE-SHARE-YU6J-IEHU-828H",
        )
        self.assertTrue(bot_core.is_pro_plan_start_token("FILE-SHARE-YU6J-IEHU-828H"))
        self.assertTrue(bot_core.is_pro_plan_start_token("PRO_FILE-SHARE-YU6J-IEHU-828H"))

        # Add 2 Admin Channels and a User Bot for User 777888999
        bot_core.save_channel(
            -1002220001, "Admin Official #1", "AdminOff1", "https://t.me/AdminOff1"
        )
        bot_core.save_channel(
            -1002220002, "Admin Official #2", "AdminOff2", "https://t.me/AdminOff2"
        )
        ub_id = bot_core.save_user_bot(
            owner_user_id=777888999,
            owner_name="Krishna User",
            bot_token="7123456789:AAH1234567890abcdefGHIJKLMNOPQRSTUV",
            channel_1_title="User Ch 1",
            channel_1_link="https://t.me/UserCh1",
            channel_2_title="User Ch 2",
            channel_2_link="https://t.me/UserCh2",
        )

        # Before Pro Plan: 2 Admin + 2 User channels
        before_ch = bot_core.get_combined_force_channels_for_user_bot(ub_id)
        self.assertEqual([c["owner"] for c in before_ch], ["admin", "admin", "user", "user"])

        # 1st user (777888999) clicks the Single-Use Pro Activation Link -> succeeds!
        ok1, msg1 = bot_core.activate_user_pro_plan(
            user_id=777888999,
            entered_key="FILE-SHARE-YU6J-IEHU-828H",
            first_name="Krishna User",
        )
        self.assertTrue(ok1, msg1)
        self.assertTrue(bot_core.is_user_pro(777888999))

        # 2nd user (888999000) tries to click the SAME Single-Use Link -> BLOCKED!
        ok2, msg2 = bot_core.activate_user_pro_plan(
            user_id=888999000,
            entered_key="FILE-SHARE-YU6J-IEHU-828H",
            first_name="Second User",
        )
        self.assertFalse(ok2)
        self.assertIn("Single-Use", msg2)
        self.assertFalse(bot_core.is_user_pro(888999000))

        # After Pro Plan on User 777888999: Admin's 2 channels are REMOVED and user can add 4 own channels!
        bot_core.update_user_bot_channels(
            bot_db_id=ub_id,
            channel_1_title="Krishna Ch 1",
            channel_1_link="https://t.me/KrishnaCh1",
            channel_2_title="Krishna Ch 2",
            channel_2_link="https://t.me/KrishnaCh2",
            channel_3_title="Krishna Ch 3",
            channel_3_link="https://t.me/KrishnaCh3",
            channel_4_title="Krishna Ch 4",
            channel_4_link="https://t.me/KrishnaCh4",
        )
        after_ch = bot_core.get_combined_force_channels_for_user_bot(ub_id)
        self.assertEqual(len(after_ch), 4)
        self.assertEqual([c["owner"] for c in after_ch], ["user", "user", "user", "user"])
        self.assertEqual(
            [c["title"] for c in after_ch],
            ["Krishna Ch 1", "Krishna Ch 2", "Krishna Ch 3", "Krishna Ch 4"],
        )

        # Pro user uploads via /user-upload are LIFETIME PERMANENT (is_permanent=1, expires_at='')
        f_pro = bot_core.save_file(
            tg_file_id="BQACAgUAAxk_pro",
            file_type="document",
            file_name="ProForever.zip",
            caption="Pro Lifetime File",
            created_by=777888999,
            custom_name="ProForever",
            uploader_role="user",
        )
        r_pro = dict(bot_core.get_file(f_pro))
        self.assertEqual(r_pro["is_permanent"], 1)
        self.assertEqual(r_pro["expires_at"], "")

        # Admin resets Single-Use Link -> 2nd user can now activate!
        bot_core.reset_pro_plan_single_use_link()
        ok2_retry, _ = bot_core.activate_user_pro_plan(
            user_id=888999000,
            entered_key="FILE-SHARE-YU6J-IEHU-828H",
            first_name="Second User",
        )
        self.assertTrue(ok2_retry)
        self.assertTrue(bot_core.is_user_pro(888999000))

        # Admin generates a brand-new key -> starts with FILE-SHARE- and resets single-use
        new_cfg = bot_core.generate_new_pro_plan_key()
        self.assertTrue(new_cfg["pro_plan_secret_key"].startswith("FILE-SHARE-"))
        self.assertEqual(new_cfg["pro_key_used_by"], 0)

    def test_start_bot_build_user_upload_and_pro_link_async_handlers(self):
        sent_messages = []
        sent_photos = []

        class DummyMessage:
            text = "/start"
            caption = ""

            async def reply_text(self, text, reply_markup=None, disable_web_page_preview=None):
                sent_messages.append((text, reply_markup))
                return SimpleNamespace(message_id=len(sent_messages))

        class DummyBot:
            async def send_message(self, chat_id, text, reply_markup=None, disable_web_page_preview=None):
                sent_messages.append((text, reply_markup))
                return SimpleNamespace(message_id=len(sent_messages))

            async def send_photo(self, chat_id, photo, caption, reply_markup=None):
                sent_photos.append((chat_id, photo, caption, reply_markup))
                return SimpleNamespace(message_id=len(sent_photos))

        user_obj = SimpleNamespace(
            id=444555666, first_name="TestUser", username="test_user"
        )
        chat_obj = SimpleNamespace(id=444555666, type="private", title="", username="")
        update = SimpleNamespace(
            effective_user=user_obj,
            effective_chat=chat_obj,
            message=DummyMessage(),
            callback_query=None,
        )

        async def _run_all():
            # 1. Normal /start
            ctx_start = SimpleNamespace(args=[], bot=DummyBot(), bot_data={}, user_data={})
            await bot_core.start_cmd(update, ctx_start)

            # 2. /bot_build
            await bot_core.bot_build_entry(update, ctx_start)

            # 3. /user_upload
            await bot_core.user_upload_entry(update, ctx_start)

            # 4. /Pro-plan (must NOT leak secret key to regular user, must show @Krishna_Zx_Store_bot)
            await bot_core.pro_plan_entry(update, ctx_start)

            # 5. One-Click Pro Activation Link: /start FILE-SHARE-YU6J-IEHU-828H
            ctx_pro_link = SimpleNamespace(
                args=["FILE-SHARE-YU6J-IEHU-828H"],
                bot=DummyBot(),
                bot_data={},
                user_data={},
            )
            await bot_core.start_cmd(update, ctx_pro_link)

        asyncio.run(_run_all())
        self.assertGreaterEqual(len(sent_messages), 4)
        # Ensure regular user /Pro-plan prompt never leaks the secret key
        pro_prompt_text = sent_messages[3][0]
        self.assertNotIn("FILE-SHARE-YU6J-IEHU-828H", pro_prompt_text)
        self.assertIn("Krishna_Zx_Store_bot", pro_prompt_text)

        # Ensure clicking ?start=FILE-SHARE-YU6J-IEHU-828H sent the Default VIP Banner + YOUR PRO PLAN ACTIVE!
        self.assertEqual(len(sent_photos), 1)
        self.assertEqual(sent_photos[0][1], bot_core.DEFAULT_PRO_BANNER_URL)
        self.assertIn("YOUR PRO PLAN ACTIVE!", sent_photos[0][2])
        self.assertTrue(bot_core.is_user_pro(444555666))


if __name__ == "__main__":
    unittest.main()

