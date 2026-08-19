#ᴀɴɪᴢᴏɴᴇꜰʟɪx_ʙᴏᴛᴢ
#ᴀɴɪᴢᴏɴᴇꜰʟɪx on ᴛɢ

import motor.motor_asyncio
import asyncio
import random
import time
from datetime import datetime
import secrets
import uuid
import hmac
import hashlib
import pymongo, os
import config
from config import DB_URI, DB_NAME, RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY, TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY
import logging

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]

logging.basicConfig(level=logging.INFO)

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }

class AniZoneFlix:

    def __init__(self, DB_URI, DB_NAME):
        self.busy_admins = set()
        self.bot_admin_locks = {}
        self.settings_cache = {}
        self.channels_cache = None
        self.fsub_bots_cache = None
        self.clones_cache = {}
        self.del_timer_cache = None
        self.admin_cache = {}
        self.banned_user_cache = {}
        self.verified_user_cache = {}
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
        self.database = self.dbclient[DB_NAME]

        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.user_data = self.database['users']
        self.sex_data = self.database['sex']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        self.del_timer_data = self.database['del_timer']
        self.fsub_data = self.database['fsub']   
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.bypass_data = self.database['bypass_attempts']
        self.settings_data = self.database['settings']
        self.cooldown_data = self.database['cooldowns']
        self.sessions = self.database['sessions'] # Codeflix Network Collection
        self.antibot_data = self.sessions # Alias for script compatibility
        self.clones = self.database['clones']
        self.redirects = self.database['redirects']
        self.fsub_bots = self.database['fsub_bots']
        self.logs = self.database['logs']
        self.referrals = self.database['referrals']
        self.helpers = self.database['helpers']
        self.payloads = self.database['payloads']

    async def create_indexes(self):
        """Creates necessary database indexes."""
        try:
            await self.sessions.create_index("mask_token")
            await self.sessions.create_index("short_token")
            await self.sessions.create_index("session_id", unique=True)
            await self.redirects.create_index("token", unique=True)
            await self.fsub_bots.create_index("token", unique=True)
            await self.logs.create_index([("user_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
            await self.referrals.create_index([("referrer_id", pymongo.ASCENDING), ("referred_id", pymongo.ASCENDING)], unique=True)
            logging.info("Database indexes created successfully.")
        except Exception as e:
            logging.error(f"Failed to create database indexes: {e}")


    # SETTINGS & FEATURE FLAGS
    async def get_settings(self, bot_username: str = None, use_cache=True):
        cache_key = bot_username.lower().replace("@", "").strip() if bot_username else "global"
        if use_cache and cache_key in self.settings_cache:
            return self.settings_cache[cache_key]

        settings = await self.settings_data.find_one({'_id': 'bot_settings'})

        # Fields that are ALWAYS global and cannot be overridden by bots
        GLOBAL_ONLY_FIELDS = [
            'shortener_url', 'shortener_api', 'shorteners', 'shortener_active', 'shortener',
            'website_url', 'api_url', 'base_url', 'cdn_url', 'owner_tag', 'upi_id',
            'anime_banners', 'video_banners', 'app_id', 'api_hash', 'owner_id',
            'use_recaptcha', 'recaptcha_site_key', 'recaptcha_secret_key',
            'use_turnstile', 'turnstile_site_key', 'turnstile_secret_key',
            'verify_bot_active', 'verify_api_url', 'verify_api_secret', 'verify_bot_username'
        ]

        default_settings = {
            '_id': 'bot_settings',
            'shortener_active': True,
            'shortener_url': config.SHORTENER_URL,
            'shortener_api': config.SHORTENER_API_KEY,
            'website_url': config.WEBSITE_URL,
            'api_url': '',
            'base_url': '',
            'session_string': '',
            'file_delivery': True,
            'verification_enabled': True,
            'verification_method': 'mini_app',
            'core_features': True,
            'shorten_admins': True,
            'daily_verify_limit': 5,
            'use_recaptcha': False,
            'use_turnstile': False,
            'use_302_redirect': False,
            'redirect_type': 302,
            'auto_redirect': False,
            'frontend_verify': True,
            'auto_ban': True,
            'recaptcha_site_key': config.RECAPTCHA_SITE_KEY,
            'recaptcha_secret_key': config.RECAPTCHA_SECRET_KEY,
            'turnstile_site_key': config.TURNSTILE_SITE_KEY,
            'turnstile_secret_key': config.TURNSTILE_SECRET_KEY,
            'auto_ban': True,
            'file_delivery': True,
            'streaming_active': True,
            'download_btn_active': True,
            'verify_window': 86400,
            'referral_active': True,
            'access_limit': 1,
            'anime_banners': config.ANIME_BANNERS,
            'bot_name': config.BOT_NAME,
            'bot_username': config.BOT_USERNAME,
            'owner_tag': config.OWNER_TAG,
            'upi_id': config.UPI_ID,
            'cdn_url': config.CDN_URL,
            'random_mode': False,
            'shorteners': [],
            'video_banners': [],
            'protect_content_normal': False,
            'protect_content_premium': False,
            'protect_content_auth': False,
            'verify_log_channel': '',
            'verify_log_destinations': [],
            'app_id': config.APP_ID,
            'api_hash': config.API_HASH,
            'owner_id': config.OWNER_ID,
            'custom_caption_active': True,
            'custom_caption_text': "<b>• By `https://t.me/AniZoneFlix`</b>",
            'verify_bot_active': False,
            'verify_api_url': getattr(config, 'VERIFY_API_URL', 'https://your-verify-api.example.com'),
            'verify_api_secret': getattr(config, 'VERIFY_API_SECRET', 'your_random_api_secret'),
            'verify_bot_username': getattr(config, 'VERIFY_BOT_USERNAME', 'YourVerifyBot')
        }

        if not settings:
            await self.settings_data.insert_one(default_settings)
            settings = default_settings
        else:
            # Ensure all other fields exist
            updated = False
            for field, default in default_settings.items():
                if field not in settings:
                    settings[field] = default
                    updated = True

            if updated:
                await self.settings_data.update_one({'_id': 'bot_settings'}, {'$set': settings})

        if not bot_username:
            self.settings_cache[cache_key] = settings
            return settings

        # Load bot-specific overrides
        bot_username = bot_username.lower().replace("@", "")
        bot_settings = await self.settings_data.find_one({'_id': f'bot_settings_{bot_username}'})
        if not bot_settings:
            self.settings_cache[cache_key] = settings
            return settings

        # Merge: bot settings take precedence, EXCEPT for global-only fields
        merged = {**settings, **bot_settings}
        for field in GLOBAL_ONLY_FIELDS:
            merged[field] = settings.get(field, default_settings.get(field))

        merged['_id'] = settings['_id'] # Keep global ID as reference
        self.settings_cache[cache_key] = merged
        return merged

    async def update_setting(self, key: str, value, bot_username: str = None):
        # Fields that are ALWAYS global
        GLOBAL_ONLY_FIELDS = [
            'shortener_url', 'shortener_api', 'shorteners', 'shortener_active', 'shortener',
            'website_url', 'api_url', 'base_url', 'cdn_url', 'owner_tag', 'upi_id',
            'anime_banners', 'video_banners', 'app_id', 'api_hash', 'owner_id',
            'use_recaptcha', 'recaptcha_site_key', 'recaptcha_secret_key',
            'use_turnstile', 'turnstile_secret_key', 'verify_log_destinations',
            'verify_bot_active', 'verify_api_url', 'verify_api_secret', 'verify_bot_username'
        ]

        doc_id = 'bot_settings'
        if bot_username and key not in GLOBAL_ONLY_FIELDS and key == 'session_string':
            # Session string can be bot-specific or global, let's treat it as bot-specific override
            pass
        if bot_username and key not in GLOBAL_ONLY_FIELDS:
            bot_username = bot_username.lower().replace("@", "")
            doc_id = f'bot_settings_{bot_username}'

        await self.settings_data.update_one(
            {'_id': doc_id},
            {'$set': {key: value}},
            upsert=True
        )
        if doc_id == 'bot_settings':
            self.settings_cache.clear() # Invalidate cache

            # Propagate updated values to sys.modules
            if key in ['app_id', 'api_hash', 'owner_id', 'website_url', 'api_url', 'base_url', 'shortener_url', 'shortener_api']:
                import sys
                if key == 'app_id':
                    val = int(value)
                    config.APP_ID = val
                    for m in list(sys.modules.values()):
                        if m and hasattr(m, 'APP_ID'):
                            try: setattr(m, 'APP_ID', val)
                            except Exception: pass
                elif key == 'api_hash':
                    val = str(value)
                    config.API_HASH = val
                    for m in list(sys.modules.values()):
                        if m and hasattr(m, 'API_HASH'):
                            try: setattr(m, 'API_HASH', val)
                            except Exception: pass
                elif key == 'owner_id':
                    val = int(value)
                    config.OWNER_ID = val
                    for m in list(sys.modules.values()):
                        if m and hasattr(m, 'OWNER_ID'):
                            try: setattr(m, 'OWNER_ID', val)
                            except Exception: pass
                elif key == 'website_url':
                    val = str(value)
                    config.WEBSITE_URL = val
                    for m in list(sys.modules.values()):
                        if m:
                            if hasattr(m, 'WEBSITE_URL'):
                                try: setattr(m, 'WEBSITE_URL', val)
                                except: pass
                            if hasattr(m, 'website_url'):
                                try: setattr(m, 'website_url', val)
                                except: pass
                elif key == 'api_url':
                    val = str(value)
                    config.API_URL = val
                    for m in list(sys.modules.values()):
                        if m:
                            if hasattr(m, 'API_URL'):
                                try: setattr(m, 'API_URL', val)
                                except: pass
                            if hasattr(m, 'api_url'):
                                try: setattr(m, 'api_url', val)
                                except: pass
                elif key == 'shortener_url':
                    val = str(value)
                    config.SHORTENER_URL = val
                    for m in list(sys.modules.values()):
                        if m:
                            if hasattr(m, 'SHORTENER_URL'):
                                try: setattr(m, 'SHORTENER_URL', val)
                                except: pass
                            if hasattr(m, 'shortener_url'):
                                try: setattr(m, 'shortener_url', val)
                                except: pass
                elif key == 'shortener_api':
                    val = str(value)
                    config.SHORTENER_API_KEY = val
                    for m in list(sys.modules.values()):
                        if m:
                            if hasattr(m, 'SHORTENER_API_KEY'):
                                try: setattr(m, 'SHORTENER_API_KEY', val)
                                except: pass
                            if hasattr(m, 'shortener_api'):
                                try: setattr(m, 'shortener_api', val)
                                except: pass

    async def update_settings(self, data: dict, bot_username: str = None):
        GLOBAL_ONLY_FIELDS = [
            'shortener_url', 'shortener_api', 'shorteners', 'shortener_active', 'shortener',
            'website_url', 'api_url', 'base_url', 'cdn_url', 'owner_tag', 'upi_id',
            'anime_banners', 'video_banners', 'app_id', 'api_hash', 'owner_id',
            'use_recaptcha', 'recaptcha_site_key', 'recaptcha_secret_key',
            'use_turnstile', 'turnstile_secret_key', 'verify_log_destinations',
            'verify_bot_active', 'verify_api_url', 'verify_api_secret', 'verify_bot_username'
        ]

        global_data = {}
        bot_data = {}

        for k, v in data.items():
            if k in GLOBAL_ONLY_FIELDS:
                global_data[k] = v
            else:
                bot_data[k] = v

        if global_data:
            await self.settings_data.update_one(
                {'_id': 'bot_settings'},
                {'$set': global_data},
                upsert=True
            )
            self.settings_cache.clear()

        if bot_data and bot_username:
            bot_username = bot_username.lower().replace("@", "")
            await self.settings_data.update_one(
                {'_id': f'bot_settings_{bot_username}'},
                {'$set': bot_data},
                upsert=True
            )
            self.settings_cache.clear()


    # USER DATA
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id, 'warnings': 0})
        return

    async def get_warnings(self, user_id: int):
        user = await self.user_data.find_one({'_id': int(user_id)})
        if user:
            return user.get('warnings', 0)
        return 0

    async def increment_warnings(self, user_id: int):
        await self.user_data.update_one({'_id': int(user_id)}, {'$inc': {'warnings': 1}}, upsert=True)
        user = await self.user_data.find_one({'_id': int(user_id)})
        if user and user.get('warnings', 0) >= 3:
            await self.add_ban_user(int(user_id))
            return True # Banned
        return False

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in user_docs]
        return user_ids

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})
        return


    # ADMIN DATA
    async def admin_exist(self, admin_id: int):
        now = time.time()
        if admin_id in self.admin_cache:
            val, expiry = self.admin_cache[admin_id]
            if now < expiry:
                return val
        found = await self.admins_data.find_one({'_id': admin_id})
        is_admin = bool(found)
        self.admin_cache[admin_id] = (is_admin, now + 30)
        return is_admin

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})
        self.admin_cache[admin_id] = (True, time.time() + 30)

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})
        self.admin_cache[admin_id] = (False, time.time() + 30)

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids


    # BAN USER DATA
    async def ban_user_exist(self, user_id: int):
        now = time.time()
        if user_id in self.banned_user_cache:
            val, expiry = self.banned_user_cache[user_id]
            if now < expiry:
                return val
        found = await self.banned_user_data.find_one({'_id': user_id})
        is_banned = bool(found)
        self.banned_user_cache[user_id] = (is_banned, now + 30)
        return is_banned

    async def is_user_banned(self, user_id: int):
        return await self.ban_user_exist(user_id)

    async def add_ban_user(self, user_id: int, reason="No Reason Provided"):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id, 'reason': reason})
        else:
            await self.banned_user_data.update_one({'_id': user_id}, {'$set': {'reason': reason}})
        await self.log_event(user_id, "USER_BANNED", f"Reason: {reason}")
        self.banned_user_cache[user_id] = (True, time.time() + 30)

    async def get_ban_user_data(self, user_id: int):
        return await self.banned_user_data.find_one({'_id': user_id})

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})
            await self.log_event(user_id, "USER_UNBANNED", "Admin removed ban.")
        self.banned_user_cache[user_id] = (False, time.time() + 30)

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        user_ids = [doc['_id'] for doc in users_docs]
        return user_ids

    async def get_all_banned_users(self):
        return await self.banned_user_data.find().to_list(length=None)



    # AUTO DELETE TIMER SETTINGS
    async def set_del_timer(self, value: int):        
        existing = await self.del_timer_data.find_one({})
        if existing:
            await self.del_timer_data.update_one({}, {'$set': {'value': value}})
        else:
            await self.del_timer_data.insert_one({'value': value})
        self.del_timer_cache = value

    async def get_del_timer(self):
        if self.del_timer_cache is not None:
            return self.del_timer_cache
        data = await self.del_timer_data.find_one({})
        val = 900
        if data:
            val = data.get('value', 900)
        self.del_timer_cache = val
        return val


    # CHANNEL MANAGEMENT (Force Sub)
    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def show_channels(self, use_cache=True):
        if use_cache and self.channels_cache:
            return self.channels_cache

        channel_docs = await self.fsub_data.find().to_list(length=None)
        channel_ids = [doc['_id'] for doc in channel_docs]
        self.channels_cache = channel_ids
        return channel_ids

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})
            self.channels_cache = None
            return

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})
            self.channels_cache = None
            return

    # DATABASE CHANNEL MANAGEMENT (Storage) - BOT SPECIFIC
    async def db_channel_exist(self, channel_id: int, bot_username: str):
        if not bot_username: return False
        bot_username = bot_username.lower().replace("@", "").strip()
        found = await self.channel_data.find_one({'channel_id': int(channel_id), 'bot_username': bot_username})
        return bool(found)

    async def get_all_db_channels(self, bot_username: str):
        if not bot_username: return []
        bot_username = bot_username.lower().replace("@", "").strip()
        docs = await self.channel_data.find({'bot_username': bot_username}).to_list(length=None)
        return [doc['channel_id'] for doc in docs]

    async def add_db_channel(self, channel_id: int, bot_username: str):
        if not bot_username: return False
        bot_username = bot_username.lower().replace("@", "").strip()
        if not await self.db_channel_exist(channel_id, bot_username):
            await self.channel_data.insert_one({'channel_id': int(channel_id), 'bot_username': bot_username})
            return True
        return False

    async def del_db_channel(self, channel_id: int, bot_username: str):
        if not bot_username: return False
        bot_username = bot_username.lower().replace("@", "").strip()
        if await self.db_channel_exist(channel_id, bot_username):
            await self.channel_data.delete_one({'channel_id': int(channel_id), 'bot_username': bot_username})
            return True
        return False

    async def block_session(self, session_id: str):
        await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"blocked": True, "status": "blocked"}}
        )

    # BOT-SPECIFIC SETTINGS
    async def get_bot_settings(self, bot_username: str):
        settings = await self.settings_data.find_one({'_id': f'bot_settings_{bot_username}'})
        if not settings:
            default = {
                '_id': f'bot_settings_{bot_username}',
                'shortener_active': True,
                'db_channels': [] # Legacy support if needed, but we use channel_data collection
            }
            await self.settings_data.insert_one(default)
            return default
        return settings

    async def update_bot_setting(self, bot_username: str, key: str, value):
        await self.settings_data.update_one(
            {'_id': f'bot_settings_{bot_username}'},
            {'$set': {key: value}},
            upsert=True
        )

    
