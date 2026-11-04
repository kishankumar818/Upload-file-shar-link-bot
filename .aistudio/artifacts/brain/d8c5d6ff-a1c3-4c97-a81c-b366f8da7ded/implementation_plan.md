# VIP Pro Plan Activation Link, 4-Channel Pro Bot Upgrade & Dynamic `/start` Control

This update introduces a hidden one-click `/Pro-plan` activation deep link (`FILE-SHARE-YU6J-IEHU-828H`) that displays a Default VIP Banner and **"👑 Your Pro Plan Active!"** message, upgrades Pro users from 2 channels (+ 2 Admin channels) to **4 of their own Force-Join channels (removing Admin's 2 channels)**, unlocks **Unlimited Lifetime Uploads**, and gives the Admin full control over which features appear on `/start`.

## User Review & Critical Decisions

> [!IMPORTANT]
> Below are your confirmed choices from our clarification step and your latest instructions:

- **Confirmed Decision 1 — Single-Use Secret Activation Link (`FILE-SHARE-YU6J-IEHU-828H`)**:
  - Your ready-to-share activation link is:
    `https://t.me/FILE_SHARE_00_bot?start=FILE-SHARE-YU6J-IEHU-828H`
  - The secret key `FILE-SHARE-YU6J-IEHU-828H` is **completely hidden from regular users** in all public bot screens and menus.
  - Each activation link click is **single-use**: once a user clicks the link and activates their Pro Plan, that link token is marked as claimed so it cannot be reused by someone else (and the Admin can reset/re-arm the link or generate fresh single-use links anytime from the Admin Panel).
- **Confirmed Decision 2 — Default VIP Banner & "Your Pro Plan Active" Welcome Card**:
  - Clicking the activation link immediately sends a **Default VIP Gold Banner** with a rich unicorn & premium emoji description announcing **"👑 Your Pro Plan Active!"**.
- **Confirmed Decision 3 — 4 User Channels on Pro Plan (Admin's 2 Channels Removed)**:
  - **Free Users**: 2 Admin Channels + 2 User Channels (7-day file expiry).
  - **Pro Plan Users**: Admin's 2 channels are **automatically removed** from the user's bot, and the Pro user unlocks the **"➕ Add 4 Channels (Pro Plan)"** option to connect up to **4 of their own Force-Join channels**, plus **Unlimited Lifetime Uploads**.

---

## 1. Overview & Core Concept

- **What It Does**:
  1. **Hidden Secret Activation Link & Key (`FILE-SHARE-YU6J-IEHU-828H`)**: Allows the Admin to privately share a single-use deep link (`?start=FILE-SHARE-YU6J-IEHU-828H`) with a user. Clicking the link opens the bot, activates `/Pro-plan` in under 1 second, and displays the VIP Pro Banner and **"👑 Your Pro Plan Active!"** confirmation.
  2. **Pro 4-Channel Force-Join Upgrade**: Automatically removes the 2 default Admin channels from any Pro user's cloned bot (`/BOT-build`) and unlocks slots for **Channel #1, Channel #2, Channel #3, and Channel #4** owned entirely by the Pro user.
  3. **Unlimited Lifetime User Uploads**: Upgrades `/user-upload` for Pro users so their files and links are stored permanently (`is_permanent = 1`, zero 7-day auto-delete).
  4. **Admin `/start` Feature Visibility Control**: Lets the Admin toggle which features (`/BOT-build`, `/user-upload`, `/Pro-plan`, `Manage Bot Channels`, `Help`) appear when users send `/start`.
  5. **Unified Command Switching**: Ensures `/start`, `/bot_build`, `/user_upload`, and `/Pro-plan` respond immediately at any time without getting stuck in an unfinished step.
- **Target Audience**: Bot Admin and VIP/Pro Telegram users.
- **Key Value**: Gives the Admin a frictionless way to monetize or reward VIP users with lifetime storage and full 4-channel branding while keeping free users on the 2+2 channel and 7-day expiry model.

---

## 2. User Experience & Visual Design

- **Key User Flows**:
  1. **One-Click Pro Activation Link Flow**:
     - Admin sends `https://t.me/FILE_SHARE_00_bot?start=FILE-SHARE-YU6J-IEHU-828H` to a user.
     - User clicks the link and taps **Start** in Telegram.
     - Bot verifies that the single-use link is available, activates `is_pro = 1` for that user, marks the single-use activation as consumed, and sends the **Default VIP Gold Banner** with the caption:
       - **Header**: `👑💎 YOUR PRO PLAN ACTIVE! 💎👑`
       - **Unicorn & Premium Emoji Description**: Highlights **♾️ Unlimited Lifetime File & Link Uploads**, **📢 Add 4 Own Force-Join Channels (Admin Channels Removed!)**, and **⚡ 24/7 Instant Delivery**.
       - **Action Buttons**: `🟢 📤 /user-upload (♾️ Lifetime)` · `🟣 ➕ Add 4 Channels to My Bot` · `🔵 🏠 Home Screen`.
  2. **Free vs. Pro Bot Channel Management (`/BOT-build`)**:
     - **Free User Bot Home**: Shows `2 Admin Official Channels + 2 User Channels` and button `🟠 ➕ Add 2 Channels`.
     - **Pro User Bot Home**: Admin's 2 channels disappear automatically; shows `👑 Pro 4-Channel Mode (0 Admin Channels + 4 Your Channels)` and button `🟣 ➕ Add 4 Channels (Pro Unlocked)` guiding the user through Channels 1, 2, 3, and 4.
  3. **Admin `/start` Customizer & Single-Use Link Manager**:
     - Admin opens `/admin` or the Web Control Center -> sees the ready-to-copy Pro Activation Link, its single-use status (`Available` / `Used — Click to Reset for Next User`), and live toggles for every `/start` feature.
- **Visual Identity & Theme (Web Control Center)**:
  - *Aesthetic Direction*: High-contrast Dark Obsidian & Royal Gold VIP Control Center (`#0B0F19` canvas, `#111827` structural surfaces, `#F59E0B` gold and `#8B5CF6` royal purple accents).
  - *Typography & Hierarchy*: Clean geometric display headers paired with `tabular-nums` monospace formatting for secret keys, deep links, and user IDs.

---

## 3. Key Product Decisions & Trade-Offs

- **Decision 1: Single-Use Deep Link with Admin 1-Click Re-Arm**
  - *Chosen Approach*: Store `pro_plan_secret_key = "FILE-SHARE-YU6J-IEHU-828H"` and track `pro_key_used_by` / `pro_key_used_at` in SQLite. Once clicked by a user, the link is locked to that user and cannot be claimed by a second user until the Admin clicks **"🔄 Reset Single-Use Link"** (or sets a new key) in the Admin Panel.
  - *Why*: Matches your requirement for a single-use activation link while still letting you keep `"FILE-SHARE-YU6J-IEHU-828H"` as your master key format.
- **Decision 2: Zero Public Exposure of the Secret Key**
  - *Chosen Approach*: Never display `FILE-SHARE-YU6J-IEHU-828H` to non-admin users in `/start`, `/help`, `/Pro-plan`, or public simulator hints. Only the Admin Panel (protected by `ADMIN_IDS` in Telegram and the master password gate on the website) displays the copyable link.
  - *Why*: Ensures no regular user can see or guess the key unless the Admin shares the link with them.
- **Decision 3: Automatic Removal of Admin's 2 Channels on Pro Upgrade**
  - *Chosen Approach*: Update `get_combined_force_channels_for_user_bot()` so it checks `is_user_pro(owner_user_id)`. If the bot owner is on the Free plan, it returns `2 Admin Channels + 2 User Channels`. As soon as the owner activates `/Pro-plan`, it skips the 2 Admin channels and returns up to `4 User Channels` (`channel_1` through `channel_4`).

---

## 4. Technical Architecture & Data Strategy *(Technical Reference)*

### Architecture & Component Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                   TELEGRAM BOT & WEB CONTROL CENTER                        │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        ▼                                                           ▼
┌───────────────────────────────────────┐   ┌────────────────────────────────┐
│   Telegram Deep-Link & Command Router │   │   Admin Control Center UI      │
│  • /start FILE-SHARE-YU6J-IEHU-828H   │   │  • Copy Single-Use Pro Link    │
│  • /Pro-plan, /BOT-build, /user-upload│   │  • Reset Link for Next User    │
│  • Unified Conversation State Engine  │   │  • Toggle /start Features      │
└──────────────────┬────────────────────┘   └───────────────┬────────────────┘
                   │                                        │
                   └──────────────────┬─────────────────────┘
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                     SQLite Persistent Vault (bot_data.db)                  │
│  • bot_builder_config: pro_plan_secret_key ('FILE-SHARE-YU6J-IEHU-828H'),  │
│    pro_key_used_by, allow_bot_build, allow_user_upload, allow_pro_plan     │
│  • users: is_pro (0/1), pro_activated_at                                   │
│  • user_bots: channel_1..channel_4 (Free: 2 Admin + 2 User | Pro: 4 User)  │
│  • files: is_permanent (Free: 0 [7-day] | Admin & Pro: 1 [Lifetime])       │
└────────────────────────────────────────────────────────────────────────────┘
```

### Data Model & State Updates

1. **`bot_builder_config` Table**:
   - `pro_plan_secret_key`: Defaults to `"FILE-SHARE-YU6J-IEHU-828H"`.
   - `pro_key_used_by`: Stores the `user_id` that consumed the current single-use link (`0` when available/reset).
   - `pro_banner_url`: Default VIP Pro Gold Banner photo URL sent when the link is clicked.
2. **`user_bots` Table**:
   - Add `channel_3_title`, `channel_3_link`, `channel_4_title`, `channel_4_link` columns so Pro users can add 4 channels.
3. **Interactive Flows**:
   - **`/start FILE-SHARE-YU6J-IEHU-828H` (or `/start PRO_FILE-SHARE-YU6J-IEHU-828H`)**: Intercepted at the top of `start_cmd()`. Validates single-use availability, upgrades user to `is_pro = 1`, upgrades any existing files of that user to Lifetime, removes Admin channels from their user bot, and sends the **Default VIP Banner + "👑 Your Pro Plan Active!"** card.
   - **4-Channel Interactive Setup (`userbot:addch:<id>`)**: Detects if the user is Pro; if Free, collects 2 channels (`Step 1/2` -> `Step 2/2`); if Pro, collects up to 4 channels (`Step 1/4` -> `Step 4/4`, with `skip` option) and removes the 2 Admin channels.
