import json
import os
import aiohttp
import asyncio
from typing import List, Dict, Union
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
import qrcode
from app.config import settings
from app.db.models import User, Message
from app.schemas import MessageCreate

clients: Dict[str, TelegramClient] = {}

async def get_client(phone: str) -> TelegramClient:
    """
    Retrieve or create a Telegram client for a given phone number.
    """
    if phone in clients:
        return clients[phone]
    client = TelegramClient(StringSession(), settings.api_id, settings.api_hash)
    clients[phone] = client
    return client

async def login_qr(phone: str, session: AsyncSession) -> str:
    """
    Initiate QR code login for a given phone number.
    """
    user = await session.execute(select(User).filter_by(phone=phone))
    user = user.scalars().first()

    if user is None:
        user = User(phone=phone, status="pending")
        session.add(user)
        await session.commit()

    client = await get_client(phone)

    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        qr_login = await client.qr_login()
        qr_code_url = qr_login.url

        qr = qrcode.make(qr_code_url)
        qr_code_path = f'app/sessions/{phone}_qr.png'
        qr.save(qr_code_path)

        return f'http://localhost:8000/sessions/{phone}_qr.png'
    raise HTTPException(status_code=403, detail="User is already authorized")

async def check_login_status(phone: str, session: AsyncSession) -> str:
    """
    Check the login status of a user by phone number.
    """
    user = await session.execute(select(User).filter_by(phone=phone))
    user = user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    client = await get_client(phone)

    if not client.is_connected():
        await client.connect()
    try:
        if await client.is_user_authorized():
            user.status = "active"
            await session.commit()
            qr_code_path = f'app/sessions/{phone}_qr.png'
            if os.path.exists(qr_code_path):
                os.remove(qr_code_path)
            return "active"
        else:
            user.status = "inactive"
            await session.commit()
            return user.status
    except:
        user.status = "inactive"
        await session.commit()
        return user.status

async def wait_for_authorization(phone: str, session: AsyncSession) -> None:
    """
    Wait for the user to authorize via QR code.
    """
    client = await get_client(phone)
    qr_login = await client.qr_login()
    r = False
    while not r:
        try:
            r = await qr_login.wait(10)
        except SessionPasswordNeededError:
            await client.sign_in(password="")
            r = True
        except:
            await qr_login.recreate()
    user = await session.execute(select(User).filter_by(phone=phone))
    user = user.scalars().first()
    if user:
        if await client.is_user_authorized():
            user.status = "active"
            user.session_name = client.session.save()
            qr_code_path = f'app/sessions/{phone}_qr.png'
            if os.path.exists(qr_code_path):
                os.remove(qr_code_path)
        else:
            user.status = "inactive"
        await session.commit()
        client.add_event_handler(lambda event: new_message_handler(event, session), events.NewMessage(incoming=True, outgoing=True))

async def fetch_products(session: aiohttp.ClientSession, params: Dict[str, str], required_count: int) -> List[Dict[str, Union[str, int]]]:
    """
    Fetch products from Wildberries until the required count is reached.
    """
    api_url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    products = []

    page = 1
    while len(products) < required_count:
        params['page'] = str(page)
        async with session.get(api_url, params=params) as response:
            text = await response.text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return []

            if 'data' in data and 'products' in data['data']:
                products.extend(data['data']['products'])
            else:
                break

        page += 1

    return products[:required_count]

async def parse_wildberries() -> List[str]:
    """
    Parse Wildberries to retrieve product information.
    """
    params = {
        'appType': '1',
        'curr': 'rub',
        'dest': '-1029256,-102269,-2162196,-1255563',
        'regions': '77',
        'resultset': 'catalog',
        'query': 'любой товар',
        'sort': 'popular',
        'spp': '0'
    }

    async with aiohttp.ClientSession() as session:
        products = await fetch_products(session, params, 10)

        product_list = [
            f"{product.get('name')} - {product.get('salePriceU') / 100} руб. - https://www.wildberries.ru/catalog/{product.get('id')}/detail.aspx"
            for product in products
        ]

        return product_list

async def new_message_handler(event, session: AsyncSession) -> None:
    """
    Handle new incoming messages.
    """
    client = event.client
    session_name = client.session.save()
    user = await session.execute(select(User).filter_by(session_name=session_name))
    user = user.scalars().first()
    if user:
        sender = await event.get_sender()
        recipient_username = await event.get_chat()
        try:
            if "wild: любой товар" in event.message.message:
                products = await parse_wildberries()
                await client.send_message(event.chat_id, "\n".join(products))
            message = Message(
                chat_id=event.chat_id,
                sender_id=event.sender_id,
                sender_username=sender.username if sender and hasattr(sender, 'username') else 'unknown',
                text=event.message.message,
                is_self=event.out,
                user_id=user.id,
                recipient_username=recipient_username.username if recipient_username and hasattr(recipient_username, 'username') else 'unknown'
            )
            session.add(message)
            await session.commit()
        except Exception as e:
            if session.is_active:
                await session.rollback()
            raise e

async def get_messages(phone: str, uname: str, session: AsyncSession) -> List[Dict[str, Union[str, bool]]]:
    """
    Retrieve the last 50 messages for a given user and username.
    """
    user = await session.execute(select(User).filter_by(phone=phone))
    user = user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    messages_query = await session.execute(
        select(Message).filter_by(user_id=user.id, recipient_username=uname).order_by(Message.id.desc()).limit(50)
    )
    messages = messages_query.scalars().all()

    return [{
        "username": message.sender_username,
        "is_self": message.is_self,
        "message_text": message.text
    } for message in messages]

async def send_message(message_data: MessageCreate, session: AsyncSession) -> None:
    """
    Send a message and save it to the database.
    """
    user = await session.execute(select(User).filter_by(phone=message_data.from_phone))
    user = user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    client = await get_client(user.phone)
    if not client.is_connected():
        await client.connect()

    await client.send_message(message_data.username, message_data.message_text)

    try:
        message = Message(
            chat_id=None, 
            sender_id=user.id,
            sender_username=message_data.username,
            text=message_data.message_text,
            is_self=True,
            user_id=user.id,
            recipient_username=message_data.username
        )
        session.add(message)
        await session.commit()
    except Exception as e:
        if session.is_active:
            await session.rollback()
        raise e
