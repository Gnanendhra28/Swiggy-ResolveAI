import os
import pytest
from alembic.config import Config
from alembic import command


def test_alembic_migrations():
    """Test executing Alembic migrations upgrade and downgrade."""
    alembic_ini_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic.ini"
    )
    alembic_cfg = Config(alembic_ini_path)
    # Set to in-memory or test SQLite database
    test_db_url = "sqlite:///./test_migration.db"
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    try:
        # Run upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Run downgrade to base
        command.downgrade(alembic_cfg, "base")

        # Run upgrade to head again
        command.upgrade(alembic_cfg, "head")
    finally:
        if os.path.exists("./test_migration.db"):
            try:
                os.remove("./test_migration.db")
            except Exception:
                pass
