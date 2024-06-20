from sqlalchemy import Column, BigInteger, String, Text, Boolean, ForeignKey 
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True)
    status = Column(String)
    session_name = Column(String)
    messages = relationship("Message", back_populates="user")

class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(BigInteger, index=True)
    sender_id = Column(BigInteger)
    sender_username = Column(String)
    text = Column(Text)
    is_self = Column(Boolean)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    recipient_username = Column(String)
    user = relationship("User", back_populates="messages")
