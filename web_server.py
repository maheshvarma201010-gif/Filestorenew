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
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, Query, Path, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import (
    SHORTENER_URL, SHORTENER_API_KEY, WEBSITE_URL, PICS, 
    BOT_NAME, BOT_USERNAME, TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY, 
    RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY, OWNER_ID
)
from database.database import db
from helper_func import generate_stream_hash, get_messages
from protect import (
    get_short_link, validate_flow, get_root_html, get_bypass_html,
    get_expired_html, get_app_redirect_html,
    get_verification_r2_html,
    get_real_ip, fix_bg_url, get_secure_theme, get_random_banner,
    is_google_chrome, is_allowed_verify_client
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Anizoneflix Secure API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RATE LIMITING ---
RATE_LIMITS = {} # {ip: {timestamp: count}}

async def check_rate_limit(request: Request, limit=10, window=60):
    """Simple IP-based rate limiting with cleanup"""
    ip = get_real_ip(request)
    now = time.time()

    # Cleanup RATE_LIMITS occasionally (every 100 requests roughly)
    if random.random() < 0.01:
        to_del = [k for k, v in RATE_LIMITS.items() if now - v['start'] > window * 2]
        for k in to_del: del RATE_LIMITS[k]

    if ip not in RATE_LIMITS:
        RATE_LIMITS[ip] = {'start': now, 'count': 1}
        return True

    if now - RATE_LIMITS[ip]['start'] > window:
        RATE_LIMITS[ip] = {'start': now, 'count': 1}
        return True

    RATE_LIMITS[ip]['count'] += 1
    if RATE_LIMITS[ip]['count'] > limit:
        settings = await db.get_settings() or {}
        bg_image = get_random_banner(settings)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>⏳ Rate Limited</title>
            {get_secure_theme(bg_image)}
        </head>
        <body>
            <div class="glass-card">
                <div class="theme-icon">⏳</div>
                <h1>Rate Limited</h1>
                <p class="subtitle">Too many requests. Please wait a minute before trying again.</p>
                <div class="footer">✦ Secure Shield ✦</div>
            </div>
        </body>
        </html>
        """
        raise HTTPException(status_code=429, detail=html_content)
    return True

# --- UTILITY FUNCTIONS ---

async def trace_shortlink(url: str) -> str:
    """
    Traces the original shortlink using:
    1. curl -IL "url" (follows redirects, gets Location headers)
    2. curl -s "url" | grep -oE "https?://[a-zA-Z0-9./?=&_-]+" (extracts links from response body)
    Returns the last resolved/traced URL, or the original url if no new URL is found.
    """
    import shlex
    from proxy_manager import proxy_manager
    logger.info(f"Tracing shortlink: {url}")
    last_url = url

    proxy = proxy_manager.get_proxy()
    proxy_arg = ""
    if proxy:
        escaped_proxy = shlex.quote(proxy)
        proxy_arg = f"-x {escaped_proxy} "

    # Method 1: curl -IL to trace Location headers
    try:
        escaped_url = shlex.quote(url)
        cmd = f'curl {proxy_arg}-A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" -IL -m 10 {escaped_url}'
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode('utf-8', errors='ignore')

        locations = re.findall(r'(?i)location:\s*([^\r\n]+)', stdout_str)
        if locations:
            candidate = locations[-1].strip()
            if candidate.startswith("http"):
                last_url = candidate
                logger.info(f"Method 1 (curl -IL) traced last URL: {last_url}")
    except Exception as e:
        logger.error(f"Error in trace_shortlink Method 1: {e}")

    # Method 2: curl -s -L (Follows and captures HTML content for Python regex parsing)
    try:
        escaped_url = shlex.quote(last_url)
        cmd = f'curl {proxy_arg}-A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" -s -L -m 10 {escaped_url}'
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode('utf-8', errors='ignore')

        target_url = None

        # 1. Parse window.location.href or window.location
        match = re.search(r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\']+)["\']', stdout_str, re.IGNORECASE)
        if match:
            target_url = match.group(1)
            logger.info(f"Found window.location redirect: {target_url}")

        # 2. Parse location.replace
        if not target_url:
            match = re.search(r'location\.replace\(\s*["\'](https?://[^"\']+)["\']\s*\)', stdout_str, re.IGNORECASE)
            if match:
                target_url = match.group(1)
                logger.info(f"Found location.replace redirect: {target_url}")

        # 3. Parse meta refresh url
        if not target_url:
            match = re.search(r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\'][^"\']*url=(https?://[^"\']+)["\']', stdout_str, re.IGNORECASE)
            if match:
                target_url = match.group(1)
                logger.info(f"Found meta refresh redirect: {target_url}")

        # 4. Parse custom Opening Link anchor
        if not target_url:
            match = re.search(r'Opening Link<br/><a\s+href=["\'](https?://[^"\']+)["\']', stdout_str, re.IGNORECASE)
            if match:
                target_url = match.group(1)
                logger.info(f"Found Opening Link click redirect: {target_url}")

        # 5. Fallback: Parse general URLs if we are still on a shortener intermediary page
        if not target_url:
            if any(domain in last_url for domain in ["arolinks.com", "babylinks.in", "vplinks.in"]):
                found_urls = re.findall(r'(https?://[a-zA-Z0-9./?=&_-]+)', stdout_str)
                for u in reversed(found_urls):
                    cleaned_u = u.strip().rstrip('"\'')
                    if cleaned_u != last_url and not any(domain in cleaned_u for domain in ["arolinks.com", "babylinks.in", "vplinks.in"]):
                        target_url = cleaned_u
                        break

        if target_url:
            last_url = target_url
            logger.info(f"Method 2 (HTML parsing) traced last URL: {last_url}")
    except Exception as e:
        logger.error(f"Error in trace_shortlink Method 2: {e}")

    return last_url


def get_base_url(request: Request, settings: dict):
    """Get base URL for current request"""
    try:
        if settings and settings.get('base_url'):
            return settings.get('base_url').rstrip('/')
        config_url = settings.get('website_url', WEBSITE_URL).rstrip('/') if settings else WEBSITE_URL
        if not config_url or any(x in config_url for x in ['onrender.com', 'localhost', 'railway.app', '127.0.0.1']):
            return f"{request.url.scheme}://{request.url.netloc}"
        return config_url
    except:
        return f"{request.url.scheme}://{request.url.netloc}"

def get_bot_instance(username):
    """Get bot instance by username"""
    try:
        from bot import Bot
        if not username:
            return next(iter(Bot.instances.values()), None)
        
        username = username.lower().replace("@", "")
        bot = Bot.instances.get(username)
        if bot: 
            return bot
        
        for uname, inst in Bot.instances.items():
            if uname.lower() == username:
                return inst
        
        return next(iter(Bot.instances.values()), None)
    except:
        return None

def get_mime_type(filename, current_mime=None):
    """Get MIME type based on file extension"""
    try:
        ext_to_mime = {
            '.mp4': 'video/mp4',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.flv': 'video/x-flv',
            '.wmv': 'video/x-ms-wmv',
            '.3gp': 'video/3gpp',
            '.ts': 'video/mp2t',
            '.m3u8': 'application/x-mpegURL'
        }
        ext = os.path.splitext(filename)[1].lower() if filename else ''
        return ext_to_mime.get(ext, current_mime or 'video/mp4')
    except:
        return current_mime or 'video/mp4'

def generate_underscore_alias():
    import string, random
    # Generate 4 random alphanumeric blocks of lengths between 3 and 5, joined by underscores
    blocks = []
    for _ in range(4):
        length = random.randint(3, 5)
        blocks.append("".join(random.choices(string.ascii_lowercase + string.digits, k=length)))
    return "_".join(blocks)

async def get_or_create_underscore_shortlink(token_data, settings, request):
    session_id = token_data['session_id']
    latest_session = await db.sessions.find_one({'session_id': session_id})
    if not latest_session:
        return None

    alias = latest_session.get('alias')
    short_link = latest_session.get('original_shortlink')

    if alias and short_link:
        return short_link

    if not alias:
        # Keep trying until we generate a unique alias not already in use
        while True:
            alias = generate_underscore_alias()
            existing = await db.sessions.find_one({'alias': alias})
            if not existing:
                break
        await db.sessions.update_one({'session_id': session_id}, {'$set': {'alias': alias}})

    # Generate the trace / target url: {web_url}/track/{alias}
    web_url = get_base_url(request, settings)
    target_url = f"{web_url}/track/{alias}"

    shortener_url = token_data.get('shortener_url') or settings.get('shortener_url', SHORTENER_URL)
    api_key = token_data.get('shortener_api') or settings.get('shortener_api', SHORTENER_API_KEY)

    short_link = None
    if shortener_url and api_key:
        short_link = await get_short_link(target_url, alias=alias, shortener_url=shortener_url, api_key=api_key)

    if not short_link:
        # Fallback if shortener failed or is unconfigured
        short_link = target_url

    traced_url = short_link
    if short_link and short_link != target_url:
        traced_url = await trace_shortlink(short_link)

    await db.sessions.update_one(
        {'session_id': session_id},
        {'$set': {
            'original_shortlink': short_link,
            'traced_url': traced_url,
            'last_traced_url': traced_url,
            'LAST_TRACED_URL': traced_url
        }}
    )
    return short_link

# --- ERROR HANDLERS ---

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    if exc.status_code == 429 and exc.detail.startswith("<!DOCTYPE html>"):
        return HTMLResponse(content=exc.detail, status_code=exc.status_code)

    settings = await db.get_settings() or {}
    bg_image = get_random_banner(settings)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔮 Error {exc.status_code}</title>
        {get_secure_theme(bg_image)}
    </head>
    <body>
        <div class="glass-card">
            <div class="theme-icon">🔮</div>
            <h1>Error {exc.status_code}</h1>
            <p class="subtitle">{html.escape(str(exc.detail))}</p>
            <button class="btn" onclick="window.location.replace('/')">🏠 Go Home</button>
            <div class="footer">✦ Secure Shield ✦</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=exc.status_code)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Global Error: {exc}")
    settings = await db.get_settings() or {}
    bg_image = get_random_banner(settings)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>⚠️ System Error</title>
        {get_secure_theme(bg_image)}
    </head>
    <body>
        <div class="glass-card">
            <div class="theme-icon">⚠️</div>
            <h1>System Error</h1>
            <p class="subtitle">An unexpected error occurred. Our team has been notified.</p>
            <button class="btn" onclick="window.location.replace('/')">🏠 Go Home</button>
            <div class="footer">✦ Secure Shield ✦</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=500)

# --- ROUTE HANDLERS ---

async def trace_and_store_session_url(token, token_data, settings, request):
    try:
        session_id = token_data.get('session_id')
        if not session_id:
            return None

        latest_session = await db.sessions.find_one({'session_id': session_id})
        if latest_session and latest_session.get('traced_url'):
            return latest_session['traced_url']

        web_url = get_base_url(request, settings)
        target = f"{web_url}/track/{session_id}"

        shortener_url = token_data.get('shortener_url') or settings.get('shortener_url', SHORTENER_URL)
        if shortener_url:
            shortener_url = shortener_url.strip().rstrip('/')
            if not shortener_url.startswith("http"):
                shortener_url = "https://" + shortener_url

        api_key = token_data.get('shortener_api') or settings.get('shortener_api', SHORTENER_API_KEY)

        short_link = None
        if shortener_url and api_key:
            short_link = await get_short_link(target, shortener_url=shortener_url, api_key=api_key)
            if not short_link:
                if any(domain in shortener_url for domain in ["babylinks.in", "arolinks.com", "vplinks.in"]):
                    short_link = f"{shortener_url}/st?api={api_key}&url={urllib.parse.quote(target)}"
                else:
                    short_link = f"{shortener_url}/st?api={api_key}&url={urllib.parse.quote(target)}"

        if short_link:
            traced_last_url = await trace_shortlink(short_link)
            if traced_last_url:
                await db.sessions.update_one(
                    {'session_id': session_id},
                    {'$set': {
                        'traced_url': traced_last_url,
                        'last_traced_url': traced_last_url,
                        'LAST_TRACED_URL': traced_last_url
                    }}
                )
                return traced_last_url
        else:
            await db.sessions.update_one(
                {'session_id': session_id},
                {'$set': {
                    'traced_url': target,
                    'last_traced_url': target,
                    'LAST_TRACED_URL': target
                }}
            )
            return target
    except Exception as e:
        logger.error(f"Error tracing and storing session url: {e}")
        return None

async def process_direct_verification_redirect(request: Request, token: str, token_data: dict, settings: dict):
    session_id = token_data['session_id']
    verification_enabled = settings.get('verification_enabled', True)
    web_url = get_base_url(request, settings)

    # Automatically mark frontend gate cleared without setting session to 'verified'
    await db.sessions.update_one(
        {'session_id': session_id},
        {'$set': {'status': 'timer_started', 'timer_start_at': time.time(), 'frontend_viewed': True, 'gate_cleared': True}}
    )

    if not verification_enabled:
        target_verification_url = f"{web_url}/track/{token}"
    else:
        latest_session = await db.sessions.find_one({'session_id': session_id})
        target_verification_url = latest_session.get('last_traced_url') or latest_session.get('traced_url') or latest_session.get('LAST_TRACED_URL')
        if not target_verification_url:
            target_verification_url = await trace_and_store_session_url(token, token_data, settings, request)
        if not target_verification_url:
            target_verification_url = latest_session.get('original_shortlink') or latest_session.get('traced_url')

    if not target_verification_url:
        target_verification_url = f"{web_url}/track/{token}"

    v_method = token_data.get('verification_method') if token_data else settings.get('verification_method', 'mini_app')

    if v_method in ['own_browser', 'browser']:
        return RedirectResponse(url=f"{web_url}/own_browser?token={token}")

    redirect_token = await db.create_local_redirect(target_verification_url, expire=600)
    return RedirectResponse(url=f"{web_url}/redirect?token={redirect_token}")

@app.get("/health")
async def health_handler():
    return {"status": "✅ Anizoneflix Secure Active"}

@app.get("/", response_class=HTMLResponse)
async def root_handler(request: Request):
    try:
        settings = await db.get_settings() or {}
        return get_root_html(settings)
    except Exception as e:
        logger.error(f"Root handler error: {e}")
        return HTMLResponse(content="🔮 Anizoneflix Gateway", status_code=200)

@app.api_route("/proxy", methods=["GET", "POST"])
async def proxy_handler(request: Request, url: str = Query(...)):
    try:
        decoded_url = urllib.parse.unquote(url)
        if not decoded_url.startswith("http"):
            return Response(content="Invalid proxy target URL", status_code=400)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        body = None
        if request.method == "POST":
            body = await request.body()

        async with aiohttp.ClientSession(headers=headers) as session:
            request_func = session.post if request.method == "POST" else session.get
            async with request_func(decoded_url, data=body, timeout=15, allow_redirects=True) as resp:
                content_type = resp.headers.get("Content-Type", "")
                final_url = str(resp.url)

                if "/track/" in final_url:
                    return RedirectResponse(url=final_url)

                if "html" in content_type.lower():
                    html_text = await resp.text()

                    parsed_url = urllib.parse.urlparse(final_url)
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"

                    injected_script = f"""
                    <base href="{base_url}">
                    <script>
                        // Intercept clicks on links
                        document.addEventListener('click', function(e) {{
                            var target = e.target.closest('a');
                            if (target && target.href && target.href.startsWith('http')) {{
                                var rawHref = target.getAttribute('href');
                                var resolvedUrl = new URL(rawHref, document.baseURI).href;
                                if (!resolvedUrl.includes('/proxy?url=')) {{
                                    e.preventDefault();
                                    window.location.href = '/proxy?url=' + encodeURIComponent(resolvedUrl);
                                }}
                            }}
                        }}, true);

                        // Intercept form submissions
                        document.addEventListener('submit', function(e) {{
                            var form = e.target;
                            if (form.action && form.action.startsWith('http')) {{
                                var rawAction = form.getAttribute('action') || '';
                                var resolvedAction = new URL(rawAction, document.baseURI).href;
                                if (!resolvedAction.includes('/proxy?url=')) {{
                                    form.action = '/proxy?url=' + encodeURIComponent(resolvedAction);
                                }}
                            }}
                        }}, true);

                        // Monkey-patch window.fetch
                        const originalFetch = window.fetch;
                        window.fetch = function(input, init) {{
                            let url;
                            if (typeof input === 'string') {{
                                url = input;
                            }} else if (input instanceof Request) {{
                                url = input.url;
                            }} else {{
                                url = String(input);
                            }}

                            if (url && url.startsWith('http')) {{
                                if (!url.includes('/proxy?url=')) {{
                                    url = '/proxy?url=' + encodeURIComponent(url);
                                }}
                            }} else if (url) {{
                                let resolved = new URL(url, document.baseURI).href;
                                url = '/proxy?url=' + encodeURIComponent(resolved);
                            }}

                            if (typeof input === 'string') {{
                                input = url;
                            }} else if (input instanceof Request) {{
                                input = new Request(url, input);
                            }}
                            return originalFetch.call(this, input, init);
                        }};

                        // Monkey-patch XMLHttpRequest
                        const originalOpen = XMLHttpRequest.prototype.open;
                        XMLHttpRequest.prototype.open = function(method, url, async, user, password) {{
                            if (url && url.startsWith('http')) {{
                                if (!url.includes('/proxy?url=')) {{
                                    url = '/proxy?url=' + encodeURIComponent(url);
                                }}
                            }} else if (url) {{
                                let resolved = new URL(url, document.baseURI).href;
                                url = '/proxy?url=' + encodeURIComponent(resolved);
                            }}
                            return originalOpen.call(this, method, url, async, user, password);
                        }};
                    </script>
                    """

                    if "<head>" in html_text:
                        html_text = html_text.replace("<head>", f"<head>{injected_script}", 1)
                    else:
                        html_text = f"{injected_script}{html_text}"

                    response_headers = {
                        "Content-Type": content_type,
                        "Access-Control-Allow-Origin": "*"
                    }
                    return Response(content=html_text, headers=response_headers, status_code=200)
                else:
                    body = await resp.read()
                    response_headers = {
                        "Content-Type": content_type,
                        "Access-Control-Allow-Origin": "*"
                    }
                    return Response(content=body, headers=response_headers, status_code=resp.status)
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return Response(content=f"Proxy error: {str(e)}", status_code=500)

@app.get("/redirect", response_class=HTMLResponse)
async def local_redirect_handler(request: Request, token: str = Query(None), m: str = Query(None)):
    try:
        settings = await db.get_settings() or {}
        
        if not token: 
            return HTMLResponse(content="Missing token", status_code=400)
        
        redirect_data = await db.get_local_redirect(token)
        if not redirect_data: 
            return HTMLResponse(
                content=get_expired_html(settings=settings),
                status_code=200
            )
        
        await db.mark_redirect_used(token)
        target_url = redirect_data['url']

        return RedirectResponse(url=target_url)
    except Exception as e:
        logger.error(f"Redirect error: {e}")
        return HTMLResponse(content="Redirect error", status_code=500)

@app.get("/own_browser", response_class=HTMLResponse)
async def own_browser_handler(request: Request, token: str = Query(...)):
    try:
        token_data = await db.get_verify_token(token)
        if not token_data:
            settings = await db.get_settings()
            return HTMLResponse(content=get_expired_html(settings=settings), status_code=200)

        bot_uname = token_data.get('bot_username')
        settings = await db.get_settings(bot_username=bot_uname)
        session_id = token_data['session_id']

        latest_session = await db.sessions.find_one({'session_id': session_id})
        target_verification_url = latest_session.get('last_traced_url') or latest_session.get('traced_url') or latest_session.get('original_shortlink')

        if not target_verification_url:
            web_url = get_base_url(request, settings)
            target_verification_url = f"{web_url}/track/{token}"

        v_method = token_data.get('verification_method') if token_data else settings.get('verification_method', 'mini_app')
        base_url = get_base_url(request, settings)
        if v_method == 'browser':
            ob_mode = settings.get('browser_mode', 'normal')
        else:
            ob_mode = settings.get('own_browser_mode', 'proxy')

        from protect import get_own_browser_ui
        return HTMLResponse(content=get_own_browser_ui(target_verification_url, base_url, settings, use_proxy=(ob_mode == 'proxy')), status_code=200)
    except Exception as e:
        logger.error(f"Own browser error: {e}")
        return HTMLResponse(content="Own browser error", status_code=500)

@app.get("/r2/{user_id}/{token}", response_class=HTMLResponse)
async def r2_route_handler(request: Request, user_id: str, token: str, inner: Optional[bool] = Query(None)):
    try:
        ua = request.headers.get("User-Agent", "")
        if not is_allowed_verify_client(ua):
            token_data = await db.get_verify_token(token) if token else None
            settings = await db.get_settings()
            if token_data:
                session_id = token_data['session_id']
                await db.sessions.update_one(
                    {'session_id': session_id},
                    {'$set': {'status': 'blocked', 'expiry': 0}}
                )
                bot_uname = token_data.get('bot_username')
                settings = await db.get_settings(bot_username=bot_uname)
            return HTMLResponse(content=get_bypass_html(token, settings, token_data or {"blocked": True}), status_code=200)

        await check_rate_limit(request, limit=20)

        token_data, error_code = await validate_flow(request, token)

        if error_code == "SESSION_MISSING" or not token_data:
             settings = await db.get_settings()
             return HTMLResponse(content=get_expired_html(settings=settings), status_code=200)

        bot_uname = token_data.get('bot_username')
        settings = await db.get_settings(bot_username=bot_uname)

        if error_code == "LINK_EXPIRED_REUSE":
            return HTMLResponse(content=get_expired_html(settings=settings), status_code=200)

        if error_code in ["SESSION_BLOCKED"]:
            return HTMLResponse(content=get_bypass_html(token, settings, token_data), status_code=200)

        if error_code:
             bot_username = settings.get('bot_username', BOT_USERNAME)
             return RedirectResponse(url=f"https://t.me/{bot_username}")

        # Pre-generate custom underscore shortlink
        await get_or_create_underscore_shortlink(token_data, settings, request)

        v_method = token_data.get('verification_method') if token_data else settings.get('verification_method', 'mini_app')

        if not inner:
            if v_method in ["own_browser", "browser"]:
                from protect import get_own_browser_ui
                base_url = get_base_url(request, settings)
                target_url = f"{base_url}/r2/{user_id}/{token}?inner=true"
                return HTMLResponse(content=get_own_browser_ui(target_url, base_url, settings, use_proxy=True), status_code=200)

        user_id = token_data.get('user_id')
        html_content = get_verification_r2_html(user_id, token, settings, verification_method=v_method)
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        logger.error(f"R2 error: {e}")
        return HTMLResponse(content="Verification error", status_code=500)

@app.get("/verify/{token}", response_class=HTMLResponse)
@app.get("/verify", response_class=HTMLResponse)
async def verify_route_handler(request: Request, token: Optional[str] = None, inner: Optional[bool] = Query(None)):
    try:
        if not token:
            token = request.query_params.get('token')

        ua = request.headers.get("User-Agent", "")
        if not is_allowed_verify_client(ua):
            token_data = await db.get_verify_token(token) if token else None
            settings = await db.get_settings()
            if token_data:
                session_id = token_data['session_id']
                await db.sessions.update_one(
                    {'session_id': session_id},
                    {'$set': {'status': 'blocked', 'expiry': 0}}
                )
                bot_uname = token_data.get('bot_username')
                settings = await db.get_settings(bot_username=bot_uname)
            return HTMLResponse(content=get_bypass_html(token, settings, token_data or {"blocked": True}), status_code=200)

        await check_rate_limit(request, limit=20)

        token_data, error_code = await validate_flow(request, token)

        if error_code == "SESSION_MISSING" or not token_data:
             settings = await db.get_settings()
             return HTMLResponse(content=get_expired_html(settings=settings), status_code=200)

        bot_uname = token_data.get('bot_username')
        settings = await db.get_settings(bot_username=bot_uname)
        bot_username = settings.get('bot_username', BOT_USERNAME)

        if error_code == "LINK_EXPIRED_REUSE": 
            return HTMLResponse(content=get_expired_html(settings=settings), status_code=200)
        
        if error_code in ["SESSION_BLOCKED"]:
            return HTMLResponse(content=get_bypass_html(token, settings, token_data), status_code=200)

        if error_code:
            return RedirectResponse(url=f"https://t.me/{bot_username}")
        
        # Pre-generate custom underscore shortlink
        await get_or_create_underscore_shortlink(token_data, settings, request)

        v_method = token_data.get('verification_method') if token_data else settings.get('verification_method', 'mini_app')

        if not inner:
            if v_method in ["own_browser", "browser"]:
                from protect import get_own_browser_ui
                base_url = get_base_url(request, settings)
                target_url = f"{base_url}/verify/{token}?inner=true"
                return HTMLResponse(content=get_own_browser_ui(target_url, base_url, settings, use_proxy=True), status_code=200)

        user_id = token_data.get('user_id')
        html_content = get_verification_r2_html(user_id, token, settings, verification_method=v_method)
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        logger.error(f"Verify error: {e}")
        return HTMLResponse(content="Verification error", status_code=500)



@app.post("/gate/{token}")
async def gate_submission_handler(
    request: Request,
    token: str,
    captcha_token: Optional[str] = Form(None),
    uid: Optional[str] = Query(None)
):
    try:
        token_data, error_code = await validate_flow(request, token)
        if error_code:
            return {"success": False, "error": error_code}

        bot_uname = token_data.get('bot_username')
        settings = await db.get_settings(bot_username=bot_uname)

        session_id = token_data['session_id']

        verification_enabled = settings.get('verification_enabled', True)
        web_url = get_base_url(request, settings)

        # Mark frontend gate cleared without setting session to 'verified' or marking user verified
        await db.sessions.update_one(
            {'session_id': session_id},
            {'$set': {'status': 'timer_started', 'timer_start_at': time.time(), 'frontend_viewed': True, 'gate_cleared': True}}
        )

        if not verification_enabled:
            # If verification is disabled, point directly to backend track handler to complete backend verification cleanly
            target_verification_url = f"{web_url}/track/{token}"
        else:
            latest_session = await db.sessions.find_one({'session_id': session_id})
            target_verification_url = latest_session.get('last_traced_url') or latest_session.get('traced_url') or latest_session.get('LAST_TRACED_URL')
            if not target_verification_url:
                target_verification_url = await trace_and_store_session_url(token, token_data, settings, request)

            if not target_verification_url:
                target_verification_url = latest_session.get('original_shortlink') or latest_session.get('traced_url')

        if not target_verification_url:
            web_url = get_base_url(request, settings)
            target_verification_url = f"{web_url}/track/{token}"

        v_method = token_data.get('verification_method') if token_data else settings.get('verification_method', 'mini_app')
        web_url = get_base_url(request, settings)

        if v_method in ['own_browser', 'browser']:
            redirect_url = f"{web_url}/own_browser?token={token}"
        else:
            redirect_token = await db.create_local_redirect(target_verification_url, expire=600)
            redirect_url = f"{web_url}/redirect?token={redirect_token}"

        return {"success": True, "redirect_url": redirect_url}
    except Exception as e:
        logger.error(f"Gate submission failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/track/{token}")
async def track_handler(request: Request, token: str):
    """Complete verification immediately after shortener"""
    try:
        ua = request.headers.get("User-Agent", "")
        if not is_allowed_verify_client(ua):
            token_data = await db.get_verify_token(token) if token else None
            settings = await db.get_settings()
            if token_data:
                session_id = token_data['session_id']
                await db.sessions.update_one(
                    {'session_id': session_id},
                    {'$set': {'status': 'blocked', 'expiry': 0}}
                )
                bot_uname = token_data.get('bot_username')
                settings = await db.get_settings(bot_username=bot_uname)
            return HTMLResponse(content=get_bypass_html(token, settings, token_data or {"blocked": True}), status_code=200)

        token_data, error = await validate_flow(request, token)

        if error:
            # If the session is blocked or bypass was detected, immediately show the bypass detected page!
            settings = await db.get_settings()
            if token_data:
                bot_uname = token_data.get('bot_username')
                settings = await db.get_settings(bot_username=bot_uname)

            if error in ["SESSION_BLOCKED", "USER_BANNED"]:
                return HTMLResponse(content=get_bypass_html(token, settings, token_data or {"blocked": True}), status_code=200)
            elif error == "SESSION_EXPIRED":
                return HTMLResponse(content=get_expired_html(settings), status_code=200)
            return RedirectResponse(url="/")
        
        bot_uname = token_data.get('bot_username')
        settings = await db.get_settings(bot_username=bot_uname)

        # Successful verification (direct pass)
        session_id = token_data['session_id']
        await db.sessions.update_one(
            {'session_id': session_id},
            {'$set': {'status': 'verified', 'referer_verified': True}}
        )
        await db.log_stat('successful_verifications')

        referral_id = token_data.get('referral_id')
        if referral_id and settings.get('referral_active'):
            await db.update_referral_status(token_data['user_id'], "completed", verified=True, content_accessed=True)

        # Instantly deliver the files in the background to automatically continue the user's request
        try:
            bot = getattr(request.app.state, 'bot', None)
            if bot:
                user_id = int(token_data['user_id'])
                content_id = token_data['content_id']

                await db.set_user_verified(user_id, bot_username=bot_uname, token=session_id)
                await db.set_verified_worker(bot.username, user_id)
                await db.decrement_user_credits(user_id, bot_username=bot_uname)
                await db.mark_session_used(session_id)

                if content_id != "verify_general":
                    from plugins.start import send_files
                    asyncio.create_task(send_files(bot, user_id, content_id))

                # Send verification completed log to all configured destinations using main bot
                try:
                    user_id = int(token_data['user_id'])
                    user_obj = await bot.get_users(user_id) if bot else None
                    traced_link = token_data.get('original_shortlink') or token_data.get('traced_url') or f"Session: {session_id}"
                    from plugins.start import send_verify_log
                    asyncio.create_task(send_verify_log("verified", user_id, user_obj, session_id, traced_link, bot_uname or BOT_USERNAME))
                except Exception as log_err:
                    logger.error(f"Error triggering verify log: {log_err}")
        except Exception as deliver_err:
            logger.error(f"Error in background delivery: {deliver_err}")

        bot_username = bot_uname or BOT_USERNAME
        session_id = token_data['session_id'].replace("-", "_")

        v_method = token_data.get('verification_method') if token_data else settings.get('verification_method', 'mini_app')
        if v_method in ['browser', 'own_browser']:
            bg_image = None

            # Button behavior for Own Browser should go back to chat smoothly or close tab if possible
            close_js = f"window.location.replace('https://t.me/{bot_username}');"
            if v_method == 'browser':
                close_js = """
                    if (window.Telegram && window.Telegram.WebApp) {
                        Telegram.WebApp.close();
                    } else if (window.top !== window && window.top.Telegram && window.top.Telegram.WebApp) {
                        window.top.Telegram.WebApp.close();
                    } else {
                        try {
                            if (window.top !== window) {
                                window.top.location.replace("https://t.me/""" + bot_username + """");
                                return;
                            }
                        } catch(e) {}
                        window.location.replace("https://t.me/""" + bot_username + """");
                    }
                """

            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>Verification Complete</title>
                <script src="https://telegram.org/js/telegram-web-app.js"></script>
                {get_secure_theme(bg_image)}
                <style>
                    .success-card {{
                        background: rgba(13, 17, 23, 0.75);
                        color: #f8fafc;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.5), 0 0 15px var(--theme-glow);
                        border: 1px solid var(--glass-border);
                        padding: 35px;
                        border-radius: 28px;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="glass-card success-card">
                    <div class="theme-icon">✅</div>
                    <h1>Verified!</h1>
                    <p class="subtitle">Your requested files have been sent directly to your Telegram chat.</p>
                    <button class="btn" style="background: linear-gradient(135deg, var(--neon-green), #059669) !important;" onclick="closeWebApp()">📥 Go to Chat</button>
                    <div class="footer">✦ Secure Shield ✦</div>
                </div>
                <script>
                    function closeWebApp() {{
                        {close_js}
                    }}
                    window.onload = () => {{
                        if (window.Telegram && window.Telegram.WebApp) {{
                            Telegram.WebApp.ready();
                            setTimeout(closeWebApp, 1500);
                        }} else if (window.top !== window && window.top.Telegram && window.top.Telegram.WebApp) {{
                            window.top.Telegram.WebApp.ready();
                            setTimeout(closeWebApp, 1500);
                        }} else {{
                            setTimeout(closeWebApp, 1500);
                        }}
                    }};
                </script>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=200)

        tg_url = f"tg://resolve?domain={bot_username}&start=verify_{session_id}"
        return RedirectResponse(url=tg_url)
    except Exception as e:
        logger.error(f"Track verification error: {e}")
        return RedirectResponse(url="/")


@app.get("/ref/{referrer_id}")
async def referral_handler(referrer_id: str):
    try:
        settings = await db.get_settings() or {}
        bot_username = settings.get('bot_username', BOT_USERNAME)
        return RedirectResponse(url=f"https://t.me/{bot_username}?start=ref_{referrer_id}")
    except Exception as e:
        logger.error(f"Referral handler error: {e}")
        return Response(status_code=500)

@app.get("/download")
async def download_query_handler(path: str = Query(None)):
    try:
        if not path: 
            return Response(content="Missing path", status_code=400)
        
        url = await db.get_url_by_token(path)
        if not url: 
            return Response(content="Invalid path", status_code=404)
        
        url = url.replace("/watch/", "/download/").replace("/stream/", "/download/").replace("/v/", "/download/")
        return RedirectResponse(url=url + ("&mode=download" if "?" in url else "?mode=download"))
    except Exception as e:
        logger.error(f"Download error: {e}")
        return Response(status_code=500)

async def stream_generator(bot, msg, start, limit):
    async for chunk in bot.stream_media(msg, offset=start, limit=limit):
        yield chunk

@app.get("/dl/{bot_username}/{msg_id}/{name}")
@app.get("/stream/{bot_username}/{msg_id}/{name}")
@app.get("/download/{bot_username}/{msg_id}/{name}")
async def dl_handler(
    request: Request,
    bot_username: str,
    msg_id: int,
    name: str,
    hash: str = Query(None),
    mode: Optional[str] = Query(None)
):
    try:
        bot_username = bot_username.lower().replace("@", "")
        if not hash or hash != generate_stream_hash(msg_id):
            return Response(status_code=403)
        
        bot = get_bot_instance(bot_username)
        if not bot: 
            return Response(status_code=404)
        
        try:
            messages = await get_messages(bot, [msg_id])
            msg = messages[0] if isinstance(messages, list) and messages else messages
            if not msg or msg.empty: 
                return Response(status_code=404)
        except:
            return Response(status_code=500)
        
        media = msg.document or msg.video or msg.audio or msg.animation
        if not media: 
            return Response(status_code=404)
        
        is_download = "/download" in request.url.path or mode == 'download'
        
        headers = {
            "Content-Type": "application/octet-stream" if is_download else get_mime_type(media.file_name, media.mime_type),
            "Content-Disposition": f'{"attachment" if is_download else "inline"}; filename="{urllib.parse.quote(media.file_name or "file")}"; filename*=UTF-8\'\'{urllib.parse.quote(media.file_name or "file")}',
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*"
        }
        
        range_header = request.headers.get("Range")
        start, end = 0, media.file_size - 1
        status_code = 200
        
        if range_header and range_header.startswith("bytes="):
            try:
                range_val = range_header.replace("bytes=", "")
                if "-" in range_val:
                    r_start, r_end = range_val.split("-", 1)
                    if not r_start and r_end:
                        start = max(0, media.file_size - int(r_end))
                        end = media.file_size - 1
                    else:
                        start = int(r_start) if r_start else 0
                        end = int(r_end) if r_end else media.file_size - 1
                
                if start >= media.file_size:
                    return Response(status_code=416, headers={"Content-Range": f"bytes */{media.file_size}"})
                
                end = min(end, media.file_size - 1)
                if start > end: 
                    start = 0
                
                status_code = 206
                headers["Content-Range"] = f"bytes {start}-{end}/{media.file_size}"
                headers["Content-Length"] = str(end - start + 1)
            except:
                pass
        else:
             headers["Content-Length"] = str(media.file_size)
        
        return StreamingResponse(
            stream_generator(bot, msg, start, end - start + 1),
            status_code=status_code,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Download handler error: {e}")
        return Response(status_code=500)

@app.get("/v/{path}", response_class=HTMLResponse)
async def player_v_handler(request: Request, path: str):
    try:
        url = await db.get_url_by_token(path)
        
        if not url: 
            return "Invalid Link"
        
        parsed = urllib.parse.urlparse(url)
        parts = parsed.path.strip('/').split('/')
        
        if len(parts) < 4: 
            return HTMLResponse(content="Internal Error", status_code=500)
        
        bot_username, msg_id, name = parts[1], int(parts[2]), urllib.parse.unquote(parts[3])
        stream_hash = urllib.parse.parse_qs(parsed.query).get('hash', [None])[0]
        
        ua = request.headers.get('User-Agent', 'Unknown').lower()
        
        if "android" in ua and request.query_params.get('w') != '1':
            settings = await db.get_settings() or {}
            base_origin = f"{request.url.scheme}://{request.url.netloc}"
            stream_url = f"{base_origin}/stream/{bot_username}/{msg_id}/{urllib.parse.quote(name)}?hash={stream_hash}&stream=true"
            web_player_url = str(request.url) + ("&w=1" if "?" in str(request.url) else "?w=1")
            
            return get_app_redirect_html(stream_url, web_player_url, name, settings)
        
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    background: #0a0a0f; 
                    color: #f0f0ff; 
                    font-family: 'Inter', sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    flex-direction: column;
                    gap: 20px;
                    padding: 20px;
                }
                .box {
                    background: rgba(10, 10, 15, 0.8);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 28px;
                    padding: 40px 30px;
                    text-align: center;
                    max-width: 380px;
                    width: 100%;
                }
                h2 { font-size: 26px; margin-bottom: 12px; background: linear-gradient(135deg, #fff 30%, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
                p { color: #8888aa; margin-bottom: 25px; line-height: 1.6; font-size: 14px; }
                .btn {
                    display: inline-block;
                    padding: 16px 35px;
                    background: linear-gradient(135deg, #8b5cf6, #6366f1);
                    color: white;
                    text-decoration: none;
                    border-radius: 22px;
                    font-weight: 700;
                    transition: all 0.25s ease;
                    box-shadow: 0 15px 35px rgba(99, 102, 241, 0.3);
                    font-size: 14px;
                }
                .btn:hover { transform: translateY(-2px); box-shadow: 0 20px 45px rgba(99, 102, 241, 0.4); }
                .icon { font-size: 50px; margin-bottom: 15px; display: block; }
            </style>
        </head>
        <body>
            <div class="box">
                <span class="icon">🎵</span>
                <h2>Secure Player</h2>
                <p>Install the Stream Player app for high quality playback</p>
                <a href="https://t.me/AniZoneFlix" class="btn">📱 Get App</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Player error: {e}")
        return HTMLResponse(content="Player Error", status_code=500)

@app.get("/watch/{bot_username}/{msg_id}/{name}")
async def watch_handler(request: Request, bot_username: str, msg_id: int, name: str, hash: str = Query(None)):
    try:
        bot_username = bot_username.lower().replace("@", "")
        settings = await db.get_settings() or {}
        web_url = get_base_url(request, settings)
        
        url = f"{web_url}/watch/{bot_username}/{msg_id}/{urllib.parse.quote(name)}?hash={hash}"
        p_token = await db.create_local_redirect(url)
        
        return RedirectResponse(url=f"/v/{p_token}")
    except Exception as e:
        logger.error(f"Watch handler error: {e}")
        return Response(status_code=500)

async def web_server(bot):
    """Main web server entry point - Returns the FastAPI app"""
    app.state.bot = bot
    return app
