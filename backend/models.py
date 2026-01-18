from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    strava_athlete_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tokens = relationship("Token", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_token = Column(String, nullable=False)  # In production, encrypt this!
    refresh_token = Column(String, nullable=False) # In production, encrypt this!
    expires_at = Column(Integer, nullable=False)   # Unix timestamp
    scope = Column(String, nullable=True)

    user = relationship("User", back_populates="tokens")
