import socket
import struct
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Resilient public DNS fallback for cloud PostgreSQL hosts (e.g. neon.tech)
_orig_getaddrinfo = socket.getaddrinfo

def _fallback_dns_lookup(hostname: str) -> list:
    try:
        packet = b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        for part in hostname.split("."):
            packet += struct.pack("B", len(part)) + part.encode()
        packet += b"\x00\x00\x01\x00\x01"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.5)
        sock.sendto(packet, ("8.8.8.8", 53))
        data, _ = sock.recvfrom(1024)
        sock.close()
        ips = []
        i = 0
        while i < len(data) - 4:
            if data[i:i+4] == b"\x00\x01\x00\x01":
                rdlen = struct.unpack(">H", data[i+8:i+10])[0]
                if rdlen == 4:
                    ips.append(socket.inet_ntoa(data[i+10:i+14]))
            i += 1
        return ips
    except Exception:
        return []

def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    except socket.gaierror:
        if isinstance(host, str) and "neon.tech" in host:
            ips = _fallback_dns_lookup(host)
            if ips:
                return _orig_getaddrinfo(ips[0], port, family, type, proto, flags)
        raise

socket.getaddrinfo = _patched_getaddrinfo

# Configure connection parameters based on engine type
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    # Production-grade connection pooling for PostgreSQL
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        db.rollback()
        logger.error(f"Database session error: {exc}")
        raise
    finally:
        db.close()
