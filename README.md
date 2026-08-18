# Anizoneflix — High-Performance Secure Multi-Bot & Content Delivery System

Anizoneflix is a production-ready, ultra-fast, and highly reliable Telegram Multi-Bot content delivery engine built in Python using Pyrogram (and compatible pyrofork/wzgram) and MongoDB. It secures, groups, and packages content files across primary and cloned DB channels into secure, shared, shareable file-sharing start tokens/links with advanced episode metadata detection.

---

## 🚀 Key Features

- **Unified Shared Range/Link Engine**: Shares a core token parsing, range validation, and link generation engine across all commands.
- **Robust Multi-Admin State Manager**: Session-isolated conversation manager with automatic inactivity cleanup. No fragile globals.
- **Priority Metadata Extraction**: Captions are prioritized over filenames to capture full descriptive file names and complete HTML/Markdown original captions without truncation.
- **Caption-First Episode Detection**: Seamless extraction of seasons, episodes, and parts from file names and captions. Includes sanitization of emojis, graphic symbols, and common noise like `1080p`, `x264`, and `2026`.
- **Primary & Cloned DB Channel Mappings**: Automatically identifies which DB bot/channel configuration owns the supplied message ranges and produces links under that specific bot's context.

---

## 🛠️ Installation & Quick Start

### 1. Prerequisites
- Python 3.10+
- MongoDB instance (Atlas or Local)
- Telegram App API ID and API Hash

### 2. Local Setup
Clone the repository and install all required dependencies:
```bash
git clone https://github.com/AniZoneFlix/Anizoneflix.git
cd Anizoneflix
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the repository root:
```env
TG_BOT_TOKEN=8672264237:AAG...
APP_ID=22266643
API_HASH=7d0b85b4146034511b8776ed7ff99de4
CHANNEL_ID=-1003748914288
OWNER_ID=8646416973
DATABASE_URL=mongodb+srv://...
DATABASE_NAME=AniZoneFlix_Bot
```

### 4. Run the Bot
```bash
python main.py
```

---

## ⚙️ DB Bot / Cloned Channels Mapping

Each clone bot can manage its own unique database channels. Primary and clone DB bots can be registered using `/dbchnl`.
```
DB Bot A  ──> DB Channel A (cid: -1004446716010)
DB Bot B  ──> DB Channel B (cid: -1003903003195)
```
When an admin invokes an advanced range command (`/advbatch`) targeting `https://t.me/c/4446716010/...`, the core DB resolver detects the channel, resolves the owner to DB Bot A, and initiates links on behalf of DB Bot A.

---

## 📦 Admin Commands Reference

All commands listed below are restricted strictly to configured bot admins and the system owner. Unauthorized requests receive a clean `Access Denied` permission message and abort instantly.

All commands support **Reply Mode**: replying to any message containing Telegram links will automatically extract and process them.

### 1. `/genlink`
Generates a secure, protected single file-store start link.
- **Syntax**: `/genlink [link]` or `/genlink [link1] [link2] ...` (supports Bulk mode)
- **Single Example**: `/genlink https://t.me/c/4446716010/37150`
- **Bulk Example**:
  ```
  /genlink https://t.me/c/4446716010/37150
  https://t.me/c/4446716010/37151
  ```
