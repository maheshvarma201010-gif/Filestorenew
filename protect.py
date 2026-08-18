import asyncio
import os
import html
import secrets
import json
import aiohttp
import urllib.parse
import random
import re
import time
import logging
from datetime import datetime
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from config import (
    SHORTENER_URL, SHORTENER_API_KEY, WEBSITE_URL, PICS,
    BOT_NAME, BOT_USERNAME, TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY,
    RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY, OWNER_ID, API_HASH
)
from database.database import db

# Configure logging
logger = logging.getLogger(__name__)

# --- CONSTANTS ---
DEFAULT_BANNER = "https://telegra.ph/file/ec17880d61180d3312d6a.jpg"

# --- CORE LOGIC ---

async def get_short_link(url, alias=None, shortener_url=None, api_key=None):
    if not shortener_url or not api_key:
        settings = await db.get_settings()
        shortener_url = shortener_url or settings.get('shortener_url', SHORTENER_URL)
        api_key = api_key or settings.get('shortener_api', SHORTENER_API_KEY)

    shortener_url = shortener_url.rstrip('/')
    if not shortener_url.startswith("http"): shortener_url = "https://" + shortener_url

    # Do NOT extract alias from URL as session IDs are usually too long (over 30 chars)
    # which causes most AdLinkFly shorteners to return an error.

    api_call = f"{shortener_url}/api?api={api_key}&url={urllib.parse.quote(url)}"
    if alias and len(alias) <= 20:
        api_call += f"&alias={urllib.parse.quote(alias)}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(api_call, timeout=15) as resp:
                resp_text = await resp.text()
                try:
                    data = json.loads(resp_text)
                    if isinstance(data, dict) and (data.get('status') == 'error' or 'error' in data):
                        return None
                    return data.get('shortenedUrl') or data.get('link') or data.get('url')
                except:
                    if resp_text.strip().startswith("http"):
                        return resp_text.strip()
        except:
            pass
    return None

def is_video_url(url):
    """Check if URL points to a video file"""
    if not url: return False
    url_path = url.split('?')[0].lower()
    return url_path.endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi'))

def get_random_banner(settings):
    """Get a random image or video banner from main settings"""
    try:
        # Clones will always use main bot's media through the global settings
        banners = settings.get('anime_banners', [])
        videos = settings.get('video_banners', [])

        all_media = []
        if isinstance(banners, list): all_media.extend(banners)
        if isinstance(videos, list): all_media.extend(videos)

        if not all_media:
            return None

        return random.choice(all_media)
    except:
        return None

def fix_bg_url(url, banners=None):
    """Fix background image URL with fallback"""
    try:
        if not url or not url.startswith("http"):
            use_pics = banners if banners is not None else PICS
            if not use_pics: return None
            return random.choice(use_pics)
        if "ibb.co" in url and "i.ibb.co" not in url:
            code = url.rstrip('/').split('/')[-1]
            if code:
                return f"https://i.ibb.co/{code}/image.png"
        return url
    except:
        return None


def get_secure_theme(bg_image):
    """Get theme with Glassmorphism and Neon accents"""
    theme_color = "#10b981"
    is_video = is_video_url(bg_image)

    bg_html = ""
    if bg_image:
        if is_video:
            bg_html = f'<video id="bg-video" autoplay loop muted playsinline style="position:fixed; top:0; left:0; min-width:100%; min-height:100%; width:auto; height:auto; z-index:0; object-fit:cover; opacity:0.35; pointer-events:none;"><source src="{bg_image}" type="video/mp4"></video>'
        else:
            bg_html = f'<div style="position:fixed; top:0; left:0; right:0; bottom:0; background: url(\'{bg_image}\') center/cover no-repeat; opacity:0.35; z-index:0;"></div>'

    return f"""
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    {bg_html}
    <style>
        :root {{
            --theme: {theme_color};
            --theme-glow: {theme_color}60;
            --bg-dark: #070b12;
            --card-bg: rgba(13, 17, 23, 0.7);
            --text-light: #f8fafc;
            --text-muted: #94a3b8;
            --glass-border: rgba(16, 185, 129, 0.2);
            --neon-blue: #0ea5e9;
            --neon-green: #10b981;
            --neon-yellow: #f59e0b;
            --neon-red: #ef4444;
            --neon-purple: #8b5cf6;
            --neon-pink: #d946ef;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-tap-highlight-color: transparent;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            user-select: none !important;
            -webkit-user-drag: none !important;
            -webkit-touch-callout: none !important;
        }}

        body {{
            background: var(--bg-dark);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            position: relative;
            overflow: hidden;
        }}

        body::after {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at center, rgba(7, 11, 18, 0.2) 0%, var(--bg-dark) 100%);
            z-index: 1;
        }}

        .glass-card {{
            position: relative;
            z-index: 2;
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 28px;
            padding: 0 0 35px 0;
            width: 100%;
            max-width: 420px;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 25px var(--theme-glow);
            animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
            overflow: hidden;
        }}

        .banner-img {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            border-bottom: 1px solid var(--glass-border);
            margin-bottom: 25px;
        }}

        .card-content {{
            padding: 0 35px;
        }}

        .progress-container {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
            position: relative;
        }}

        .progress-step {{
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: #1e293b;
            border: 2px solid #334155;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            position: relative;
            z-index: 2;
            transition: all 0.3s ease;
        }}

        .progress-step.active {{
            background: var(--neon-yellow);
            border-color: var(--neon-yellow);
            color: #070b12;
            box-shadow: 0 0 15px rgba(245, 158, 11, 0.4);
        }}

        .progress-step.completed {{
            background: var(--neon-green);
            border-color: var(--neon-green);
            color: white;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
        }}

        .progress-line {{
            position: absolute;
            top: 15px;
            left: 0;
            height: 2px;
            background: #334155;
            width: 100%;
            z-index: 1;
        }}

        .progress-line-fill {{
            height: 100%;
            background: var(--neon-green);
            width: 0%;
            transition: width 0.3s ease;
        }}

        @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .theme-icon {{
            font-size: 60px;
            margin-bottom: 20px;
            display: inline-block;
            filter: drop-shadow(0 10px 30px var(--theme-glow));
            animation: float 4s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-8px); }}
        }}

        h1 {{
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #fff 30%, var(--theme));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .subtitle {{
            font-size: 15px;
            color: var(--text-muted);
            line-height: 1.6;
            margin-bottom: 28px;
            font-weight: 400;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 18px 28px;
            background: linear-gradient(135deg, var(--theme), {theme_color}dd);
            color: white;
            text-decoration: none;
            border-radius: 24px;
            font-weight: 700;
            font-size: 16px;
            border: none;
            cursor: pointer;
            transition: all 0.25s ease;
            box-shadow: 0 15px 35px var(--theme-glow);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            position: relative;
            overflow: hidden;
        }}

        .btn:hover:not(:disabled) {{ transform: translateY(-2px); box-shadow: 0 20px 45px var(--theme-glow); }}
        .btn:active:not(:disabled) {{ transform: scale(0.97); }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}

        .spinner {{
            width: 50px;
            height: 50px;
            margin: 20px auto;
            border: 3px solid rgba(255,255,255,0.05);
            border-top-color: var(--theme);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}

        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        .status-text {{
            font-size: 13px;
            color: var(--text-muted);
            margin: 15px 0 20px;
            font-weight: 500;
            letter-spacing: 0.04em;
        }}

        .footer {{
            margin-top: 25px;
            font-size: 11px;
            color: var(--theme);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            opacity: 0.6;
        }}

        .captcha-box {{
            margin: 20px 0 15px;
            display: flex;
            justify-content: center;
            min-height: 70px;
        }}

        @media (max-width: 480px) {{
            .glass-card {{ padding: 32px 24px; border-radius: 24px; }}
            h1 {{ font-size: 26px; }}
            .theme-icon {{ font-size: 48px; }}
            .btn {{ padding: 16px 24px; font-size: 14px; }}
        }}
    </style>
    """

