import asyncio
import os
from pathlib import Path
import tempfile
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
        self.assertFalse(web_app.verify_dashboard_password(""))
        self.assertFalse(web_app.verify_dashboard_password("wrong_password_123"))
        self.assertTrue(
            web_app.verify_dashboard_password(
                "FREE00000000GHGGHGHGHGH444555Kishan1122@8441"
            )
        )

    def test_webhook_url_detection_for_render(self):
        old_render = os.environ.get("RENDER_EXTERNAL_URL")
        try:
            os.environ["RENDER_EXTERNAL_URL"] = "https://my-vault-bot.onrender.com/"
            self.assertEqual(
                bot_core.resolve_webhook_base_url(),
                "https://my-vault-bot.onrender.com",
            )
        finally:
            if old_render is None:
                os.environ.pop("RENDER_EXTERNAL_URL", None)
            else:
                os.environ["RENDER_EXTERNAL_URL"] = old_render

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
        self.assertFalse(bool(getattr(button, "api_kwargs", None)))

    def test_conflict_error_handler_graceful_recovery(self):
        initial_conflicts = int(bot_core.BOT_RUNTIME_STATUS.get("conflict_count", 0))
        ctx = SimpleNamespace(
            error=bot_core.Conflict(
                "Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"
            )
        )

        async def _run():
            orig_sleep = asyncio.sleep
            asyncio.sleep = lambda _: orig_sleep(0.01)
            try:
                await bot_core.error_handler(None, ctx)
            finally:
                asyncio.sleep = orig_sleep

        asyncio.run(_run())
        self.assertEqual(
            int(bot_core.BOT_RUNTIME_STATUS["conflict_count"]),
            initial_conflicts + 1,
        )
        self.assertIn("Conflict:", bot_core.BOT_RUNTIME_STATUS["last_error"])


if __name__ == "__main__":
    unittest.main()
