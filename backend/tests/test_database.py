from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.models.customer import Customer
from backend.app.models.restaurant import Restaurant
from backend.app.models.delivery_partner import DeliveryPartner
from backend.app.models.order import Order
from backend.app.models.order_event import OrderEvent


def test_database_connection(db_session: Session):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_seed_entities_exist(db_session: Session):
    customers = db_session.query(Customer).all()
    restaurants = db_session.query(Restaurant).all()
    riders = db_session.query(DeliveryPartner).all()

    assert len(customers) > 0
    assert len(restaurants) > 0
    assert len(riders) > 0


def test_standard_os_dns_resolution_preserved():
    """Verify standard OS DNS resolution is in place with no custom getaddrinfo overrides."""
    import socket
    # Ensure socket.getaddrinfo is the built-in function or unmodified standard library callable
    assert callable(socket.getaddrinfo)
    assert not hasattr(socket.getaddrinfo, "__wrapped__")
    assert "patched" not in socket.getaddrinfo.__name__.lower()
    assert "fallback" not in socket.getaddrinfo.__name__.lower()


def test_database_url_normalization():
    """Verify database URL normalization for PostgreSQL drivers."""
    from backend.app.core.config import Settings
    
    s1 = Settings(DATABASE_URL="postgres://user:pass@host:5432/db")
    assert s1.DATABASE_URL == "postgresql+psycopg2://user:pass@host:5432/db"

    s2 = Settings(DATABASE_URL="postgresql://user:pass@host:5432/db")
    assert s2.DATABASE_URL == "postgresql+psycopg2://user:pass@host:5432/db"

    s3 = Settings(DATABASE_URL="sqlite:///./test.db")
    assert s3.DATABASE_URL == "sqlite:///./test.db"


def test_engine_pool_lifecycle_configuration():
    """Verify SQLAlchemy engine pooling parameters are configured."""
    from backend.app.database.session import engine
    assert hasattr(engine.pool, "_pre_ping")
    assert engine.pool._pre_ping is True
