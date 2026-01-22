# Initialize Fernet with a key derived from SECRET_KEY
# Note: Fernet keys must be 32 url-safe base64-encoded bytes.
import base64
import hashlib
from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import relationship

from .config import settings
from .database import Base

key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
fernet = Fernet(key)

class EncryptedString(TypeDecorator):
    """Stored as encrypted text, decrypted on load."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return fernet.decrypt(value.encode()).decode()
        except Exception:
            # Fallback for old plaintext tokens or decryption failure
            return value

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
    access_token = Column(EncryptedString, nullable=False)
    refresh_token = Column(EncryptedString, nullable=False)
    expires_at = Column(Integer, nullable=False)   # Unix timestamp
    scope = Column(String, nullable=True)

    user = relationship("User", back_populates="tokens")

class Segment(Base):
    __tablename__ = "segments"

    id = Column(BigInteger, primary_key=True, index=True)  # Strava Segment ID
    name = Column(String, index=True)
    distance = Column(Float)
    average_grade = Column(Float, nullable=True)
    city = Column(String, nullable=True)
    
    efforts = relationship("SegmentEffort", back_populates="segment", cascade="all, delete-orphan")

class SegmentEffort(Base):
    __tablename__ = "segment_efforts"

    id = Column(BigInteger, primary_key=True, index=True)  # Strava Effort ID
    segment_id = Column(BigInteger, ForeignKey("segments.id"), nullable=False)
    activity_id = Column(BigInteger, index=True, nullable=False) # Strava Activity ID
    
    elapsed_time = Column(Integer)
    moving_time = Column(Integer)
    start_date = Column(DateTime)
    
    kom_rank = Column(Integer, nullable=True)
    pr_rank = Column(Integer, nullable=True)

    segment = relationship("Segment", back_populates="efforts")

class LLMCache(Base):
    __tablename__ = "llm_cache"

    id = Column(Integer, primary_key=True, index=True)
    prompt_hash = Column(String, unique=True, index=True, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
