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


def test_version_table_impl_supports_long_identifiers():
    """Regression test: verify version table allocates VARCHAR(64) for identifiers > 32 chars."""
    from alembic.ddl.impl import DefaultImpl
    from sqlalchemy.dialects import postgresql
    
    impl = DefaultImpl(postgresql.dialect(), None, False, False, None, {})
    vt = impl.version_table_impl(
        version_table="alembic_version",
        version_table_schema=None,
        version_table_pk=True,
    )
    col = vt.c.version_num
    assert col.type.length is not None
    assert col.type.length >= 64, f"version_num length {col.type.length} must be >= 64"


def test_migration_revisions_chain_length():
    """Verify that all migration revision names are valid and fit within the 64-char limit."""
    from alembic.script import ScriptDirectory
    alembic_ini_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic.ini"
    )
    alembic_cfg = Config(alembic_ini_path)
    script_dir = ScriptDirectory.from_config(alembic_cfg)
    
    revisions = [sc.revision for sc in script_dir.walk_revisions()]
    assert len(revisions) >= 5
    for rev in revisions:
        assert len(rev) <= 64, f"Revision ID '{rev}' exceeds 64 characters (length: {len(rev)})"
        # Confirm that at least one revision is longer than 32 characters to prove the fix is necessary
    long_revs = [r for r in revisions if len(r) > 32]
    assert len(long_revs) > 0, "Expected at least one revision > 32 chars (e.g. 004_phase_4_resilience_and_audits)"
