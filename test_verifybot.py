import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

import config
from web_server import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_verifybot_db_settings():
    from database.database import AniZoneFlix
    with patch("motor.motor_asyncio.AsyncIOMotorClient") as mock_motor:
        mock_db = MagicMock()
        mock_settings = AsyncMock()
        mock_db.settings_data = mock_settings

        # Test default settings
        mock_settings.find_one = AsyncMock(return_value=None)
        mock_settings.insert_one = AsyncMock()

        db_inst = AniZoneFlix("mongodb://localhost:27017", "test_db")
        db_inst.settings_data = mock_settings

        settings = await db_inst.get_settings(use_cache=False)
        assert "verify_bot_active" in settings
        assert settings["verify_bot_active"] is False
        assert settings["verify_api_url"] == getattr(config, "VERIFY_API_URL", "https://your-verify-api.example.com")
        assert settings["verify_api_secret"] == getattr(config, "VERIFY_API_SECRET", "your_random_api_secret")
        assert settings["verify_bot_username"] == getattr(config, "VERIFY_BOT_USERNAME", "YourVerifyBot")

@pytest.mark.asyncio
async def test_verifybot_api_endpoints():
    secret = getattr(config, "VERIFY_API_SECRET", "your_random_api_secret")
    headers = {"Authorization": f"Bearer {secret}"}

    with patch("database.database.db.get_settings", new_callable=AsyncMock) as mock_get_settings, \
         patch("database.database.db.is_user_verified", new_callable=AsyncMock) as mock_is_verified, \
         patch("database.database.db.set_user_verified", new_callable=AsyncMock) as mock_set_verified, \
         patch("database.database.db.set_verified_worker", new_callable=AsyncMock) as mock_set_worker:

        mock_get_settings.return_value = {
            "verify_api_secret": secret,
            "verify_bot_active": True
        }
        mock_is_verified.side_effect = [False, True]

        # Status endpoint before verification
        response = client.get("/api/verifybot/status?user_id=999888&bot_username=testbot", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 999888
        assert data["bot_username"] == "testbot"
        assert data["is_verified"] is False

        # Verify endpoint
        verify_payload = {
            "user_id": 999888,
            "originating_bot": "testbot",
            "session_id": "test_session_123"
        }
        response = client.post("/api/verifybot/verify", json=verify_payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Status endpoint after verification
        response = client.get("/api/verifybot/status?user_id=999888&bot_username=testbot", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True

@pytest.mark.asyncio
async def test_verifybot_api_unauthorized():
    bad_headers = {"Authorization": "Bearer wrong_secret"}
    with patch("database.database.db.get_settings", new_callable=AsyncMock) as mock_get_settings:
        mock_get_settings.return_value = {
            "verify_api_secret": getattr(config, "VERIFY_API_SECRET", "your_random_api_secret")
        }

        response = client.get("/api/verifybot/status?user_id=999888&bot_username=testbot", headers=bad_headers)
        assert response.status_code == 401

        response = client.post("/api/verifybot/verify", json={"user_id": 999888, "originating_bot": "testbot"}, headers=bad_headers)
        assert response.status_code == 401
