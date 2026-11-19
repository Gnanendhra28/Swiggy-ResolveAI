"""
Verifies that a fresh, empty PostgreSQL database/schema initializes from revision 001 to head cleanly.
"""
import sys
sys.path.insert(0, ".")
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command
from backend.app.core.config import settings

def test_fresh_migration():
    direct_url = settings.DATABASE_URL.replace("-pooler", "")
    engine = create_engine(direct_url)
    with engine.connect() as conn:
        print("[1] Creating isolated temporary PostgreSQL schema: 'test_migration_fresh'...")
        conn.execute(text("DROP SCHEMA IF EXISTS test_migration_fresh CASCADE;"))
        conn.execute(text("CREATE SCHEMA test_migration_fresh;"))
        conn.commit()

    print("[2] Configuring Alembic to target isolated clean schema via direct unpooled connection...")
    alembic_cfg = Config("backend/alembic.ini")
    
    fresh_url = direct_url
    if "?" in fresh_url:
        fresh_url += "&options=-csearch_path=test_migration_fresh"
    else:
        fresh_url += "?options=-csearch_path=test_migration_fresh"
        
    alembic_cfg.set_main_option("sqlalchemy.url", fresh_url)

    print("[3] Running alembic upgrade head from 001 to head...")
    command.upgrade(alembic_cfg, "head")
    print("SUCCESS: Full migration chain 001 -> 005 applied cleanly!")

    # Verify tables in fresh schema
    with engine.connect() as conn:
        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'test_migration_fresh'
            ORDER BY table_name;
        """)).fetchall()
        table_names = [t[0] for t in tables]
        print(f"[4] Created tables in fresh schema: {table_names}")
        assert len(table_names) == 12 # 11 tables + alembic_version
        
        current_rev = conn.execute(text("SELECT version_num FROM test_migration_fresh.alembic_version;")).scalar()
        print(f"[5] Final stamped revision: {current_rev}")
        assert current_rev == "005_phase_5_experiments_and_kpis"

        # Cleanup
        print("[6] Cleaning up temporary test schema...")
        conn.execute(text("DROP SCHEMA test_migration_fresh CASCADE;"))
        conn.commit()
        print("CLEANUP COMPLETE: Fresh PostgreSQL migration verified 100% end-to-end!")

if __name__ == "__main__":
    test_fresh_migration()
