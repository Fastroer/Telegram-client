import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from app.db.models import User, Message
from .conftest import async_session_maker

@pytest.mark.asyncio
@patch("app.services.telegram_service.TelegramClient.qr_login", new_callable=AsyncMock)
@patch("app.services.telegram_service.TelegramClient.is_user_authorized", new_callable=AsyncMock)
async def test_login_qr(mock_is_user_authorized, mock_qr_login, ac_public: AsyncClient):
    mock_is_user_authorized.return_value = False
    mock_qr_login.return_value.url = "http://localhost:8000/sessions/1234567890_qr.png"
    
    response = await ac_public.post("/login", params={"phone": "1234567890"})
    
    assert response.status_code == 200
    assert "qr_url" in response.json()
    assert response.json()["qr_url"] == "http://localhost:8000/sessions/1234567890_qr.png"


@pytest.mark.asyncio
@patch("app.services.telegram_service.TelegramClient.is_user_authorized", new_callable=AsyncMock)
async def test_check_login(mock_is_user_authorized, ac_public: AsyncClient):
    mock_is_user_authorized.return_value = True
    
    user = User(phone="1234567890", status="inactive")
    async with async_session_maker() as session:
        session.add(user)
        await session.commit()
    
    response = await ac_public.get("/check/login", params={"phone": "1234567890"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_fetch_messages(ac_public: AsyncClient):
    user = User(phone="1234567890", status="active")
    async with async_session_maker() as session:
        session.add(user)
        await session.commit()
        
        message = Message(
            chat_id=1,
            sender_id=1,
            sender_username="testuser",
            text="Hello, this is a test message.",
            is_self=True,
            user_id=user.id,
            recipient_username="testrecipient"
        )
        session.add(message)
        await session.commit()

    response = await ac_public.get("/messages", params={"phone": "1234567890", "uname": "testrecipient"})
    
    assert response.status_code == 200
    assert "messages" in response.json()
    assert len(response.json()["messages"]) == 1
    assert response.json()["messages"][0]["message_text"] == "Hello, this is a test message."


@pytest.mark.asyncio
@patch("app.services.telegram_service.TelegramClient.send_message", new_callable=AsyncMock)
async def test_create_message(mock_send_message, ac_public: AsyncClient):
    mock_send_message.return_value = None

    user = User(phone="1234567890", status="active")
    async with async_session_maker() as session:
        session.add(user)
        await session.commit()

    message_data = {
        "from_phone": "1234567890",
        "username": "testrecipient",
        "message_text": "Hello, this is a test message."
    }
    
    response = await ac_public.post("/messages", json=message_data)
    
    assert response.status_code == 200
    assert response.json() == {"status": "Message sent"}

    async with async_session_maker() as session:
        db_message = await session.execute(select(Message).filter_by(user_id=user.id, recipient_username="testrecipient"))
        db_message = db_message.scalars().first()
        
        assert db_message is not None
        assert db_message.text == "Hello, this is a test message."
        assert db_message.sender_username == "testrecipient"