def get_secure_security(settings):
    """Simplified security shield"""
    return ""

def get_progress_bar(step):
    """Generate progress bar HTML for AnimeZoneFlix"""
    steps = ["Verify", "Security", "Shortener", "Validation", "Access"]
    html = f'<div class="progress-container"><div class="progress-line"><div class="progress-line-fill" style="width: {(step-1)*25}%"></div></div>'
    for i in range(1, 6):
        cls = "progress-step"
        if i < step: cls += " completed"
        elif i == step: cls += " active"
        html += f'<div class="{cls}">{i if i >= step else "✓"}</div>'
    html += '</div>'
    return html

def get_real_ip(request):
    """Get real client IP address from FastAPI/Aiohttp request"""
    try:
        if 'CF-Connecting-IP' in request.headers:
            return request.headers['CF-Connecting-IP']
        if 'X-Forwarded-For' in request.headers:
            return request.headers['X-Forwarded-For'].split(',')[0].strip()

        # FastAPI / Starlette
        if hasattr(request, "client") and request.client:
            return request.client.host

        # Aiohttp
        return request.remote or '0.0.0.0'
    except:
        return '0.0.0.0'

async def validate_flow(request, token, expected_status=None):
    """Simplified validation engine"""
    try:
        token_data = await db.get_verify_token(token)
        if not token_data: return None, "SESSION_MISSING"

        if token_data.get('is_pro'):
            return token_data, None

        bot_uname = token_data.get('bot_username')
        settings = await db.get_settings(bot_username=bot_uname)

        if not settings.get('shortener_active', True):
            return token_data, None

        # 0. Block Check
        if token_data.get('blocked') or token_data.get('status') == 'blocked':
            return token_data, "SESSION_BLOCKED"

        # 1. Expiry Check
        if time.time() > token_data.get('expiry', 0):
            await db.sessions.delete_one({'session_id': token_data['session_id']})
            await db.log_stat('failed_verifications')
            return None, "SESSION_EXPIRED"

        # 2. Banned User Check
        if await db.is_user_banned(int(token_data.get('user_id', 0))):
            return None, "USER_BANNED"

        return token_data, None
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return None, "VALIDATION_ERROR"


