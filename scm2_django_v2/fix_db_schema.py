"""
DB schema fixes for remaining 5 ERR items.
Run: python fix_db_schema.py
"""
import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from django.db import connection

def run_sql(sql, label):
    try:
        with connection.cursor() as cur:
            cur.execute(sql)
        print(f'  [OK] {label}')
    except Exception as e:
        print(f'  [ERR] {label}: {e}')

print('=== PP BillOfMaterial: add bom_code / product_name ===')
run_sql(
    "ALTER TABLE scm_pp_billofmaterial ADD COLUMN IF NOT EXISTS bom_code VARCHAR(50) DEFAULT ''",
    'add bom_code column'
)
run_sql(
    "ALTER TABLE scm_pp_billofmaterial ADD COLUMN IF NOT EXISTS product_name VARCHAR(200) DEFAULT ''",
    'add product_name column'
)
# Populate bom_code for existing rows so unique index can be created
run_sql(
    "UPDATE scm_pp_billofmaterial SET bom_code = 'BOM-LEGACY-' || id::text WHERE bom_code = ''",
    'populate legacy bom_codes'
)
run_sql(
    "ALTER TABLE scm_pp_billofmaterial ALTER COLUMN bom_code SET NOT NULL",
    'bom_code NOT NULL'
)
run_sql(
    "ALTER TABLE scm_pp_billofmaterial ALTER COLUMN product_name SET NOT NULL",
    'product_name NOT NULL'
)
# Unique index on bom_code (model has unique=True)
run_sql(
    "CREATE UNIQUE INDEX IF NOT EXISTS scm_pp_billofmaterial_bom_code_uniq ON scm_pp_billofmaterial(bom_code)",
    'bom_code unique index'
)

print('\n=== QM InspectionResult: add DEFAULT to DB-only NOT NULL columns ===')
for col, default in [
    ('reference_type',   "''"),
    ('reference_number', "''"),
    ('inspection_date',  'CURRENT_DATE'),
    ('status',           "''"),
    ('remarks',          "''"),
]:
    run_sql(
        f"ALTER TABLE scm_qm_inspectionresult ALTER COLUMN {col} SET DEFAULT {default}",
        f'inspectionresult.{col} DEFAULT {default}'
    )

print('\nDone.')