- **Expected Output**:
  ```
  ╭─── ✦ LINK GENERATED ✦ ───╮

  Original Link:
  https://t.me/c/4446716010/37150

  Filename:
  Naruto Shippuden S01E01 Uncut

  Filecaption:
  Naruto Shippuden - S01E01 - Complete Episode Dual Audio

  🔗 Link:
  `https://t.me/AniZoneFlix_Bot?start=get-3715000000`

  ╰──────────────────────────╯
  ```

---

### 2. `/batch`
Packages a range of contiguous messages into a single shareable link.
- **Syntax**: `/batch [start_link]-[end_link]` or `/batch [start_link]-[end_msg_id]` (Short Range format)
- **Single Range Example**: `/batch https://t.me/c/4446716010/22294-https://t.me/c/4446716010/22341`
- **Short Range Example**: `/batch https://t.me/c/4446716010/22294-22341`
- **Expected Output**:
  ```
  ╭─── ✦ BATCH GENERATED ✦ ───╮

  Original RANGE Link:
  https://t.me/c/4446716010/22294-22341

  FIRST Filename:
  Naruto Shippuden S01E01

  FIRST Filecaption:
  Naruto Shippuden - S01E01 - Enter Naruto Uzumaki!

  LAST FILENAME:
  Naruto Shippuden S01E12

  LAST FILECAPTION:
  Naruto Shippuden - S01E12 - Battle on the Bridge!

  🔗 Link:
  `https://t.me/AniZoneFlix_Bot?start=get-2229400000-2234100000`

  ╰──────────────────────────╯
  ```

---

### 3. `/auto_batch`
Intelligently scan a contiguous range, detect episodes, and sort/group them into discrete chunks by quality.
- **Syntax**: `/auto_batch [range]` (Supports multiple ranges for bulk queueing)
- **Workflow**:
  1. Admin invokes `/auto_batch https://t.me/c/4446716010/22294-22341`.
  2. Bot sends a new message asking: `How many episodes should be included in total?` (Admin types: `12`).
  3. Bot sends a new message asking: `Send the anime name:` (Admin types: `Naruto`).
  4. Once confirmed via confirmation buttons, task is added to the sequential FIFO worker queue.
- **Episode Detection Priorities & Patterns**:
  - Priority 1: File Caption. Priority 2: Filename fallback.
  - Supported: `S01E01`, `E01`, `EP01`, `Episode 1`, `Marriagetoxin S02 pt3`.
  - Cleans spaces, punctuation, underscores (`_`), dashes (`-`), and strip-ignores graphic symbols and common keywords (`1080p`, `x264`, `hevc`).
- **Expected Output**:
  ```
  🎬 Quality: 1080P
  📦 Range: 1 → 12
  FIRST Caption: Naruto Shippuden S01E01 Uncut 1080p
  LAST Caption: Naruto Shippuden S01E12 1080p
  🔗 Link: `https://t.me/AniZoneFlix_Bot?start=get-222940000-223410000`
  ```

---

### 4. `/cbatch`
Divides a single large range into custom batches as specified by the admin.
- **Syntax**: `/cbatch [range]`
- **Workflow**:
  1. Admin enters `/cbatch https://t.me/c/4446716010/22294-22341`.
  2. Bot sends a message prompting: `Send custom ranges in this format: 1-12,13-79`.
  3. Admin sends: `22294-22300,22301-22341`.
- **Expected Output**:
  Generates discrete batch blocks and separate start links for each custom range.

---

### 5. `/advbatch`
Advanced version of `/auto_batch`.
- **Difference from `/auto_batch`**:
  - `/auto_batch` is bound to the current bot's configured default channels.
  - `/advbatch` parses multiple channels/clones DB links, determines the owning bot configuration using mapping lookups, uses that clone bot's client session for scanning, and generates links targeting that clone bot!
- **Bulk workflow**:
  Sequentially collects total episodes count and anime name for each provided bulk range, presents a combined summary, then starts concurrent parallel operations within safety rate limits.

---

## ⚠️ Robust Error Handling & Validation

Admins will never receive raw python traceback blocks. All standard errors are mapped gracefully:
- **Invalid Link**: `❌ Invalid Telegram Link. Please use a valid format like: https://t.me/channel/123`
- **Message Inaccessible**: `❌ Unable to access message. The message may be deleted, restricted, or inaccessible.`
- **Empty Range**: `❌ No valid messages were found in this range.`
- **DB Resolution Fail**: `❌ No configured DB bot or channel was found for this source.`

---

## ⚡ Performance Optimization

1. **Sequential Message Chunking**: Large ranges are fetched in chunked blocks of 50 messages to keep memory and API execution light.
2. **Smooth Throttling Delay**: Small sleeps (0.02s per message, 0.1s between chunks) protect the bot against flood wait exceptions during heavy auto batch runs.
3. **FIFO Serialization Worker**: Tasks are queued in an in-memory queue to guarantee the event loop is never blocked and tasks complete successfully without race conditions.
