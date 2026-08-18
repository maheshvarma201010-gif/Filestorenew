import os
import re
import time
import random
import asyncio
import logging
import sqlite3
import urllib.parse
import aiohttp
from typing import List, Dict, Tuple, Optional

import config

logger = logging.getLogger("ProxyManager")
logger.setLevel(logging.INFO)

# Regex fallback or urlparse for proxy verification
def validate_proxy_format(proxy_str: str) -> Tuple[bool, str]:
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return False, "Proxy string is empty."
    if "://" not in proxy_str:
        proxy_str = "http://" + proxy_str
    try:
        parsed = urllib.parse.urlparse(proxy_str)
        if parsed.scheme not in ["http", "https", "socks4", "socks5"]:
            return False, "Proxy scheme must be http, https, socks4, or socks5."
        if not parsed.hostname:
            return False, "Host/IP is required."
        if not parsed.port:
            return False, "Port is required."
        return True, "Valid"
    except Exception as e:
        return False, f"Invalid proxy format: {str(e)}"

def mask_proxy(proxy_str: str) -> str:
    try:
        proxy_str = proxy_str.strip()
        if "://" not in proxy_str:
            proxy_str = "http://" + proxy_str
        parsed = urllib.parse.urlparse(proxy_str)
        if parsed.username and parsed.password:
            masked_netloc = f"{parsed.username}:******@{parsed.hostname}:{parsed.port}"
            return f"{parsed.scheme}://{masked_netloc}"
        else:
            return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    except:
        pass
    return proxy_str

class ProxyManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, db_path: str = "proxies.db"):
        self.db_path = db_path
        self.rotation_strategy = "random"  # "random" or "round_robin"
        self.round_robin_index = 0
        self.proxies_cache: List[Dict] = []
        self._init_db()
        self.reload()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy TEXT UNIQUE,
                enabled INTEGER DEFAULT 1,
                last_checked TEXT,
                last_status TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Set default rotation strategy if not set
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('rotation_strategy', 'random')")
        conn.commit()
        conn.close()

    def reload(self):
        """Reload proxies from DB and config.py defaults, and restore settings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load rotation strategy
        cursor.execute("SELECT value FROM settings WHERE key='rotation_strategy'")
        row = cursor.fetchone()
        if row:
            self.rotation_strategy = row[0]

        # First, sync config.py defaults to DB
        default_proxies = getattr(config, "PROXIES", [])
        if default_proxies:
            for p_str in default_proxies:
                p_str = p_str.strip()
                is_valid, _ = validate_proxy_format(p_str)
                if is_valid:
                    cursor.execute("INSERT OR IGNORE INTO proxies (proxy, enabled) VALUES (?, 1)", (p_str,))
            conn.commit()

        # Load all proxies from DB
        cursor.execute("SELECT id, proxy, enabled, last_checked, last_status FROM proxies")
        rows = cursor.fetchall()

        self.proxies_cache = []
        for r in rows:
            self.proxies_cache.append({
                "id": r[0],
                "proxy": r[1],
                "enabled": bool(r[2]),
                "last_checked": r[3],
                "last_status": r[4]
            })

        conn.close()
        logger.info(f"Loaded {len(self.proxies_cache)} proxies from database/config.")

    def set_rotation_strategy(self, strategy: str):
        if strategy not in ["random", "round_robin"]:
            strategy = "random"
        self.rotation_strategy = strategy
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rotation_strategy', ?)", (strategy,))
        conn.commit()
        conn.close()

    def get_enabled_proxies(self) -> List[str]:
        return [p["proxy"] for p in self.proxies_cache if p["enabled"]]

    def get_proxy(self) -> Optional[str]:
        """Get proxy based on current rotation strategy."""
        enabled = self.get_enabled_proxies()
        if not enabled:
            return None

        if self.rotation_strategy == "round_robin":
            return self.get_next_proxy()
        else:
            return self.get_random_proxy()

    def get_random_proxy(self) -> Optional[str]:
        enabled = self.get_enabled_proxies()
        if not enabled:
            return None
        selected = random.choice(enabled)
        logger.info(f"Selected proxy (Random): {mask_proxy(selected)}")
        return selected

    def get_next_proxy(self) -> Optional[str]:
        enabled = self.get_enabled_proxies()
        if not enabled:
            return None

        if self.round_robin_index >= len(enabled):
            self.round_robin_index = 0

        selected = enabled[self.round_robin_index]
        self.round_robin_index = (self.round_robin_index + 1) % len(enabled)
        logger.info(f"Selected proxy (Round Robin): {mask_proxy(selected)}")
        return selected

    def add_proxy(self, proxy_str: str) -> Tuple[bool, str]:
        proxy_str = proxy_str.strip()
        if proxy_str and "://" not in proxy_str:
            proxy_str = "http://" + proxy_str
        is_valid, err_msg = validate_proxy_format(proxy_str)
        if not is_valid:
            return False, err_msg

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO proxies (proxy, enabled) VALUES (?, 1)", (proxy_str,))
            conn.commit()
            conn.close()
            self.reload()
            return True, f"Proxy added successfully: {mask_proxy(proxy_str)}"
        except sqlite3.IntegrityError:
            return False, "This proxy is already saved in the database."
        except Exception as e:
            return False, f"Failed to save proxy: {str(e)}"

    def delete_proxy(self, proxy_id_or_str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if isinstance(proxy_id_or_str, int) or (isinstance(proxy_id_or_str, str) and proxy_id_or_str.isdigit()):
                cursor.execute("DELETE FROM proxies WHERE id = ?", (int(proxy_id_or_str),))
            else:
                cursor.execute("DELETE FROM proxies WHERE proxy = ?", (str(proxy_id_or_str).strip(),))
            conn.commit()
            conn.close()
            self.reload()
            return True
        except Exception as e:
            logger.error(f"Error deleting proxy: {e}")
            return False

    def list_proxies(self) -> List[Dict]:
        return self.proxies_cache

    async def check_proxy(self, proxy_str: str) -> str:
        """Test a proxy asynchronously using https://ipv4.webshare.io/."""
        url = "https://ipv4.webshare.io/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Bypass any automatic proxying for the proxy check request
        connector = aiohttp.TCPConnector(ssl=False)

        try:
            # Check timeout explicitly or let aiohttp handle it
            async with aiohttp.ClientSession(connector=connector) as session:
                # We pass bypass_proxy=True so our monkeypatched ClientSession won't auto-wrap this request
                async with session.get(url, proxy=proxy_str, headers=headers, timeout=12, bypass_proxy=True) as resp:
                    if resp.status == 200:
                        status = "✅ Working"
                    elif resp.status in [407, 401, 403]:
                        status = "🔒 Authentication Failed"
                    else:
                        status = f"❌ Failed ({resp.status})"
        except asyncio.TimeoutError:
            status = "⏱ Timeout"
        except (aiohttp.ClientHttpProxyError, aiohttp.ClientProxyConnectionError) as e:
            if hasattr(e, "status") and e.status in [407, 401, 403]:
                status = "🔒 Authentication Failed"
            else:
                status = "❌ Failed"
        except Exception as e:
            err_str = str(e).lower()
            if "407" in err_str or "proxy authentication required" in err_str or "403" in err_str:
                status = "🔒 Authentication Failed"
            else:
                status = "❌ Failed"

        # Update proxy status in DB
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE proxies SET last_checked = ?, last_status = ? WHERE proxy = ?", (timestamp, status, proxy_str))
            conn.commit()
            conn.close()
        except Exception as db_err:
            logger.error(f"Error updating proxy check result: {db_err}")

        # Update cache directly
        for p in self.proxies_cache:
            if p["proxy"] == proxy_str:
                p["last_checked"] = timestamp
                p["last_status"] = status
                break

        return status

    def mark_proxy_failed(self, proxy_str: str, status: str = "❌ Failed"):
        """Mark a proxy as failed in DB and cache."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE proxies SET last_checked = ?, last_status = ? WHERE proxy = ?", (timestamp, status, proxy_str))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error marking proxy as failed: {e}")

        for p in self.proxies_cache:
            if p["proxy"] == proxy_str:
                p["last_checked"] = timestamp
                p["last_status"] = status
                break

proxy_manager = ProxyManager.get_instance()

# Monkeypatch aiohttp.ClientSession._request to support transparent, resilient proxy rotation and retry.
original_request = aiohttp.ClientSession._request

async def new_request(self, method: str, str_or_url, *args, **kwargs):
    bypass_proxy = kwargs.pop("bypass_proxy", False)
    if bypass_proxy:
        return await original_request(self, method, str_or_url, *args, **kwargs)

    enabled_proxies = proxy_manager.get_enabled_proxies()
    if not enabled_proxies:
        # Fallback to direct connection if no proxies are configured/enabled
        return await original_request(self, method, str_or_url, *args, **kwargs)

    tried_proxies = set()
    max_retries = len(enabled_proxies)
    timeout_added = False

    while len(tried_proxies) < max_retries:
        proxy = proxy_manager.get_proxy()
        # Ensure we pick a proxy that hasn't been tried yet for this request
        if not proxy or proxy in tried_proxies:
            untried = [p for p in enabled_proxies if p not in tried_proxies]
            if not untried:
                break
            proxy = random.choice(untried)

        tried_proxies.add(proxy)
        logger.info(f"[PROXY] Attempting {method} {str_or_url} with proxy: {mask_proxy(proxy)}")

        try:
            kwargs["proxy"] = proxy
            # Apply a safe individual request timeout (e.g., 10 seconds) for proxies to avoid hanging indefinitely,
            # unless an explicit timeout is already specified in kwargs.
            if "timeout" not in kwargs or kwargs["timeout"] is None:
                kwargs["timeout"] = aiohttp.ClientTimeout(total=10)
                timeout_added = True

            resp = await original_request(self, method, str_or_url, *args, **kwargs)
            if resp.status in [401, 403, 407]:
                logger.warning(f"[PROXY] Auth failure {resp.status} with proxy {mask_proxy(proxy)}. Marking proxy as failed.")
                proxy_manager.mark_proxy_failed(proxy, "🔒 Authentication Failed")
                try:
                    resp.close()
                except:
                    pass
                continue
            return resp

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ConnectionResetError,
            OSError
        ) as e:
            logger.warning(f"[PROXY] Request failed with proxy {mask_proxy(proxy)}: {type(e).__name__} ({str(e)}). Marking proxy as failed.")
            proxy_manager.mark_proxy_failed(proxy, f"❌ Failed: {type(e).__name__}")
            continue

    # Fallback to direct connection
    logger.info(f"[PROXY] All proxies failed. Falling back to direct connection for {method} {str_or_url}")
    kwargs["proxy"] = None
    if timeout_added:
        kwargs.pop("timeout", None)
    return await original_request(self, method, str_or_url, *args, **kwargs)

aiohttp.ClientSession._request = new_request
