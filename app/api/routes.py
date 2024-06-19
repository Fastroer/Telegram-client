from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.telegram_service import login_qr, check_login_status, wait_for_authorization, get_messages, send_message
from app.db.database import get_session
from app.schemas import MessageCreate
from typing import Dict, Any

router = APIRouter()

@router.post("/login", response_model=Dict[str, Any])
async def login(phone: str, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)) -> Dict[str, str]:
    """
    Initiate QR code login for a given phone number.

    Args:
        phone (str): The phone number of the user.
        background_tasks (BackgroundTasks): FastAPI background tasks.
        session (AsyncSession): The database session.

    Returns:
        Dict[str, str]: URL for the generated QR code.
    
    Raises:
        HTTPException: If unable to generate QR code.
    """
    url = await login_qr(phone, session)
    if url:
        background_tasks.add_task(wait_for_authorization, phone, session)
        return {"qr_url": url}
    raise HTTPException(status_code=500, detail="Unable to generate QR code")

@router.get("/check/login", response_model=Dict[str, str])
async def check_login(phone: str, session: AsyncSession = Depends(get_session)) -> Dict[str, str]:
    """
    Check the login status of a user by phone number.

    Args:
        phone (str): The phone number of the user.
        session (AsyncSession): The database session.

    Returns:
        Dict[str, str]: The login status of the user.
    
    Raises:
        HTTPException: If the user is not found.
    """
    status = await check_login_status(phone, session)
    return {"status": status}

@router.get("/messages", response_model=Dict[str, Any])
async def fetch_messages(phone: str, uname: str, session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    """
    Retrieve the last 50 messages for a given user and username.

    Args:
        phone (str): The phone number of the user.
        uname (str): The username to fetch messages for.
        session (AsyncSession): The database session.

    Returns:
        Dict[str, Any]: A list of messages.
    
    Raises:
        HTTPException: If the user is not found.
    """
    messages = await get_messages(phone, uname, session)
    return {"messages": messages}

@router.post("/messages", response_model=Dict[str, str])
async def create_message(message: MessageCreate, session: AsyncSession = Depends(get_session)) -> Dict[str, str]:
    """
    Send a message and save it to the database.

    Args:
        message (MessageCreate): The message data.
        session (AsyncSession): The database session.

    Returns:
        Dict[str, str]: The status of the message sending operation.
    
    Raises:
        HTTPException: If the user is not found.
    """
    await send_message(message, session)
    return {"status": "Message sent"}
