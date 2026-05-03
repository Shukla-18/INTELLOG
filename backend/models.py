"""SQLAlchemy ORM Models"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Boolean
from backend.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    vm_name = Column(String(100), nullable=False, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    memory_used_mb = Column(Float)
    memory_total_mb = Column(Float)
    disk_percent = Column(Float)
    suspicious = Column(Boolean, default=False)
    severity = Column(String(20), default="LOW")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class NetworkData(Base):
    __tablename__ = "network"

    id = Column(Integer, primary_key=True, index=True)
    vm_name = Column(String(100), nullable=False, index=True)
    bytes_sent = Column(Float, nullable=False)
    bytes_recv = Column(Float, nullable=False)
    packets_sent = Column(Integer)
    packets_recv = Column(Integer)
    bytes_sent_rate = Column(Float, default=0)
    bytes_recv_rate = Column(Float, default=0)
    suspicious = Column(Boolean, default=False)
    severity = Column(String(20), default="LOW")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LogEntry(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    vm_name = Column(String(100), nullable=False, index=True)
    source = Column(String(200))
    content = Column(Text, nullable=False)
    log_hash = Column(String(64), unique=True, index=True)
    suspicious = Column(Boolean, default=False)
    severity = Column(String(20), default="LOW")
    tags = Column(Text, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    vm_name = Column(String(100), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    explanation = Column(Text)
    resolved = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