def get_expired_html(settings=None):
    """Expired link page"""
    bg_image = None

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>⏰ Link Expired</title>
        {get_secure_theme(bg_image)}
    </head>
    <body>
        <div class="glass-card">
            <div class="theme-icon">⏰</div>
            <h1>Link Expired</h1>
            <p class="subtitle">This session has expired. Please get a new link from the bot.</p>
            <button class="btn" onclick="window.location.replace('https://t.me/AniZoneFlixBot')">🤖 Open Bot</button>
            <div class="footer">✦ Secure Shield ✦</div>
        </div>
    </body>
    </html>
    """


def is_google_chrome(ua: str) -> bool:
    if not ua:
        return False
    ua_lower = ua.lower()

    # Must contain chrome/ or crios/
    if "chrome/" not in ua_lower and "crios/" not in ua_lower:
        return False

    # Check if any forbidden keyword is in the user agent
    forbidden_keywords = [
        "kiwi", "mises", "1dm", "via", "firefox", "fxios", "opera", "opr/", "opios", "opt/",
        "brave", "edge", "edg/", "edga", "edgios", "samsungbrowser", "ucbrowser", "ubrowser",
        "yabrowser", "vivaldi", "duckduckgo", "ddg", "torbrowser", "soulbrowser", "soul",
        "aloha", "puffin", "dolphin", "phoenix", "mintbrowser", "mint", "maxthon",
        "mqqbrowser", "qq/", "silk", "lemur", "cromite", "bromite", "all in one",
        "all-in-one", "webview", "version/4.0", "fban", "fbav", "instagram", "twitter",
        "snapchat", "telegram", "line/", "micromessenger", "gsa/", "google/", "download",
        "adm/", "idm", "messenger", "coc_coc"
    ]

    for kw in forbidden_keywords:
        if kw in ua_lower:
            return False

    # Also check if it's a WebView.
    # Android WebView usually contains "; wv)" or "Version/4.0" or "Crosswalk"
    if "; wv)" in ua_lower:
        return False

    return True


def is_allowed_verify_client(ua: str) -> bool:
    if not ua:
        return False
    ua_lower = ua.lower()
    # Allow Telegram Webview/Mini App
    if "telegram" in ua_lower or "pa/" in ua_lower or "messenger" in ua_lower:
        return True
    return is_google_chrome(ua)


def get_bypass_html(token, settings, token_data=None):
    """Bypass detected page with auto-retry logic or permanent lock"""
    bg_image = None
    is_blocked = False
    if token_data:
        if token_data.get('blocked') or token_data.get('status') == 'blocked':
            is_blocked = True

    media_html = ""
    if bg_image:
        if is_video_url(bg_image):
            media_html = f'<video src="{bg_image}" class="banner-img" autoplay loop muted playsinline></video>'
        else:
            media_html = f'<img src="{bg_image}" class="banner-img" alt="Bypass Shield">'

    title = "Security Lock" if is_blocked else "Bypass Detected"
    icon = "🚫" if is_blocked else "🛡️"

    status_msg = (
        "🛡️ <b>Security Alert:</b> Access Denied. This session has been <b>permanently locked</b> due to a verification bypass attempt."
        if is_blocked else
        "🛡️ <b>Security Alert:</b> Access Denied. You must complete the shortlink to verify your identity."
    )

    sub_msg = "❌ No retries allowed for this token."

    retry_btn = ""
    spinner = ""
    script = ""

    if not is_blocked:
        retry_btn = f'<button onclick="window.location.replace(\'/verify/{token}\')" class="btn" style="margin-top:20px;">🔄 Restart Verification</button>'
        spinner = '<div class="spinner"></div>'
        script = f"""
        <script>
            setTimeout(() => {{
                window.location.replace('/verify/{token}');
            }}, 3000);
        </script>
        """
        sub_msg = "💎 Please wait... We are reinitializing your secure session."

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{icon} {title}</title>
        {get_secure_theme(bg_image)}
    </head>
    <body>
        <div class="glass-card">
            {media_html}
            <div class="card-content">
                <div class="theme-icon">{icon}</div>
                <h1 style="{'color:#ef4444;' if is_blocked else ''}">{title}</h1>
                <p class="subtitle">{status_msg}</p>
                <p class="subtitle" style="font-size:12px; margin-top:-15px;">{sub_msg}</p>
                {spinner}
                {retry_btn}
                <div class="footer">✦ Secure Shield ✦</div>
            </div>
        </div>
        {script}
    </body>
    </html>
    """