# Get current mode of a channel
    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    # Set mode of a channel
    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # REQUEST FORCE-SUB MANAGEMENT

    # Add the user to the set of users for a   specific channel
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")


    # Method 2: Remove a user from the channel set
    async def del_req_user(self, channel_id: int, user_id: int):
        # Remove the user from the set of users for the channel
        await self.rqst_fsub_Channel_data.update_one(
            {'_id': channel_id}, 
            {'$pull': {'user_ids': user_id}}
        )

    # Check if the user exists in the set of the channel's users
    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False  


    # Method to check if a channel exists using show_channels
    async def reqChannel_exist(self, channel_id: int):
    # Get the list of all channel IDs from the database
        channel_ids = await self.show_channels()
        #print(f"All channel IDs in the database: {channel_ids}")

    # Check if the given channel_id is in the list of channel IDs
        if channel_id in channel_ids:
            #print(f"Channel {channel_id} found in the database.")
            return True
        else:
            #print(f"Channel {channel_id} NOT found in the database.")
            return False



    # COOLDOWN MANAGEMENT
    async def check_cooldown(self, identifier: str, cooldown_seconds: int = 5):
        record = await self.cooldown_data.find_one({'_id': identifier})
        if not record:
            return True

        last_time = record.get('last_time', 0)
        if time.time() - last_time < cooldown_seconds:
            return False
        return True

    async def update_cooldown(self, identifier: str):
        await self.cooldown_data.update_one(
            {'_id': identifier},
            {'$set': {'last_time': time.time()}},
            upsert=True
        )


    # VERIFICATION MANAGEMENT
    async def db_verify_status(self, user_id):
        user = await self.user_data.find_one({'_id': user_id})
        if user:
            return user.get('verify_status', default_verify)
        return default_verify

    async def db_update_verify_status(self, user_id, verify):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

    async def get_verify_status(self, user_id):
        verify = await self.db_verify_status(user_id)
        return verify

    async def update_verify_status(self, user_id, verify_token="", is_verified=False, verified_time=0, link=""):
        current = await self.db_verify_status(user_id)
        current['verify_token'] = verify_token
        current['is_verified'] = is_verified
        current['verified_time'] = verified_time
        current['link'] = link
        await self.db_update_verify_status(user_id, current)

    # Set verify count
    async def set_verify_count(self, user_id: int, count: int):
        await self.sex_data.update_one({'_id': user_id}, {'$set': {'verify_count': count}}, upsert=True)

    # Get verify count
    async def get_verify_count(self, user_id: int):
        user = await self.sex_data.find_one({'_id': user_id})
        if user:
            return user.get('verify_count', 0)
        return 0

    # Reset all users' verify counts
    async def reset_all_verify_counts(self):
        await self.sex_data.update_many({}, {'$set': {'verify_count': 0}})

    # Get total verify count
    async def get_total_verify_count(self):
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$verify_count"}}}]
        result = await self.sex_data.aggregate(pipeline).to_list(length=1)
        return result[0]["total"] if result else 0

    async def is_user_verified(self, user_id: int, bot_username: str = None):
        cache_key = (user_id, bot_username.lower().replace("@", "").strip() if bot_username else None)
        now = time.time()
        if cache_key in self.verified_user_cache:
            val, expiry = self.verified_user_cache[cache_key]
            if now < expiry:
                return val

        # 1. Premium users are ALWAYS verified across all bots and services
        from database.db_premium import is_premium_user
        if await is_premium_user(user_id):
            self.verified_user_cache[cache_key] = (True, now + 10)
            return True

        user = await self.user_data.find_one({'_id': user_id})
        if not user:
            self.verified_user_cache[cache_key] = (False, now + 10)
            return False

        if bot_username:
            bot_username = bot_username.lower().replace("@", "")
            bot_ver = user.get('bot_verifications', {}).get(bot_username, {})
            verified = bot_ver.get('verified', False)
            expires_at = bot_ver.get('expires_at', 0)
            remaining_access = bot_ver.get('remaining_access', 0)

            if verified and now < expires_at and (remaining_access > 0 or remaining_access == -1):
                self.verified_user_cache[cache_key] = (True, now + 10)
                return True

            # If it was marked verified but expired or ran out of accesses, update DB status to invalid
            if verified:
                await self.user_data.update_one(
                    {'_id': user_id},
                    {'$set': {
                        f'bot_verifications.{bot_username}.verified': False,
                        f'bot_verifications.{bot_username}.remaining_access': 0
                    }}
                )
            self.verified_user_cache[cache_key] = (False, now + 10)
            return False

        # Fallback to global
        verified = user.get('verified', False)
        expires_at = user.get('expires_at', 0)
        remaining_access = user.get('remaining_access', 0)
        if verified and now < expires_at and (remaining_access > 0 or remaining_access == -1):
            self.verified_user_cache[cache_key] = (True, now + 10)
            return True
        if verified:
            await self.user_data.update_one(
                {'_id': user_id},
                {'$set': {
                    'verified': False,
                    'remaining_access': 0
                }}
            )
        self.verified_user_cache[cache_key] = (False, now + 10)
        return False

    async def set_user_verified(self, user_id: int, bot_username: str = None, token: str = ""):
        settings = await self.get_settings(bot_username=bot_username)
        limit = settings.get('access_limit', 1)
        window = settings.get('verify_window', 86400)

        now = time.time()
        expires = now + window

        update_doc = {
            'verified': True,
            'verified_at': now,
            'expires_at': expires,
            'remaining_access': limit,
            'verification_token': token,
            'verification_method': 'shortlink',
            'last_verified': now,
            'last_access': now
        }

        # Keep legacy compatibility fields
        update_doc['last_verified'] = now
        update_doc['access_credits'] = limit

        if bot_username:
            bot_username = bot_username.lower().replace("@", "")
            update_doc[f'bot_verifications.{bot_username}'] = {
                'verified': True,
                'verified_at': now,
                'expires_at': expires,
                'remaining_access': limit,
                'verification_token': token,
                'verification_method': 'shortlink',
                'last_verified': now,
                'last_access': now,
                'access_credits': limit # Legacy compat
            }

        await self.user_data.update_one(
            {'_id': user_id},
            {'$set': update_doc},
            upsert=True
        )

        # Clear/update verified user cache
        cache_key = (user_id, bot_username.lower().replace("@", "").strip() if bot_username else None)
        self.verified_user_cache[cache_key] = (True, now + 10)
        self.verified_user_cache[(user_id, None)] = (True, now + 10)

        # Record verification history for /count command
        import pytz
        from datetime import datetime
        ist = pytz.timezone("Asia/Kolkata")
        dt = datetime.fromtimestamp(now, tz=ist)
        date_str = dt.strftime("%d-%m-%Y")

        await self.database["verifications_history"].insert_one({
            "user_id": int(user_id),
            "verified_at": now,
            "expires_at": expires,
            "date_str": date_str
        })

    async def decrement_user_credits(self, user_id: int, bot_username: str = None):
        self.verified_user_cache.pop((user_id, bot_username.lower().replace("@", "").strip() if bot_username else None), None)
        self.verified_user_cache.pop((user_id, None), None)

        user = await self.user_data.find_one({'_id': user_id})
        if not user: return None

        now = time.time()
        if bot_username:
            bot_username = bot_username.lower().replace("@", "")
            bot_ver = user.get('bot_verifications', {}).get(bot_username, {})
            credits = bot_ver.get('remaining_access', bot_ver.get('access_credits', 0))
            if credits == -1:
                await self.user_data.update_one(
                    {'_id': user_id},
                    {'$set': {f'bot_verifications.{bot_username}.last_access': now}}
                )
                return user

            if credits > 0:
                new_credits = credits - 1
                is_verified = (new_credits > 0)
                return await self.user_data.find_one_and_update(
                    {'_id': user_id},
                    {'$set': {
                        f'bot_verifications.{bot_username}.remaining_access': new_credits,
                        f'bot_verifications.{bot_username}.verified': is_verified,
                        f'bot_verifications.{bot_username}.last_access': now,
                        f'bot_verifications.{bot_username}.access_credits': new_credits # Legacy compat
                    }},
                    return_document=pymongo.ReturnDocument.AFTER
                )
            return None

        # Fallback to global
        credits = user.get('remaining_access', user.get('access_credits', 0))
        if credits == -1:
            await self.user_data.update_one(
                {'_id': user_id},
                {'$set': {'last_access': now}}
            )
            return user # Unlimited

        if credits > 0:
            new_credits = credits - 1
            is_verified = (new_credits > 0)
            return await self.user_data.find_one_and_update(
                {'_id': user_id},
                {'$set': {
                    'remaining_access': new_credits,
                    'verified': is_verified,
                    'last_access': now,
                    'access_credits': new_credits # Legacy compat
                }},
                return_document=pymongo.ReturnDocument.AFTER
            )
        return None

    async def check_daily_limit(self, user_id: int, bot_username: str = None):
        settings = await self.get_settings(bot_username=bot_username)
        limit = settings.get('daily_verify_limit', 5)

        count = await self.get_verify_count(user_id)
        if count >= limit:
            return False, limit
        return True, limit

    async def set_verified_worker(self, bot_username: str, user_id: int):
        """Mark a user as shortener-verified with current timestamp for a specific worker/bot."""
        bot_username = bot_username.lower().replace("@", "")
        coll = self.database[f"bot_{bot_username}_verify"]
        await coll.update_one(
            {"_id": user_id},
            {"$set": {"verified_at": time.time()}},
            upsert=True
        )

    async def is_verified_worker(self, bot_username: str, user_id: int, expire_seconds: int) -> bool:
        """Check if a user's verification is still valid for a specific worker/bot."""
        bot_username = bot_username.lower().replace("@", "")
        coll = self.database[f"bot_{bot_username}_verify"]
        doc = await coll.find_one({"_id": user_id})
        if not doc:
            return False
        verified_at = doc.get("verified_at")
        if not verified_at:
            return False
        elapsed = time.time() - verified_at
        return elapsed < expire_seconds


    # URL SHORTENER GATE - SESSION MANAGEMENT
    async def get_verify_token(self, token):
        # Strip underscores to get raw token for compatibility
        normalized = token.replace("___", "")
        hyphenated = normalized.replace("_", "-")
        underscored = normalized.replace("-", "_")
        tokens = [token, normalized, hyphenated, underscored]
        # Search by session_id, mask_token or short_token
        query = {
            "$or": [
                {"session_id": {"$in": tokens}},
                {"mask_token": {"$in": tokens}},
                {"short_token": {"$in": tokens}},
                {"alias": {"$in": tokens}}
            ],
            "expiry": {"$gt": time.time()}
        }
        return await self.sessions.find_one(query)

    async def update_token_status(self, token, status):
        await self.sessions.update_one(
            {"$or": [{"session_id": token}, {"mask_token": token}, {"short_token": token}]},
            {"$set": {"status": status}}
        )

    async def start_token_timer(self, token):
        await self.sessions.update_one(
            {"$or": [{"session_id": token}, {"mask_token": token}, {"short_token": token}]},
            {"$set": {"status": "timer_started", "timer_start_at": time.time()}}
        )

    def generate_hmac_token(self, data):
        return hmac.new(config.API_HASH.encode(), data.encode(), hashlib.sha256).hexdigest()

    async def create_verification_session(self, user_id, content_id, referral_id=None, bot_username=None):
        session_id = str(uuid.uuid4()).replace("-", "_")
        # Enhance token with user_id, content_id and timestamp for higher entropy
        token_payload = f"{session_id}:{user_id}:{content_id}:{time.time()}"
        raw_mask = self.generate_hmac_token(token_payload)

        # Generate custom alphanumeric short token with 6 characters
        import string
        short_token_raw = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        wrapped_token = f"___{short_token_raw}___"

        # Highly complex obfuscated token format with underscore padding
        entropy = secrets.token_hex(8)
        mask_token = f"_____{raw_mask[:16]}_____{session_id}_____{entropy}_____"

        settings = await self.get_settings(bot_username=bot_username)
        access_limit = settings.get('access_limit', 1)

        # Random Shortener Selection (Always randomize if multiple available)
        shorteners = settings.get('shorteners', [])
        selected_short_url = settings.get('shortener_url', config.SHORTENER_URL)
        selected_short_api = settings.get('shortener_api', config.SHORTENER_API_KEY)
        session_verification_method = settings.get('verification_method', 'mini_app')

        if shorteners:
            short = random.choice(shorteners)
            selected_short_url = short.get('url')
            selected_short_api = short.get('api')
            sh_method = short.get('verification_method', 'global')
            if sh_method and sh_method != 'global':
                session_verification_method = sh_method

        await self.log_stat('total_verifications')

        await self.sessions.insert_one({
            "session_id": session_id,
            "user_id": str(user_id),
            "bot_username": bot_username,
            "content_id": content_id,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "expiry": int(time.time() + 86400), # 24 hours (generous expiry to avoid transient session expiry errors)
            "mask_token": mask_token,
            "short_token": wrapped_token,
            "secure_token": None,
            "gate_cleared": False,
            "tab_id": None,
            "ip": None,
            "ip_history": [],
            "user_agent": None,
            "fingerprint": None,
            "frontend_viewed": False,
            "referral_id": str(referral_id) if referral_id else None,
            "access_count": access_limit,
            "usage_count": 0,
            "shortener_url": selected_short_url,
            "shortener_api": selected_short_api,
            "verification_method": session_verification_method
        })
        return session_id, wrapped_token

    async def get_session_by_mask_token(self, mask_token):
        return await self.sessions.find_one({"mask_token": mask_token, "expiry": {"$gt": time.time()}})

    async def update_session_security(self, session_id, tab_id, ip=None, user_agent=None):
        update_data = {"tab_id": tab_id}
        if ip: update_data["ip"] = ip
        if user_agent: update_data["user_agent"] = user_agent

        await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )

    async def verify_session(self, session_id, short_token):
        await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "verified", "short_token": short_token}}
        )

    async def get_session_by_token(self, token):
        # The bot receives verify_{TOKEN}
        # We check session_id (Standard UUID), short_token (standard), mask_token (fallback), or secure_token (legacy)
        # We allow "verified" or "blocked" status to let the bot show appropriate messages
        # Allow retrieve of verified sessions without strict expiry check to prevent false-positives
        query = {"status": {"$in": ["verified", "blocked"]}}

        normalized = token.replace("___", "")
        # Resilience: Try matching both hyphen and underscore versions
        tokens = [
            token, token.replace("-", "_"), token.replace("_", "-"),
            normalized, normalized.replace("-", "_"), normalized.replace("_", "-")
        ]

        # Combine all checks into a single, high-performance $or query with 1 roundtrip
        combined_query = {
            **query,
            "$or": [
                {"session_id": {"$in": tokens}},
                {"short_token": {"$in": tokens}},
                {"mask_token": {"$in": tokens}},
                {"secure_token": {"$in": tokens}},
                {"alias": {"$in": tokens}}
            ]
        }
        return await self.sessions.find_one(combined_query)

    async def mark_session_used(self, session_id):
        await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "used"}}
        )
        # Update stats
        await self.settings_data.update_one(
            {'_id': 'bot_stats'},
            {'$inc': {'successful_verifications': 1}},
            upsert=True
        )

    async def log_stat(self, stat_name):
        await self.settings_data.update_one(
            {'_id': 'bot_stats'},
            {'$inc': {stat_name: 1}},
            upsert=True
        )

    async def get_stats(self):
        stats = await self.settings_data.find_one({'_id': 'bot_stats'})
        if not stats:
            stats = {
                'total_verifications': 0,
                'successful_verifications': 0,
                'failed_verifications': 0,
                'total_referrals': 0,
                'successful_referrals': 0,
                'failed_referrals': 0,
                'security_alerts': 0,
                'total_bypasses': 0
            }
            await self.settings_data.insert_one({'_id': 'bot_stats', **stats})

        # Add dynamic stats
        now = time.time()
        stats['active_sessions'] = await self.sessions.count_documents({"expiry": {"$gt": now}})
        stats['expired_sessions'] = await self.sessions.count_documents({"expiry": {"$lt": now}})
        stats['today_access'] = await self.get_total_verify_count()

        return stats

    async def cleanup_sessions(self):
        await self.sessions.delete_many({"expiry": {"$lt": time.time()}})

    async def cleanup_strict_verifications(self):
        # Implementation for bot.py scheduler
        await self.cleanup_sessions()
        await self.redirects.delete_many({"expiry": {"$lt": time.time()}})

    async def create_local_redirect(self, url, expire=86400):
        # Always create a new unique token for strict one-time use logic
        token = secrets.token_urlsafe(12)
        await self.redirects.insert_one({
            "token": token,
            "url": url,
            "expiry": int(time.time() + expire),
            "used": False
        })
        return token

    async def get_local_redirect(self, token, delete=False):
        query = {"token": token, "expiry": {"$gt": time.time()}, "used": False}
        doc = await self.redirects.find_one(query)
        if doc and delete:
            await self.redirects.delete_one({"_id": doc["_id"]})
        return doc

    async def mark_redirect_used(self, token):
        await self.redirects.update_one({"token": token}, {"$set": {"used": True}})

    async def get_url_by_token(self, token):
        doc = await self.redirects.find_one({"token": token})
        return doc["url"] if doc else None


    # CLONE MANAGEMENT
    async def add_clone(self, username, token, channel_id):
        if not username: return
        username = username.strip().lower().replace("@", "")
        await self.clones.update_one(
            {"username": username},
            {
                "$set": {
                    "username": username,
                    "token": token.strip(),
                    "channel_id": int(str(channel_id).strip()),
                    "name": username.capitalize(),
                    "banners": config.ANIME_BANNERS,
                    "fsub_channels": [],
                    "community_link": f"https://t.me/{username}"
                }
            },
            upsert=True
        )

    async def get_all_clones(self):
        return await self.clones.find().to_list(length=None)

    async def get_clone(self, username):
        if not username: return None
        username = str(username).strip().lower().replace("@", "")
        return await self.clones.find_one({"username": username})

    async def del_clone(self, username):
        if not username: return
        username = str(username).strip().lower().replace("@", "")
        await self.clones.delete_one({"username": username})

    async def update_clone_setting(self, username, key, value):
        if not username: return
        username = str(username).strip().lower().replace("@", "")
        await self.clones.update_one(
            {"username": username},
            {"$set": {key: value}}
        )

    async def update_clone_token(self, username, token):
        if not username: return
        await self.update_clone_setting(username, "token", token.strip())

    # REQUIRED FSUB BOT MANAGEMENT
    async def add_fsub_bot(self, token, name, username):
        try:
            bot_id = int(token.split(":")[0])
            await self.fsub_bots.update_one(
                {"_id": bot_id},
                {"$set": {"token": token, "name": name, "username": username}},
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"Error adding fsub bot: {e}")
            return False

    async def del_fsub_bot(self, bot_id: int):
        await self.fsub_bots.delete_one({"_id": bot_id})

    async def get_fsub_bots(self):
        return await self.fsub_bots.find().to_list(length=None)

    # LOGGING
    async def log_event(self, user_id: int, event_type: str, details: str):
        log_entry = {
            "user_id": int(user_id),
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.utcnow()
        }
        await self.logs.insert_one(log_entry)

    async def get_recent_logs(self, limit=50):
        return await self.logs.find().sort("timestamp", pymongo.DESCENDING).limit(limit).to_list(length=None)

    async def get_user_logs(self, user_id: int, limit=50):
        return await self.logs.find({"user_id": int(user_id)}).sort("timestamp", pymongo.DESCENDING).limit(limit).to_list(length=None)

    # REFERRAL SYSTEM
    async def add_referral(self, referrer_id, referred_id):
        if str(referrer_id) == str(referred_id):
            return False

        existing = await self.referrals.find_one({"referred_id": str(referred_id)})
        if existing:
            return False

        await self.log_stat('total_referrals')

        await self.referrals.insert_one({
            "referrer_id": str(referrer_id),
            "referred_id": str(referred_id),
            "created_at": datetime.utcnow(),
            "status": "pending",
            "verified": False,
            "content_accessed": False
        })
        return True

    async def update_referral_status(self, referred_id, status, verified=None, content_accessed=None):
        update_data = {"status": status}
        if verified is not None: update_data["verified"] = verified
        if content_accessed is not None: update_data["content_accessed"] = content_accessed

        if status == "completed":
            await self.log_stat('successful_referrals')
        elif status == "failed":
            await self.log_stat('failed_referrals')

        await self.referrals.update_one(
            {"referred_id": str(referred_id)},
            {"$set": update_data}
        )

    async def get_referral_stats(self, user_id=None):
        if user_id:
            total = await self.referrals.count_documents({"referrer_id": str(user_id)})
            success = await self.referrals.count_documents({"referrer_id": str(user_id), "status": "completed"})
            return {"total": total, "success": success}
        else:
            total = await self.referrals.count_documents({})
            success = await self.referrals.count_documents({"status": "completed"})
            return {"total": total, "success": success}

    # SESSION ACCESS LIMIT
    async def decrement_access_count(self, session_id):
        # Handle unlimited access (-1) or positive count
        session = await self.sessions.find_one({"session_id": session_id})
        if not session: return None

        if session.get("access_count") == -1:
            return await self.sessions.find_one_and_update(
                {"session_id": session_id},
                {"$inc": {"usage_count": 1}},
                return_document=pymongo.ReturnDocument.AFTER
            )

        return await self.sessions.find_one_and_update(
            {"session_id": session_id, "access_count": {"$gt": 0}},
            {"$inc": {"access_count": -1, "usage_count": 1}},
            return_document=pymongo.ReturnDocument.AFTER
        )

    async def check_session_access(self, session_id):
        session = await self.sessions.find_one({"session_id": session_id})
        if not session:
            return False
        if session.get("access_count", 0) > 0 or session.get("access_count") == -1: # -1 for unlimited
            return True
        return False

    # RESTART TASKS
    async def clear_all_bans(self):
        await self.banned_user_data.delete_many({})

    # SHORTENER & VIDEO MANAGEMENT (Always Global)
    async def add_shortener(self, url, api, bot_username=None):
        # We always fetch global settings for these
        settings = await self.get_settings()
        shorteners = settings.get('shorteners', [])
        shorteners.append({"url": url.strip(), "api": api.strip()})
        await self.update_setting("shorteners", shorteners)

    async def del_shortener(self, index, bot_username=None):
        settings = await self.get_settings()
        shorteners = settings.get('shorteners', [])
        if 0 <= index < len(shorteners):
            shorteners.pop(index)
            await self.update_setting("shorteners", shorteners)
            return True
        return False

    async def add_video_banner(self, url, bot_username=None):
        settings = await self.get_settings()
        videos = settings.get('video_banners', [])
        videos.append(url.strip())
        await self.update_setting("video_banners", videos)

    async def del_video_banner(self, index, bot_username=None):
        settings = await self.get_settings()
        videos = settings.get('video_banners', [])
        if 0 <= index < len(videos):
            videos.pop(index)
            await self.update_setting("video_banners", videos)
            return True
        return False

    # HELPER BOT MANAGEMENT
    async def add_helper_bot(self, token, username):
        await self.helpers.update_one(
            {"token": token},
            {"$set": {"token": token, "username": username}},
            upsert=True
        )

    async def get_helper_bots(self):
        return await self.helpers.find().to_list(length=None)

    async def del_helper_bot(self, token):
        await self.helpers.delete_one({"token": token})

    # BOT ADMIN TASK LOCKS & QUEUE
    def get_bot_admin_lock(self, bot_username, user_id):
        if not bot_username:
            bot_username = "default"
        bot_username = bot_username.lower().replace("@", "").strip()
        key = (bot_username, user_id)
        if key not in self.bot_admin_locks:
            self.bot_admin_locks[key] = asyncio.Lock()
        return self.bot_admin_locks[key]

    # DATA EXPORT/IMPORT
    async def export_data(self, output_dir):
        import json
        from bson import json_util
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        collections = await self.database.list_collection_names()
        for coll_name in collections:
            cursor = self.database[coll_name].find({})
            docs = await cursor.to_list(length=None)
            with open(os.path.join(output_dir, f"{coll_name}.json"), "w") as f:
                json.dump(docs, f, default=json_util.default, indent=4)
        return collections

    async def import_data(self, input_dir):
        import json
        from bson import json_util
        if not os.path.exists(input_dir):
            return False

        for filename in os.listdir(input_dir):
            if filename.endswith(".json"):
                coll_name = filename[:-5]
                with open(os.path.join(input_dir, filename), "r") as f:
                    docs = json.load(f, object_hook=json_util.object_hook)
                    if docs:
                        await self.database[coll_name].delete_many({})
                        await self.database[coll_name].insert_many(docs)
        return True

    # PAYLOAD STORAGE (For short start tokens)
    async def add_payload(self, payload):
        # Check if payload already exists to avoid duplicates
        existing = await self.payloads.find_one({"payload": payload})
        if existing:
            return existing["token"]

        token = secrets.token_urlsafe(8)
        await self.payloads.update_one(
            {"token": token},
            {"$set": {"token": token, "payload": payload, "created_at": datetime.utcnow()}},
            upsert=True
        )
        return token

    async def get_payload(self, token):
        doc = await self.payloads.find_one({"token": token})
        return doc["payload"] if doc else None

    # VERIFY LOG DESTINATIONS
    async def get_verify_log_destinations(self):
        settings = await self.get_settings()
        dests = settings.get('verify_log_destinations', [])
        # Migration fallback for legacy single verify_log_channel
        legacy_chan = settings.get('verify_log_channel')
        if legacy_chan and not dests:
            try:
                cid = int(legacy_chan)
                dests = [{'chat_id': cid, 'type': 'channel', 'title': f'Channel ({cid})'}]
            except:
                pass
        return dests

    async def add_verify_log_destination(self, chat_id: int, chat_type: str, title: str):
        dests = await self.get_verify_log_destinations()
        # Remove duplicates
        dests = [d for d in dests if d['chat_id'] != chat_id]

        channel_count = sum(1 for d in dests if d.get('type') == 'channel')
        group_count = sum(1 for d in dests if d.get('type') == 'group')

        if len(dests) >= 4:
            return False, "Maximum 4 total destinations reached."

        if chat_type == 'channel' and channel_count >= 2:
            return False, "Maximum 2 channel destinations reached."

        if chat_type == 'group' and group_count >= 2:
            return False, "Maximum 2 group destinations reached."

        dests.append({'chat_id': chat_id, 'type': chat_type, 'title': title})
        await self.update_setting('verify_log_destinations', dests)
        return True, "Destination added successfully."

    async def del_verify_log_destination(self, chat_id: int):
        dests = await self.get_verify_log_destinations()
        new_dests = [d for d in dests if d['chat_id'] != chat_id]
        await self.update_setting('verify_log_destinations', new_dests)
        return True


db = AniZoneFlix(DB_URI, DB_NAME)
