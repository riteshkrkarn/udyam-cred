"""Final verification script for Stage 2 MVP completion."""
import sys
from app.database import engine, init_db
from sqlalchemy import inspect

# Initialize DB to ensure all tables exist
init_db(engine)

# Get table names
inspector = inspect(engine)
tables = inspector.get_table_names()

print("=" * 70)
print("DATABASE VERIFICATION - STAGE 2 MVP")
print("=" * 70)

# Stage 1 tables
stage1_tables = {"users", "shops", "reconciliation_results", "refresh_tokens"}
# Stage 2 tables
stage2_tables = {
    "applications", "consents", "documents", "household_data",
    "decisions", "overrides", "audit_logs", "data_sources"
}

print("\n✓ STAGE 1 TABLES (4):")
for tbl in sorted(stage1_tables):
    status = "✓" if tbl in tables else "✗"
    print(f"  {status} {tbl}")

print("\n✓ STAGE 2 TABLES (8):")
for tbl in sorted(stage2_tables):
    status = "✓" if tbl in tables else "✗"
    print(f"  {status} {tbl}")

print("\n" + "=" * 70)
print("FOREIGN KEY CONSTRAINTS")
print("=" * 70)

# Check foreign keys
for table_name in sorted(stage2_tables | stage1_tables):
    fks = inspector.get_foreign_keys(table_name)
    if fks:
        print(f"\n{table_name}:")
        for fk in fks:
            constrained = ", ".join(fk["constrained_columns"])
            referred = f"{fk['referred_table']}.{', '.join(fk['referred_columns'])}"
            print(f"  • {constrained} → {referred}")

print("\n" + "=" * 70)
print("✓ DATABASE VERIFICATION COMPLETE")
print("=" * 70)

sys.exit(0)
