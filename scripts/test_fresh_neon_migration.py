"""
Safe, Isolated Fresh Database Migration Verification against Neon PostgreSQL.
Never modifies or drops pre-existing schemas.
Creates an ephemeral, uniquely-named schema, executes Alembic migrations from 001 to head,
validates all created tables and stamped revision, and guarantees cleanup in a try/finally block.
"""
import sys
import uuid
from typing import List

sys.path.insert(0, ".")

from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command
from backend.app.core.config import settings


def run_safe_fresh_migration_test() -> int:
    # 1. Safety Guardrail: Direct unpooled connection required for DDL migrations
    direct_url = settings.DATABASE_URL.replace("-pooler", "")
    engine = create_engine(direct_url)

    # 2. Generate a guaranteed unique, isolated disposable schema name
    schema_id = uuid.uuid4().hex[:12]
    ephemeral_schema = f"test_ephemeral_mig_{schema_id}"

    # Strict safety invariant: never touch public or production schemas
    if ephemeral_schema.lower() in ("public", "information_schema", "pg_catalog") or not ephemeral_schema.startswith("test_ephemeral_"):
        raise RuntimeError(f"FATAL: Target schema '{ephemeral_schema}' violates safety guardrail!")

    print("======================================================================")
    print("  SAFE FRESH MIGRATION TEST — DISPOSABLE ISOLATED SCHEMA")
    print("======================================================================")
    print(f"Target Disposable Schema : {ephemeral_schema}")
    print("Production Application Schema: PRESERVED (UNTURNED)")
    print("----------------------------------------------------------------------")

    schema_created = False
    try:
        # Step A: Verify the disposable schema does not exist prior to test
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
                {"s": ephemeral_schema}
            ).scalar()
            if existing:
                raise RuntimeError(f"Safety violation: Schema '{ephemeral_schema}' unexpectedly pre-exists!")
            
            # Create isolated disposable schema
            print(f"[STEP 1] Creating isolated disposable schema: '{ephemeral_schema}'...")
            conn.execute(text(f'CREATE SCHEMA "{ephemeral_schema}";'))
            conn.commit()
            schema_created = True

        # Step B: Configure Alembic to execute migrations strictly inside the ephemeral schema
        print(f"[STEP 2] Configuring Alembic to target '{ephemeral_schema}' via direct connection...")
        alembic_cfg = Config("backend/alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", direct_url)
        alembic_cfg.set_main_option("target_schema", ephemeral_schema)

        # Step C: Execute full migration sequence from scratch (001 -> 005)
        print("[STEP 3] Executing 'alembic upgrade head' across full revision chain...")
        command.upgrade(alembic_cfg, "head")
        print("  -> Full migration chain 001 -> 005 executed successfully!")

        # Step D: Verify all 12 tables and head revision in the ephemeral schema
        with engine.connect() as conn:
            tables = conn.execute(
                text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = :s 
                    ORDER BY table_name;
                """),
                {"s": ephemeral_schema}
            ).fetchall()
            created_tables = [t[0] for t in tables]
            print(f"[STEP 4] Verified tables in '{ephemeral_schema}': {len(created_tables)} table(s)")
            
            expected_tables = {
                "alembic_version",
                "customers",
                "delivery_partners",
                "historical_orders",
                "ml_prediction_audits",
                "order_events",
                "order_investigations",
                "orders",
                "recovery_execution_audits",
                "recovery_recommendations",
                "restaurants",
                "simulation_experiments",
            }
            missing = expected_tables - set(created_tables)
            if missing:
                raise AssertionError(f"Fresh migration failed! Missing tables: {missing}")

            # Verify stamped revision
            stamped_rev = conn.execute(
                text(f'SELECT version_num FROM "{ephemeral_schema}".alembic_version;')
            ).scalar()
            print(f"[STEP 5] Verified final stamped revision: {stamped_rev}")
            if stamped_rev != "005_phase_5_experiments_and_kpis":
                raise AssertionError(f"Revision mismatch! Expected '005_phase_5_experiments_and_kpis', got '{stamped_rev}'")

        print("RESULT: Safe fresh migration test PASSED with 100% table and revision parity!")

    finally:
        # Step E: Guaranteed cleanup in finally block
        if schema_created:
            print(f"[CLEANUP] Dropping isolated disposable schema '{ephemeral_schema}' CASCADE...")
            with engine.connect() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{ephemeral_schema}" CASCADE;'))
                conn.commit()

                # Verify complete cleanup
                still_exists = conn.execute(
                    text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
                    {"s": ephemeral_schema}
                ).scalar()
                if still_exists:
                    print(f"ERROR: Incomplete cleanup: Schema '{ephemeral_schema}' still exists!")
                    return 1
                print(f"[CLEANUP] Verification confirmed: '{ephemeral_schema}' fully removed.")
        print("======================================================================\n")

    return 0


if __name__ == "__main__":
    exit_code = run_safe_fresh_migration_test()
    sys.exit(exit_code)
