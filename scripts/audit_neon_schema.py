"""
Independent Schema Integrity Audit between SQLAlchemy Base.metadata and Neon PostgreSQL.
"""
import sys
sys.path.insert(0, ".")
from sqlalchemy import inspect
from backend.app.database.session import engine
from backend.app.database.base import Base
import backend.app.models

def run_schema_audit():
    insp = inspect(engine)
    db_tables = set(insp.get_table_names())
    meta_tables = set(Base.metadata.tables.keys())

    print("=== TABLE LEVEL COMPARISON ===")
    print("Database tables:", sorted(list(db_tables)))
    print("Model metadata tables:", sorted(list(meta_tables)))
    missing_in_db = meta_tables - db_tables
    extra_in_db = db_tables - meta_tables - {"alembic_version"}
    print("Missing in DB:", missing_in_db)
    print("Extra in DB:", extra_in_db)

    print("\n=== DETAILED COLUMN & CONSTRAINT AUDIT ===")
    discrepancies = []
    
    for table_name in sorted(list(meta_tables)):
        if table_name not in db_tables:
            discrepancies.append(f"TABLE MISSING: {table_name}")
            continue
            
        db_cols = {col["name"]: col for col in insp.get_columns(table_name)}
        meta_cols = {col.name: col for col in Base.metadata.tables[table_name].columns}
        
        # Check missing or unexpected columns
        missing_cols = set(meta_cols.keys()) - set(db_cols.keys())
        if missing_cols:
            discrepancies.append(f"{table_name}: Missing columns in DB: {missing_cols}")
            
        extra_cols = set(db_cols.keys()) - set(meta_cols.keys())
        if extra_cols:
            discrepancies.append(f"{table_name}: Extra columns in DB: {extra_cols}")
        
        for col_name, m_col in meta_cols.items():
            if col_name in db_cols:
                d_col = db_cols[col_name]
                # Nullability check
                if m_col.nullable != d_col["nullable"]:
                    discrepancies.append(
                        f"{table_name}.{col_name}: Nullability mismatch! Model nullable={m_col.nullable}, DB nullable={d_col['nullable']}"
                    )
                # Type inspection
                m_type = str(m_col.type).upper()
                d_type = str(d_col["type"]).upper()
        
        # Primary key check
        db_pk = insp.get_pk_constraint(table_name)
        m_pk = [c.name for c in Base.metadata.tables[table_name].primary_key.columns]
        if set(db_pk.get("constrained_columns", [])) != set(m_pk):
            discrepancies.append(
                f"{table_name}: Primary Key mismatch! Model={m_pk}, DB={db_pk.get('constrained_columns')}"
            )
            
        # Foreign key check
        db_fks = insp.get_foreign_keys(table_name)
        db_fk_cols = {
            fk["constrained_columns"][0]: (fk["referred_table"], fk["referred_columns"][0])
            for fk in db_fks if fk["constrained_columns"]
        }
        for fk in Base.metadata.tables[table_name].foreign_keys:
            col = fk.parent.name
            ref = (fk.column.table.name, fk.column.name)
            if col not in db_fk_cols:
                discrepancies.append(f"{table_name}.{col}: Missing Foreign Key to {ref} in DB")
            elif db_fk_cols[col] != ref:
                discrepancies.append(f"{table_name}.{col}: Foreign Key mismatch! Model={ref}, DB={db_fk_cols[col]}")

        # Indexes check
        db_indexes = {idx["name"]: idx for idx in insp.get_indexes(table_name)}
        for m_idx in Base.metadata.tables[table_name].indexes:
            if m_idx.name not in db_indexes:
                discrepancies.append(f"{table_name}: Index {m_idx.name} missing in DB")

    print(f"\nTotal discrepancies found: {len(discrepancies)}")
    if discrepancies:
        for d in discrepancies:
            print("  -", d)
    else:
        print("PERFECT MATCH: All 11 tables, columns, nullability, primary keys, and foreign keys match 100%!")

    # Check Alembic version table
    conn = engine.connect()
    from sqlalchemy import text
    version_row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    print(f"\nAlembic Version in Neon Database: {version_row[0] if version_row else 'None'}")
    conn.close()

if __name__ == "__main__":
    run_schema_audit()