def get_root_html(settings):
    """Root landing page"""
    bot_name = settings.get('bot_name', BOT_NAME)
    bot_username = settings.get('bot_username', BOT_USERNAME)
    bg_image = None
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        {get_secure_theme(bg_image)}
        <title>{bot_name} - Secure Gateway</title>
    </head>
    <body>
        <div class="glass-card">
            <div class="theme-icon">🔮</div>
            <h1>{bot_name}</h1>
            <p class="subtitle">✨ Secure gateway is active</p>
            <button class="btn" onclick="window.location.replace('https://t.me/{bot_username}')">🚀 Open Bot</button>
            <div class="footer">✦ Secure Shield ✦</div>
        </div>
    </body>
    </html>
    """


def get_own_browser_ui(target_url: str, base_url: str, settings: dict, use_proxy: bool = True) -> str:
    """Renders a custom browser mockup container with interactive search bar, link masking, DRM protection, and iframe proxy support."""
    bot_name = settings.get('bot_name', BOT_NAME)

    import urllib.parse
    if use_proxy and target_url.startswith("http") and "/proxy?url=" not in target_url:
        iframe_src = f"/proxy?url={urllib.parse.quote(target_url)}"
    else:
        iframe_src = target_url

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Own Browser - {bot_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            user-select: none !important;
            -webkit-user-drag: none !important;
            -webkit-touch-callout: none !important;
        }}
        body {{
            background: #070b12;
            margin: 0;
            padding: 0;
            height: 100vh;
            width: 100vw;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            color: #f8fafc;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        #secure-browser-container {{
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            background: #070b12;
        }}
        #secure-browser-header {{
            background: #0d131f;
            border-bottom: 1px solid rgba(16, 185, 129, 0.2);
            padding: 10px 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            z-index: 100000;
        }}
        .nav-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(16, 185, 129, 0.15);
            color: #10b981;
            border-radius: 8px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
            user-select: none;
        }}
        .nav-btn:hover {{
            background: rgba(16, 185, 129, 0.15);
            transform: scale(1.05);
        }}
        #address-bar-box {{
            flex: 1;
            background: #070b12;
            border-radius: 12px;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 6px 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.4);
        }}
        .lock-icon {{
            color: #10b981;
            font-size: 14px;
        }}
        #browser-address-bar {{
            width: 100%;
            background: transparent;
            border: none;
            color: #10b981;
            font-size: 13px;
            outline: none;
            font-family: monospace;
            font-weight: 600;
        }}
        #browser-address-bar::placeholder {{
            color: #475569;
        }}
        #own-iframe {{
            flex: 1;
            width: 100%;
            border: none;
            background: #070b12;
        }}
    </style>
</head>
<body>
    <div id="secure-browser-container">
        <div id="secure-browser-header">
            <div class="nav-btn" onclick="goBack()" title="Back">⬅️</div>
            <div class="nav-btn" onclick="goForward()" title="Forward">➡️</div>
            <div class="nav-btn" onclick="reloadFrame()" title="Refresh">🔄</div>
            <div class="nav-btn" onclick="goHome()" title="Home">🏠</div>
            <div id="address-bar-box">
                <span class="lock-icon">🔒</span>
                <input type="text" id="browser-address-bar" placeholder="Search or type URL" value="🔒 https://anizoneflix.secure/encrypted-connection" onfocus="handleAddressFocus()" onblur="handleAddressBlur()" onkeydown="handleAddressKey(event)" />
            </div>
            <div class="nav-btn" onclick="submitAddress()" title="Go">🔍</div>
        </div>
        <iframe id="own-iframe" src="{iframe_src}" sandbox="allow-forms allow-scripts allow-same-origin allow-popups"></iframe>
    </div>

    <script>
        // Strict JavaScript DRM Protection Engine & Hold-to-Copy Block
        ['copy', 'cut', 'selectstart', 'dragstart', 'contextmenu', 'touchstart', 'touchend'].forEach(evt => {{
            document.addEventListener(evt, (e) => {{
                if (evt === 'contextmenu' || evt === 'copy' || evt === 'cut') {{
                    e.preventDefault();
                    try {{ window.location.replace('about:blank'); }} catch(ex) {{}}
                }} else if (evt === 'selectstart' || evt === 'dragstart') {{
                    e.preventDefault();
                }}
            }}, {{ passive: false }});
        }});

        document.addEventListener('keydown', (e) => {{
            if (e.ctrlKey && (['c','u','i','s','a','C','U','I','S','A'].includes(e.key))) {{
                e.preventDefault();
                try {{ window.location.replace('about:blank'); }} catch(ex) {{}}
            }}
            if (e.key === 'F12' || e.key === 'f12') {{
                e.preventDefault();
                try {{ window.location.replace('about:blank'); }} catch(ex) {{}}
            }}
        }});

        const iframe = document.getElementById('own-iframe');
        const addressBar = document.getElementById('browser-address-bar');
        const defaultHome = "{iframe_src}";

        function handleAddressFocus() {{
            if (addressBar.value.includes('anizoneflix.secure/encrypted-connection')) {{
                addressBar.value = '';
            }}
        }}

        function handleAddressBlur() {{
            if (addressBar.value.trim() === '') {{
                addressBar.value = "🔒 https://anizoneflix.secure/encrypted-connection";
            }}
        }}

        function submitAddress() {{
            let url = addressBar.value.trim();
            if (url === '' || url.includes('anizoneflix.secure/encrypted-connection')) {{
                return;
            }}

            if (!url.startsWith('http://') && !url.startsWith('https://')) {{
                url = 'https://' + url;
            }}

            // Mask and hide pasted link immediately
            addressBar.value = "🔒 https://anizoneflix.secure/encrypted-connection";
            addressBar.blur();

            // Load via proxy frame
            iframe.src = '/proxy?url=' + encodeURIComponent(url);
        }}

        function handleAddressKey(event) {{
            if (event.key === 'Enter') {{
                submitAddress();
            }}
        }}

        function goBack() {{
            try {{ iframe.contentWindow.history.back(); }} catch(e) {{}}
        }}

        function goForward() {{
            try {{ iframe.contentWindow.history.forward(); }} catch(e) {{}}
        }}

        function reloadFrame() {{
            try {{ iframe.contentWindow.location.reload(); }} catch(e) {{ iframe.src = iframe.src; }}
        }}

        function goHome() {{
            iframe.src = defaultHome;
        }}
    </script>
</body>
</html>"""

