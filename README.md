# Anizoneflix — High-Performance Secure Multi-Bot & Content Delivery System

**Anizoneflix** is an enterprise-grade, high-performance Telegram Multi-Bot content delivery engine built with Python using Pyrogram (with Pyrogram / Pyrofork / Wzgram compatibility), FastAPI, and MongoDB Motor/PyMongo. It packages, secures, and delivers content across primary and clone database channels using shareable start tokens with automated quality and episode metadata detection.

---

## ⚡ Key Highlights & Fixes

- **Resilient Multi-DB & ID Resolution**: Decodes both raw Telegram message IDs and channel-multiplied IDs seamlessly. Prevents file delivery failures and "requested files not found" errors when files exist in database channels.
- **Unified Range & Link Engine**: Generates single file links, batch range links, list links, and auto-sorted episode groups across primary and cloned DB channels.
- **Sequential FIFO Task Queue & Rate Throttling**: Features an in-memory lock and queue registry to prevent race conditions, lock blockages, and Telegram FloodWait errors.
- **URL Verification Gate & Anti-Bypass**: Integrated shortener verification session system with countdown timer, access limits, and anti-bypass security lock.
- **Caption-First Episode & Quality Detection**: Automatically parses quality (480P, 720P, 1080P), seasons, episodes, and parts from file captions and file names.
- **Carousel & Media Streaming Support**: Interactive inline multi-file carousel delivery and streaming/download links for video files.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher
- MongoDB Instance (MongoDB Atlas or Local MongoDB)
- Telegram App `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### 2. Quick Local Setup
```bash
# Clone the repository
git clone https://github.com/AniZoneFlix/Anizoneflix.git
cd Anizoneflix

# Install dependencies
pip install -r requirements.txt

# Run unit tests to verify installation
python3 test_new_features.py
python3 test_search_collect.py

# Launch the bot engine
python3 main.py
```

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `TG_BOT_TOKEN` | Primary Telegram Bot Token from BotFather | `8672264237:AAG...` |
| `APP_ID` | Telegram App API ID | `22266643` |
| `API_HASH` | Telegram API Hash | `7d0b85b4146034511b8776ed7ff99de4` |
| `CHANNEL_ID` | Default Main Database Channel ID | `-1003748914288` |
| `OWNER_ID` | Telegram Numeric User ID of System Owner | `8646416973` |
| `DATABASE_URL` | MongoDB Connection URI | `mongodb+srv://...` |
| `DATABASE_NAME` | MongoDB Database Name | `AniZoneFlix_Bot` |
| `PORT` | Web Server Port for FastAPI / Health Checks | `8080` |
| `WEBSITE_URL` | Domain URL for Web Verification Gate & Streaming | `https://your-domain.com` |
| `SHORTENER_URL` | Default Shortener Domain | `arolinks.com` |
| `SHORTENER_API_KEY` | Default Shortener API Key | `your_api_key` |

---

## 🤖 Bot Commands Reference

### 👤 User Commands
- `/start` — Initialize or restart the bot / process start payload link.
- `/help` — Display center guidance and available commands.
- `/verify` — Check verification status or generate a new verification session.
- `/mystatus` — View active verification and premium membership countdown timer.
- `/id` — Get your Telegram user ID and group/channel chat IDs.
- `/ping` — Check bot response latency.

### 👑 Admin Commands
- `/genlink` — Generate a single or bulk secure start link.
- `/batch` — Package a range of contiguous messages into a single batch link.
- `/auto_batch` — Automatically group and batch files by quality and episode range.
- `/cbatch` — Split range into custom episode/message batches.
- `/advbatch` — Advanced multi-channel/clone auto-batch scanner and link generator.
- `/addpremium` — Grant premium access duration to users (`/addpremium user_id 30 d`).
- `/remove_premium` — Revoke premium access from specified users.
- `/premium_users` — List active premium users and remaining expiration time.
- `/addchnl` — Add required force-subscription channel.
- `/delchnl` — Remove force-subscription channel.
- `/listchnl` — List all force-subscription channels.
- `/fsub_mode` — Toggle force-sub approval request mode (`on`/`off`).
- `/count` — View today's total verification statistics and user counts.
- `/proverify` — Generate a pro verification session bypassing single-user locks.

---

## 📄 License & Credits

Released under the MIT License. Copyright (C) 2025 by **AniZoneFlix**.
