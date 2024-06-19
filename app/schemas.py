from pydantic import BaseModel

class MessageCreate(BaseModel):
    message_text: str
    from_phone: str
    username: str