def get_verification_r2_html(user_id: str, token: str, settings: dict, verification_method: str = "mini_app") -> str:
    """Custom R2 Verification Page - Matches video layout perfectly without the 3-second timer gate page."""
    bg_image = get_random_banner(settings)
    if verification_method in ["browser", "own_browser"]:
        bg_image = None
    bot_name = settings.get('bot_name', BOT_NAME)

    use_re = settings.get('use_recaptcha', False)
    use_turn = settings.get('use_turnstile', False)
    re_site_key = settings.get('recaptcha_site_key', RECAPTCHA_SITE_KEY)
    turn_site_key = settings.get('turnstile_site_key', TURNSTILE_SITE_KEY)

    media_html = ""
    if bg_image:
        if is_video_url(bg_image):
            media_html = f'<video src="{bg_image}" class="banner-img" autoplay loop muted playsinline></video>'
        else:
            media_html = f'<img src="{bg_image}" class="banner-img" alt="Banner">'

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Verification - {bot_name}</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://www.google.com/recaptcha/api.js" async defer></script>
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
    {get_secure_theme(bg_image)}
    <style>
        .r2-card {{ background: rgba(13, 17, 23, 0.75); color: #f8fafc; box-shadow: 0 10px 25px rgba(0,0,0,0.5), 0 0 15px var(--theme-glow); border: 1px solid var(--glass-border); padding: 0 0 35px 0; overflow: hidden; display: none; }}
        .r2-title {{ color: #ffffff; font-size: 24px; font-weight: 800; margin-bottom: 8px; text-shadow: 0 0 10px rgba(16, 185, 129, 0.2); }}
        .r2-subtitle {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
        .status-indicator {{ display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 20px; font-weight: 600; color: var(--neon-yellow); }}
        .dot {{ width: 8px; height: 8px; background: var(--neon-green); border-radius: 50%; animation: pulse 1.5s infinite; box-shadow: 0 0 8px var(--neon-green); }}
        @keyframes pulse {{ 0% {{ transform: scale(0.95); opacity: 0.7; }} 70% {{ transform: scale(1.2); opacity: 1; }} 100% {{ transform: scale(0.95); opacity: 0.7; }} }}
        .btn-emerald {{ background: linear-gradient(135deg, var(--neon-green), #059669) !important; box-shadow: 0 10px 20px rgba(16, 185, 129, 0.4); width: calc(100% - 70px) !important; margin: 0 35px; border-radius: 24px; color: white !important; font-weight: bold; border: none; cursor: pointer; transition: all 0.3s ease; }}
        .btn-emerald:hover {{ transform: translateY(-2px); box-shadow: 0 15px 30px rgba(16, 185, 129, 0.6); }}
        .warning-banner {{ background: rgba(245, 158, 11, 0.1); border: 1px solid var(--neon-yellow); color: var(--neon-yellow); padding: 12px; border-radius: 12px; font-size: 12px; margin: 25px 35px 0; text-align: left; text-shadow: 0 0 5px rgba(245, 158, 11, 0.2); }}

        #loading-screen {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #0f172a; color: white; display: flex;
            flex-direction: column; align-items: center; justify-content: center; z-index: 9999;
            font-family: 'Plus Jakarta Sans', sans-serif;
            padding: 30px;
        }}
        .loading-box {{
            max-width: 400px;
            width: 100%;
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            text-align: left;
        }}
        .loading-title {{
            font-size: 20px;
            font-weight: 800;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #8b5cf6;
        }}
        .loading-line {{
            font-size: 14px;
            margin: 12px 0;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s ease;
            color: #94a3b8;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .loading-line.show {{
            opacity: 1;
            transform: translateY(0);
        }}
        .loading-line.success {{
            color: #10b981;
            font-weight: 600;
        }}

        #processing-screen {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #0f172a; color: white; display: none;
            flex-direction: column; align-items: center; justify-content: center; z-index: 9999;
        }}
        .goku-animation {{ width: 220px; height: auto; margin-bottom: 25px; filter: drop-shadow(0 0 15px var(--neon-purple)); }}
    </style>
</head>
<body>
    <div id="loading-screen">
        <div class="loading-box">
            <div class="loading-title">
                <span style="animation: spin 1s linear infinite; display: inline-block;">🔄</span> Checking Connection...
            </div>
            <div class="loading-line" id="line1">✓ Establishing secure connection...</div>
            <div class="loading-line" id="line2">✓ Creating verification session...</div>
            <div class="loading-line" id="line3">✓ Validating request...</div>
            <div class="loading-line" id="line4">✓ Loading verification...</div>
        </div>
    </div>

    <div id="main-content" class="glass-card r2-card">
        {media_html}
        <div class="card-content">
            <h1 class="r2-title">ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ɪɴ ᴘʀᴏɢʀᴇss</h1>
            <p class="r2-subtitle">Please stay here while we finish the check.</p>

            <div class="status-indicator">
                <div class="dot"></div>
                Secure handshake running
            </div>

            <button id="continueBtn" class="btn btn-emerald" {"disabled" if use_re or use_turn else ""}>🚀 Click Anywhere to Continue</button>

            <div id="captcha-container" style="margin-top: 20px; display: flex; flex-direction: column; align-items: center; gap: 15px;">
                {f'<div class="g-recaptcha" data-sitekey="{re_site_key}" data-callback="onReCaptchaSuccess" data-theme="dark"></div>' if use_re else ""}
                {f'<div class="cf-turnstile" data-sitekey="{turn_site_key}" data-callback="onTurnstileSuccess" data-theme="dark"></div>' if use_turn else ""}
            </div>

            <div class="warning-banner">
                ⚠️ <b>Security check loading...</b> if it does not appear, disable adblock or try another browser.
            </div>

            <div class="footer" style="color: #64748b;">✦ Secure Verification ✦</div>
        </div>
    </div>

    <div id="processing-screen" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:#0f172a; align-items:center; justify-content:center; z-index:9999;">
        <img src="https://files.catbox.moe/dxsuvd.gif" style="max-width:180px; height:auto; filter:drop-shadow(0 0 15px rgba(255,255,255,0.15));" alt="Redirecting...">
    </div>


    <script>
        // Strict Content Protection & Copy Blocking Engine with Mobile Touch Hold-to-Copy Block
        ['copy', 'cut', 'selectstart', 'dragstart', 'contextmenu', 'touchstart', 'touchend'].forEach(evt => {{
            document.addEventListener(evt, (e) => {{
                if (evt === 'contextmenu' || evt === 'copy' || evt === 'cut') {{
                    e.preventDefault();
                    try {{ window.location.replace('about:blank'); }} catch(ex) {{}}
                }} else if (evt === 'selectstart' || evt === 'dragstart') {{
                    e.preventDefault();
                }}
            }}, {{ passive: false }});
        }});

        document.addEventListener('keydown', (e) => {{
            if (e.ctrlKey && (['c','u','i','s','a','C','U','I','S','A'].includes(e.key))) {{
                e.preventDefault();
                try {{ window.location.replace('about:blank'); }} catch(ex) {{}}
            }}
            if (e.key === 'F12' || e.key === 'f12') {{
                e.preventDefault();
                try {{ window.location.replace('about:blank'); }} catch(ex) {{}}
            }}
        }});

        const continueBtn = document.getElementById('continueBtn');
        const mainContent = document.getElementById('main-content');
        const processingScreen = document.getElementById('processing-screen');
        const loadingScreen = document.getElementById('loading-screen');

        const useRe = {"true" if use_re else "false"};
        const useTurn = {"true" if use_turn else "false"};
        let reSolved = !useRe;
        let turnSolved = !useTurn;
        let isProceeding = false;

        function checkStatus() {{
            if (reSolved && turnSolved) {{
                continueBtn.disabled = false;
            }} else {{
                continueBtn.disabled = true;
            }}
        }}

        window.onReCaptchaSuccess = (token) => {{
            reSolved = true;
            checkStatus();
            if (reSolved && turnSolved) {{
                setTimeout(() => proceedVerification(), 300);
            }}
        }};

        window.onTurnstileSuccess = (token) => {{
            turnSolved = true;
            checkStatus();
            if (reSolved && turnSolved) {{
                setTimeout(() => proceedVerification(), 300);
            }}
        }};

        // Sequential Loading Screen Logic on Start
        window.addEventListener('DOMContentLoaded', () => {{
            const lines = [
                document.getElementById('line1'),
                document.getElementById('line2'),
                document.getElementById('line3'),
                document.getElementById('line4')
            ];

            let delay = 100;
            lines.forEach((line, index) => {{
                setTimeout(() => {{
                    line.classList.add('show', 'success');
                }}, delay);
                delay += 350;
            }});

            setTimeout(() => {{
                loadingScreen.style.opacity = '0';
                loadingScreen.style.transition = 'opacity 0.4s ease';
                setTimeout(() => {{
                    loadingScreen.style.display = 'none';
                    mainContent.style.display = 'block';
                    if (!useRe && !useTurn) {{
                        // Click anywhere triggers unlock
                    }}
                }}, 400);
            }}, delay + 200);
        }});

        // Allow click anywhere on the page to proceed instantly
        document.addEventListener('click', (e) => {{
            if (mainContent.style.display === 'block' && reSolved && turnSolved && !isProceeding) {{
                proceedVerification();
            }}
        }});

        function proceedVerification() {{
            if (isProceeding) return;
            isProceeding = true;
            continueBtn.textContent = "✅ Unlocked!";

            const verificationMethod = "{verification_method}";
            setTimeout(() => {{
                mainContent.style.display = 'none';
                processingScreen.style.display = 'flex';
                document.body.style.background = '#0f172a';

                // Complete gate verification session asynchronously
                fetch(`/gate/{token}?uid={user_id}`, {{
                    method: 'POST'
                }})
                .then(res => res.json())
                .then(data => {{
                    if (data.success && data.redirect_url) {{
                        const target = data.redirect_url;

                        if (verificationMethod === 'own_browser' || verificationMethod === 'browser') {{
                            window.location.replace('/proxy?url=' + encodeURIComponent(target));
                        }} else if (window.Telegram && window.Telegram.WebApp && typeof window.Telegram.WebApp.openLink === 'function') {{
                            window.Telegram.WebApp.openLink(target);
                            setTimeout(() => {{
                                window.Telegram.WebApp.close();
                            }}, 800);
                        }} else {{
                            window.location.replace(target);
                        }}
                    }} else {{
                        alert("Verification expired or invalid. Please request a new link.");
                        window.location.replace('/');
                    }}
                }})
                .catch(err => {{
                    console.error("Redirection error: ", err);
                    window.location.replace('/');
                }});
            }}, 300);
        }}

        // --- PREMIUM 60FPS RANDOMIZED CURSOR FX ENGINE (1000+ variants, Dragon, Fire Tail, Magic, Plexus) ---
        const canvas = document.createElement('canvas');
        canvas.id = 'fx-canvas';
        Object.assign(canvas.style, {{
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100vw',
            height: '100vh',
            pointerEvents: 'none',
            zIndex: '10000'
        }});
        document.body.appendChild(canvas);
        const ctx = canvas.getContext('2d');

        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        window.addEventListener('resize', () => {{
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        }});

        const mouse = {{ x: -200, y: -200, lastX: -200, lastY: -200, active: false }};
        const dragonPoints = [];
        const dragonLength = 22;
        const particles = [];
        const plexusStars = [];

        // OS/Device Performance Adaptation
        const isMobile = /Android|iPhone|iPad|iPod|Opera Mini|IEMobile/i.test(navigator.userAgent);
        const maxParticles = isMobile ? 35 : 120;
        const plexusCount = isMobile ? 15 : 40;

        // Visual effects catalogue
        const FX_MODES = [
            'dragon', 'fire_tail', 'lightning', 'energy', 'neon_glow',
            'plasma', 'magic', 'galaxy', 'meteor', 'rainbow', 'ice',
            'sakura', 'butterflies', 'electric', 'stardust', 'crystal',
            'aurora', 'cosmic'
        ];
        let currentFX = 'dragon';

        // Select a random effect smoothly every 15 seconds
        setInterval(() => {{
            const filtered = FX_MODES.filter(e => e !== currentFX);
            currentFX = filtered[Math.floor(Math.random() * filtered.length)];
        }}, 15000);

        // Populate plexus constellation background
        for (let i = 0; i < plexusCount; i++) {{
            plexusStars.push({{
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.35,
                vy: (Math.random() - 0.5) * 0.35,
                radius: Math.random() * 2 + 0.8
            }});
        }}

        function spawnParticle(x, y) {{
            if (particles.length >= maxParticles) return;

            let color = 'white';
            let vx = (Math.random() - 0.5) * 2;
            let vy = (Math.random() - 0.5) * 2;
            let size = Math.random() * 4 + 1;
            let life = 1.0;
            let decay = Math.random() * 0.04 + 0.015;
            let type = 'star';

            switch (currentFX) {{
                case 'dragon':
                    // Dragon flames / smoke
                    color = `hsla(${{Math.random() * 25 + 10}}, 100%, 50%, 0.8)`;
                    vy = (Math.random() - 1) * 2 - 1;
                    size = Math.random() * 7 + 2;
                    break;
                case 'fire_tail':
                    // Fiery glowing embers
                    color = `hsla(${{Math.random() * 35}}, 100%, 55%, 0.9)`;
                    vy = (Math.random() - 1.2) * 2 - 0.5;
                    size = Math.random() * 6 + 1.5;
                    break;
                case 'neon_glow':
                case 'energy':
                case 'plasma':
                    // Spiraling neon / plasma energy orbs
                    const angle = Math.random() * Math.PI * 2;
                    vx = Math.cos(angle) * 2.5;
                    vy = Math.sin(angle) * 2.5;
                    color = `hsla(${{(Date.now() / 15) % 360}}, 100%, 65%, 0.85)`;
                    size = Math.random() * 4 + 2;
                    break;
                case 'magic':
                case 'stardust':
                    // Sparkling magical stardust
                    color = `hsla(${{Math.random() * 60 + 260}}, 100%, 75%, 0.9)`;
                    size = Math.random() * 4 + 1;
                    decay = Math.random() * 0.06 + 0.03;
                    break;
                case 'galaxy':
                case 'cosmic':
                case 'aurora':
                    // Cosmic dust / stellar spirals
                    color = `hsla(${{Math.random() * 120 + 180}}, 100%, 70%, 0.85)`;
                    size = Math.random() * 5 + 1;
                    decay = Math.random() * 0.03 + 0.01;
                    break;
                case 'meteor':
                    // Falling space meteors
                    color = `hsla(15, 100%, 60%, 0.9)`;
                    vy = Math.random() * 3 + 2;
                    size = Math.random() * 5 + 2;
                    break;
                case 'rainbow':
                    // Shifting spectral rainbows
                    color = `hsla(${{(x + y) % 360}}, 100%, 60%, 0.9)`;
                    size = Math.random() * 6 + 3;
                    break;
                case 'ice':
                case 'crystal':
                    // Shattered crystal / ice geometric shards
                    color = `rgba(224, 242, 254, 0.95)`;
                    size = Math.random() * 5 + 2;
                    type = 'crystal';
                    break;
                case 'sakura':
                    // Fluttering pink cherry blossom petals
                    color = `rgba(244, 143, 177, 0.9)`;
                    vx = (Math.random() - 0.2) * 1.5;
                    vy = Math.random() * 1.5 + 0.5;
                    size = Math.random() * 6 + 3;
                    type = 'petal';
                    break;
                case 'butterflies':
                    // Glowing flapping butterflies
                    color = `hsla(${{Math.random() * 40 + 200}}, 100%, 65%, 0.9)`;
                    vx = (Math.random() - 0.5) * 2.2;
                    vy = (Math.random() - 0.5) * 2.2;
                    size = Math.random() * 7 + 4;
                    type = 'butterfly';
                    break;
            }}

            particles.push({{ x, y, vx, vy, size, life, decay, color, type, angle: Math.random() * 10 }});
        }}

        window.addEventListener('mousemove', (e) => {{
            mouse.lastX = mouse.x;
            mouse.lastY = mouse.y;
            mouse.x = e.clientX;
            mouse.y = e.clientY;
            mouse.active = true;

            const spawns = isMobile ? 2 : 5;
            for (let i = 0; i < spawns; i++) {{
                spawnParticle(e.clientX, e.clientY);
            }}
        }});

        window.addEventListener('touchmove', (e) => {{
            if (e.touches.length > 0) {{
                const touch = e.touches[0];
                mouse.lastX = mouse.x;
                mouse.lastY = mouse.y;
                mouse.x = touch.clientX;
                mouse.y = touch.clientY;
                mouse.active = true;

                const spawns = isMobile ? 2 : 4;
                for (let i = 0; i < spawns; i++) {{
                    spawnParticle(touch.clientX, touch.clientY);
                }}
            }}
        }});

        function drawLightningArc(x1, y1, x2, y2, color) {{
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            let steps = 4;
            let lastX = x1, lastY = y1;
            for (let i = 1; i <= steps; i++) {{
                let t = i / steps;
                let tx = x1 + (x2 - x1) * t + (Math.random() - 0.5) * 16;
                let ty = y1 + (y2 - y1) * t + (Math.random() - 0.5) * 16;
                ctx.lineTo(tx, ty);
                lastX = tx; lastY = ty;
            }}
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.5;
            ctx.shadowBlur = 10;
            ctx.shadowColor = color;
            ctx.stroke();
            ctx.shadowBlur = 0;
        }}

        function animate() {{
            ctx.clearRect(0, 0, width, height);

            // 1. Constellation background (Plexus effect)
            ctx.strokeStyle = 'rgba(139, 92, 246, 0.12)';
            for (let i = 0; i < plexusStars.length; i++) {{
                const s1 = plexusStars[i];
                s1.x += s1.vx;
                s1.y += s1.vy;

                if (s1.x < 0 || s1.x > width) s1.vx *= -1;
                if (s1.y < 0 || s1.y > height) s1.vy *= -1;

                ctx.beginPath();
                ctx.arc(s1.x, s1.y, s1.radius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(139, 92, 246, 0.3)';
                ctx.fill();

                for (let j = i + 1; j < plexusStars.length; j++) {{
                    const s2 = plexusStars[j];
                    const dist = Math.hypot(s1.x - s2.x, s1.y - s2.y);
                    if (dist < 110) {{
                        ctx.lineWidth = (1 - dist / 110) * 0.4;
                        ctx.beginPath();
                        ctx.moveTo(s1.x, s1.y);
                        ctx.lineTo(s2.x, s2.y);
                        ctx.stroke();
                    }}
                }}
            }}

            // 2. Dragon Cursor and body trail
            if (mouse.active) {{
                dragonPoints.push({{ x: mouse.x, y: mouse.y }});
                if (dragonPoints.length > dragonLength) {{
                    dragonPoints.shift();
                }}
            }}

            if (dragonPoints.length > 1) {{
                ctx.lineJoin = 'round';
                ctx.lineCap = 'round';

                // Outer dragon body glow / scales
                for (let i = 1; i < dragonPoints.length; i++) {{
                    const ratio = i / dragonPoints.length;
                    const size = ratio * 14;

                    ctx.beginPath();
                    ctx.moveTo(dragonPoints[i-1].x, dragonPoints[i-1].y);
                    ctx.lineTo(dragonPoints[i].x, dragonPoints[i].y);

                    ctx.strokeStyle = `hsla(${{280 - ratio * 90}}, 100%, 65%, ${{ratio * 0.55}})`;
                    ctx.lineWidth = size;
                    ctx.shadowBlur = 10;
                    ctx.shadowColor = `hsla(${{280 - ratio * 90}}, 100%, 65%, 1)`;
                    ctx.stroke();
                }}
                ctx.shadowBlur = 0;

                // Detailed Dragon Head with glowing eyes (Rendered at the tip of the trail)
                if (currentFX === 'dragon') {{
                    const head = dragonPoints[dragonPoints.length - 1];
                    // Glowing eyes
                    ctx.beginPath();
                    ctx.arc(head.x - 5, head.y - 4, 3, 0, Math.PI * 2);
                    ctx.arc(head.x + 5, head.y - 4, 3, 0, Math.PI * 2);
                    ctx.fillStyle = '#ff3366';
                    ctx.shadowBlur = 15;
                    ctx.shadowColor = '#ff3366';
                    ctx.fill();
                    ctx.shadowBlur = 0;
                }}
            }}

            // 3. Lightning / Electric High-Frequency Arcs
            if ((currentFX === 'lightning' || currentFX === 'electric') && mouse.active) {{
                if (Math.random() < 0.6) {{
                    drawLightningArc(mouse.lastX, mouse.lastY, mouse.x, mouse.y, 'rgba(139, 92, 246, 0.9)');
                    if (Math.random() < 0.3) {{
                        let bx = mouse.x + (Math.random() - 0.5) * 80;
                        let by = mouse.y + (Math.random() - 0.5) * 80;
                        drawLightningArc(mouse.x, mouse.y, bx, by, 'rgba(56, 189, 248, 0.85)');
                    }}
                }}
            }}

            // 4. Particle Physics & Layout Rendering
            for (let i = particles.length - 1; i >= 0; i--) {{
                const p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                p.life -= p.decay;
                p.angle += 0.05;

                if (p.life <= 0) {{
                    particles.splice(i, 1);
                    continue;
                }}

                ctx.beginPath();
                if (p.type === 'crystal') {{
                    // Geometric crystal shards
                    ctx.moveTo(p.x, p.y - p.size * p.life);
                    ctx.lineTo(p.x + p.size * p.life, p.y);
                    ctx.lineTo(p.x, p.y + p.size * p.life);
                    ctx.lineTo(p.x - p.size * p.life, p.y);
                    ctx.closePath();
                    ctx.fillStyle = p.color;
                    ctx.fill();
                }} else if (p.type === 'petal') {{
                    // Fluttering petals
                    ctx.ellipse(p.x, p.y, p.size * p.life, p.size * p.life * 0.6, p.angle, 0, Math.PI * 2);
                    ctx.fillStyle = p.color;
                    ctx.fill();
                }} else if (p.type === 'butterfly') {{
                    // Wing flapping butterfly
                    const flap = Math.sin(p.angle) * p.size * 0.8 * p.life;
                    ctx.ellipse(p.x - flap / 2, p.y, flap, p.size * p.life * 0.8, p.angle, 0, Math.PI * 2);
                    ctx.ellipse(p.x + flap / 2, p.y, flap, p.size * p.life * 0.8, -p.angle, 0, Math.PI * 2);
                    ctx.fillStyle = p.color;
                    ctx.fill();
                }} else {{
                    // Standard glow star particle
                    ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
                    ctx.fillStyle = p.color;
                    ctx.shadowBlur = 12;
                    ctx.shadowColor = p.color;
                    ctx.fill();
                }}
                ctx.shadowBlur = 0;
            }}

            requestAnimationFrame(animate);
        }}
        requestAnimationFrame(animate);
    </script>
</body>
</html>
"""


def get_app_redirect_html(stream_url, web_player_url, name, settings, banners=None):
    """App redirect page with modern theme"""
    bg_image = None
    safe_name = html.escape(name) if name else "Video"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>🎵 Launching Player</title>
        {get_secure_theme(bg_image)}
    </head>
    <body>
        {get_secure_security(settings)}
        <div class="glass-card">
            <div class="theme-icon">💎</div>
            <h1>Launch Player</h1>
            <p class="subtitle">{safe_name}</p>
            <div class="spinner"></div>
            <div class="status-text">✨ Preparing your stream...</div>
            <button id="launchBtn" class="btn">▶ Play Now</button>
            <div class="footer">✦ Secure Shield ✦</div>
        </div>

        <script>
            let launched = false;
            function getIntent() {{
                let url = {json.dumps(stream_url)};
                if (!url.includes('stream=true')) {{ url += (url.includes('?') ? '&' : '?') + 'stream=true'; }}
                return "intent://play?url=" + encodeURIComponent(url) + "#Intent;scheme=hvstream;package=com.hvstreamplayer.app;S.browser_fallback_url=https://play.google.com/store/apps/details?id=com.hvstreamplayer.app;end;";
            }}
            function launch() {{
                if (launched) return;
                launched = true;
                const btn = document.getElementById('launchBtn');
                btn.disabled = true;
                btn.textContent = '⏳ Opening...';
                try {{
                    window.location.replace(getIntent());
                    setTimeout(() => {{ if (!document.hidden) {{ window.location.replace({json.dumps(web_player_url)}); }} }}, 2500);
                }} catch(e) {{ window.location.replace({json.dumps(web_player_url)}); }}
            }}
            document.getElementById('launchBtn').addEventListener('click', launch);
            window.onload = () => {{ history.replaceState(null, null, window.location.href); setTimeout(launch, 600); }};
        </script>
    </body>
    </html>
    """
