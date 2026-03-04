"""
DB 마이그레이션 스크립트 — 기존 scm.db에 누락 컬럼/테이블 추가
실행: python fix_db.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'scm.db')

def add_column(c, table, col, col_type="TEXT"):
    try:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        print(f"  ✅ {table}.{col} 추가")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            pass
        else:
            print(f"  ⚠️  {table}.{col}: {e}")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ── invoice_verifications ──────────────
add_column(c, "invoice_verifications", "supplier_invoice_no", "TEXT")
add_column(c, "invoice_verifications", "variance_amount", "REAL DEFAULT 0")
add_column(c, "invoice_verifications", "match_result", "TEXT DEFAULT '검토중'")
add_column(c, "invoice_verifications", "status", "TEXT DEFAULT '검토중'")

# ── supplier_evaluations ──────────────
add_column(c, "supplier_evaluations", "evaluation_period", "TEXT")
add_column(c, "supplier_evaluations", "comment", "TEXT")
add_column(c, "supplier_evaluations", "grade", "TEXT")
add_column(c, "supplier_evaluations", "eval_number", "TEXT")

# ── purchase_tax_invoices ──────────────
add_column(c, "purchase_tax_invoices", "ti_number", "TEXT")
add_column(c, "purchase_tax_invoices", "supplier_id", "INTEGER")
add_column(c, "purchase_tax_invoices", "supplier_name", "TEXT")
add_column(c, "purchase_tax_invoices", "tax_invoice_no", "TEXT")
add_column(c, "purchase_tax_invoices", "payment_terms", "TEXT DEFAULT '30일'")
add_column(c, "purchase_tax_invoices", "payment_method", "TEXT DEFAULT '계좌이체'")

# ── payment_schedule ──────────────
add_column(c, "payment_schedule", "ti_number", "TEXT")
add_column(c, "payment_schedule", "supplier_name", "TEXT")

# ── materials ──────────────
add_column(c, "materials", "min_stock", "INTEGER DEFAULT 0")
add_column(c, "materials", "lead_time_days", "INTEGER DEFAULT 7")
add_column(c, "materials", "mat_status", "TEXT DEFAULT '활성'")

# ── purchase_orders ──────────────
add_column(c, "purchase_orders", "delivery_date", "TEXT")
add_column(c, "purchase_orders", "warehouse", "TEXT")

# ── goods_receipts ──────────────
add_column(c, "goods_receipts", "bin_code", "TEXT")
add_column(c, "goods_receipts", "lot_number", "TEXT")

# ── 신규 테이블 ──────────────
c.execute('''CREATE TABLE IF NOT EXISTS alternative_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER, alt_material_code TEXT, alt_material_name TEXT,
    conversion_factor REAL DEFAULT 1.0, priority INTEGER DEFAULT 1, note TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS return_to_vendor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rtv_number TEXT UNIQUE NOT NULL, gr_id INTEGER, po_id INTEGER, supplier_id INTEGER,
    item_name TEXT NOT NULL, return_qty INTEGER NOT NULL,
    reason TEXT, defect_type TEXT, return_type TEXT DEFAULT '반품',
    credit_note_amount REAL DEFAULT 0, status TEXT DEFAULT '반품요청',
    approved_by TEXT, note TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS moving_avg_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code TEXT NOT NULL, item_name TEXT NOT NULL,
    prev_qty INTEGER DEFAULT 0, prev_avg_price REAL DEFAULT 0,
    incoming_qty INTEGER NOT NULL, incoming_price REAL NOT NULL,
    new_qty INTEGER NOT NULL, new_avg_price REAL NOT NULL,
    reference TEXT, calculated_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS blanket_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blanket_number TEXT UNIQUE NOT NULL, supplier_id INTEGER,
    item_name TEXT NOT NULL, total_limit_amount REAL NOT NULL,
    used_amount REAL DEFAULT 0, remaining_amount REAL NOT NULL,
    currency TEXT DEFAULT 'KRW', unit_price REAL DEFAULT 0,
    start_date TEXT, end_date TEXT, status TEXT DEFAULT '유효', note TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS blanket_order_releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blanket_id INTEGER, po_id INTEGER,
    release_qty INTEGER NOT NULL, release_amount REAL NOT NULL,
    release_date TEXT, created_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS purchase_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_number TEXT UNIQUE NOT NULL, pr_id INTEGER,
    title TEXT NOT NULL, requester TEXT NOT NULL, department TEXT,
    item_name TEXT NOT NULL, quantity INTEGER NOT NULL,
    estimated_amount REAL DEFAULT 0, reason TEXT,
    contract_type TEXT DEFAULT '경쟁입찰', sole_source_reason TEXT,
    step1_approver TEXT, step1_status TEXT DEFAULT '대기', step1_comment TEXT, step1_at TEXT,
    step2_approver TEXT, step2_status TEXT DEFAULT '대기', step2_comment TEXT, step2_at TEXT,
    step3_approver TEXT, step3_status TEXT DEFAULT '대기', step3_comment TEXT, step3_at TEXT,
    final_status TEXT DEFAULT '검토중',
    created_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS po_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id INTEGER, po_number TEXT,
    changed_field TEXT, old_value TEXT, new_value TEXT,
    changed_by TEXT, change_reason TEXT,
    changed_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS po_receipt_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id INTEGER UNIQUE NOT NULL,
    ordered_qty INTEGER NOT NULL,
    received_qty INTEGER DEFAULT 0,
    remaining_qty INTEGER NOT NULL,
    last_gr_date TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
)''')
c.execute('''CREATE TABLE IF NOT EXISTS purchase_info_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pir_number TEXT, supplier_id INTEGER, material_id INTEGER,
    item_name TEXT, unit_price REAL, currency TEXT DEFAULT 'KRW',
    min_order_qty INTEGER DEFAULT 1, lead_time_days INTEGER DEFAULT 7,
    discount_rate REAL DEFAULT 0, price_unit INTEGER DEFAULT 1,
    valid_from TEXT, valid_to TEXT, memo TEXT, status TEXT DEFAULT '유효',
    created_at TEXT DEFAULT (datetime('now','localtime'))
)''')

conn.commit()
conn.close()
print("\n✅ DB 마이그레이션 완료!")
