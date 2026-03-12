"""
SCM 통합관리 시스템 — MySQL DB 연결 및 초기화  (utils/db.py)
pip install pymysql bcrypt
"""
import os, re
import pymysql, pymysql.cursors
from datetime import datetime

# ── 접속 설정 ─────────────────────────────────────────
DB_CONFIG = dict(
    host     = os.environ.get("SCM_DB_HOST", "localhost"),
    port     = int(os.environ.get("SCM_DB_PORT", 3306)),
    user     = os.environ.get("SCM_DB_USER", "scm_user"),
    password = os.environ.get("SCM_DB_PASS", "scm1234"),
    database = os.environ.get("SCM_DB_NAME", "scm_db"),
    charset  = "utf8mb4",
    cursorclass = pymysql.cursors.DictCursor,
    autocommit  = False,
)

# ── SQLite → MySQL 완전 변환 ──────────────────────────
def _fix_sql(sql: str) -> str:
    sql = re.sub(r"date\('now',\s*'-(\d+)\s*days?'\)",  lambda m: f"DATE_SUB(NOW(), INTERVAL {m.group(1)} DAY)", sql, flags=re.I)
    sql = re.sub(r"date\('now',\s*'\+(\d+)\s*days?'\)", lambda m: f"DATE_ADD(NOW(), INTERVAL {m.group(1)} DAY)", sql, flags=re.I)
    sql = re.sub(r"date\('now',\s*(?:\?|%s)\)", "DATE_ADD(CURDATE(), INTERVAL ? DAY)", sql, flags=re.I)
    sql = re.sub(r"date\('now'\)",     "CURDATE()", sql, flags=re.I)
    sql = re.sub(r"datetime\('now'\)", "NOW()",     sql, flags=re.I)
    sql = re.sub(r"\bdate\(([a-zA-Z_]\w*(?:\.\w+)?)\)", lambda m: f"DATE({m.group(1)})", sql, flags=re.I)
    sql = re.sub(r"\bsubstr\s*\(",     "SUBSTRING(", sql, flags=re.I)
    sql = re.sub(r"\bINSERT\s+OR\s+IGNORE\b", "INSERT IGNORE", sql, flags=re.I)
    sql = re.sub(r"\bINSERT\s+OR\s+REPLACE\b","REPLACE",       sql, flags=re.I)
    sql = re.sub(r"!=\s*''", "IS NOT NULL AND 1=1", sql)
    sql = re.sub(r"<>\s*''", "IS NOT NULL AND 1=1", sql)
    sql = re.sub(r"(?<![!<>])=\s*''",  "IS NULL", sql)
    sql = re.sub(r"ON\s+CONFLICT\s*\([^)]*\)\s*DO\s+UPDATE\s+SET\s+(.+?)(?=\s*(?:;|$))",
                 lambda m: "ON DUPLICATE KEY UPDATE " + re.sub(r"excluded\.(\w+)", r"VALUES(\1)", m.group(1)),
                 sql, flags=re.I|re.S)
    sql = re.sub(r"\bMAX\s*\(\s*0\s*,", "GREATEST(0,", sql, flags=re.I)
    sql = re.sub(r"julianday\(([^)]+)\)\s*-\s*julianday\(([^)]+)\)",
                 lambda m: f"DATEDIFF({m.group(1).strip()},{m.group(2).strip()})", sql, flags=re.I)
    sql = re.sub(r"\bCAST\s*\((.+?)\s+AS\s+INTEGER\)", lambda m: f"CAST({m.group(1)} AS SIGNED)", sql, flags=re.I|re.S)
    return sql

# ── 래퍼 클래스 ───────────────────────────────────────
class _Row:
    def __init__(self, d): self._d = d; self._v = list(d.values())
    def __getitem__(self, k): return self._v[k] if isinstance(k,int) else self._d[k]
    def __iter__(self): return iter(self._v)
    def __len__(self): return len(self._v)
    def __contains__(self, k): return k in self._d
    def get(self, k, default=None): return self._d.get(k, default)
    def keys(self): return self._d.keys()
    def values(self): return self._d.values()
    def items(self): return self._d.items()
    def __repr__(self): return repr(self._d)

class _Cur:
    def __init__(self, c): self._c=c; self.lastrowid=c.lastrowid; self.rowcount=c.rowcount; self.description=c.description
    def fetchone(self):
        r=self._c.fetchone(); return _Row(r) if r else None
    def fetchall(self): return [_Row(r) for r in self._c.fetchall()]
    def __iter__(self):
        for r in self._c: yield _Row(r)

class _PCur:   # pandas-compatible cursor
    def __init__(self, c): self._c=c
    def execute(self, sql, args=None):
        sql=_fix_sql(sql.replace("?","%s") if args else sql)
        return self._c.execute(sql, args or ())
    def fetchone(self):
        r=self._c.fetchone(); return _Row(r) if r else None
    def fetchall(self): return [_Row(r) for r in self._c.fetchall()]
    def __iter__(self):
        for r in self._c: yield _Row(r)
    def __getattr__(self, n): return getattr(self._c, n)

class _Conn:
    def __init__(self, conn): self._conn=conn
    def execute(self, sql, args=None):
        sql=_fix_sql(sql.replace("?","%s") if args else sql)
        c=self._conn.cursor(); c.execute(sql, args or ()); return _Cur(c)
    def commit(self):   self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self):
        try: self._conn.close()
        except: pass
    def cursor(self): return _PCur(self._conn.cursor())
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def __getattr__(self, n): return getattr(self._conn, n)

def get_db() -> _Conn:
    return _Conn(pymysql.connect(**DB_CONFIG))

def gen_number(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ── 하위 호환 stub ────────────────────────────────────
def init_mm_extended_db(): pass
def init_mm_extra_db():    pass
def init_trade_db():       pass

# ════════════════════════════════════════════════════
#  init_db  — 모든 테이블 한 번에 생성
# ════════════════════════════════════════════════════
def init_db():
    conn = get_db()
    c = conn.cursor()

    tbls = [

# ── 인증 ─────────────────────────────────────────────
("""users""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(200) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password VARCHAR(256) NOT NULL,
    department VARCHAR(100),
    is_admin TINYINT(1) DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""user_permissions""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    page_key VARCHAR(100) NOT NULL,
    can_read TINYINT(1) DEFAULT 1,
    can_write TINYINT(1) DEFAULT 0,
    granted_by INT,
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_up (user_id, page_key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"""),

("""allowed_domains""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(200) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""api_settings""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_name VARCHAR(100) UNIQUE NOT NULL,
    key_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"""),

# ── MM 자재관리 ──────────────────────────────────────
("""suppliers""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    contact VARCHAR(100), email VARCHAR(200), phone VARCHAR(50), address TEXT,
    payment_terms VARCHAR(100), return_policy TEXT,
    status VARCHAR(20) DEFAULT '활성',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""materials""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    material_code VARCHAR(100) UNIQUE NOT NULL,
    material_name VARCHAR(200) NOT NULL,
    material_type VARCHAR(50) DEFAULT '원자재',
    unit VARCHAR(20) DEFAULT 'EA',
    category VARCHAR(100), storage_condition VARCHAR(100),
    standard_price DECIMAL(18,2) DEFAULT 0,
    min_stock INT DEFAULT 0, max_stock INT DEFAULT 0,
    lead_time_days INT DEFAULT 7,
    reorder_point DECIMAL(18,2) DEFAULT 0,
    reorder_qty DECIMAL(18,2) DEFAULT 0,
    auto_order TINYINT(1) DEFAULT 0,
    mat_status VARCHAR(20) DEFAULT '활성',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""purchase_requests""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    pr_number VARCHAR(100) UNIQUE NOT NULL,
    requester VARCHAR(100), department VARCHAR(100),
    material_id INT, material_name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL,
    required_date DATE,
    reason TEXT, note TEXT,
    status VARCHAR(20) DEFAULT '승인대기',
    approved_by VARCHAR(100), approved_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""purchase_orders""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    po_number VARCHAR(100) UNIQUE NOT NULL,
    pr_id INT, supplier_id INT, material_id INT,
    name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KRW',
    delivery_date DATE, warehouse VARCHAR(100),
    status VARCHAR(20) DEFAULT '발주완료',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""goods_receipts""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    gr_number VARCHAR(100) UNIQUE NOT NULL,
    po_id INT, po_number VARCHAR(100),
    name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    ordered_qty INT NOT NULL, received_qty INT NOT NULL, rejected_qty INT DEFAULT 0,
    warehouse VARCHAR(100), bin_code VARCHAR(100), lot_number VARCHAR(100),
    receiver VARCHAR(100), note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""goods_receipt""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    gr_number VARCHAR(100) UNIQUE NOT NULL,
    po_id INT, item_name VARCHAR(200) NOT NULL,
    received_qty INT NOT NULL, warehouse VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""invoice_verifications""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    iv_number VARCHAR(100) UNIQUE NOT NULL,
    po_id INT, po_number VARCHAR(100), gr_id INT,
    name VARCHAR(200), supplier VARCHAR(200), supplier_invoice_no VARCHAR(100),
    item_name VARCHAR(200),
    po_amount DECIMAL(18,2) DEFAULT 0,
    gr_amount DECIMAL(18,2) DEFAULT 0,
    invoice_amount DECIMAL(18,2) DEFAULT 0,
    tax_amount DECIMAL(18,2) DEFAULT 0,
    variance_amount DECIMAL(18,2) DEFAULT 0,
    match_result VARCHAR(20) DEFAULT '검토중',
    status VARCHAR(20) DEFAULT '검토중',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""supplier_evaluations""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    eval_number VARCHAR(100),
    supplier_id INT, name VARCHAR(200),
    evaluation_period VARCHAR(50),
    delivery_score DECIMAL(5,2) DEFAULT 0,
    quality_score DECIMAL(5,2) DEFAULT 0,
    price_score DECIMAL(5,2) DEFAULT 0,
    service_score DECIMAL(5,2) DEFAULT 0,
    total_score DECIMAL(5,2) DEFAULT 0,
    grade VARCHAR(10), evaluator VARCHAR(100), comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""moving_avg_price""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_code VARCHAR(100) NOT NULL, item_name VARCHAR(200) NOT NULL,
    prev_qty INT DEFAULT 0, prev_avg_price DECIMAL(18,2) DEFAULT 0,
    incoming_qty INT NOT NULL, incoming_price DECIMAL(18,2) NOT NULL,
    new_qty INT NOT NULL, new_avg_price DECIMAL(18,2) NOT NULL,
    reference VARCHAR(200),
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""purchase_info_records""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    pir_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id INT NOT NULL, material_id INT,
    name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    unit VARCHAR(20) DEFAULT 'EA',
    unit_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    agreed_price DECIMAL(18,2) NOT NULL DEFAULT 0,
    discount_rate DECIMAL(5,2) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'KRW',
    min_order_qty INT DEFAULT 1,
    lead_time_days INT DEFAULT 0,
    price_unit INT DEFAULT 1,
    valid_from DATE, valid_to DATE,
    status VARCHAR(20) DEFAULT '유효',
    memo TEXT, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""alternative_materials""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    material_id INT, material_code VARCHAR(100), material_name VARCHAR(200),
    alt_material_id INT, alt_material_code VARCHAR(100), alt_material_name VARCHAR(200),
    conversion_factor DECIMAL(10,4) DEFAULT 1.0,
    priority INT DEFAULT 1, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""return_to_vendor""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    rtv_number VARCHAR(100) UNIQUE NOT NULL,
    gr_id INT, po_id INT, supplier_id INT,
    name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    return_qty INT NOT NULL, reason TEXT, defect_type VARCHAR(100),
    return_type VARCHAR(50) DEFAULT '반품',
    credit_note_amount DECIMAL(18,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT '반품요청',
    approved_by VARCHAR(100), note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""blanket_orders""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    blanket_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id INT, name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    total_limit_amount DECIMAL(18,2) NOT NULL,
    used_amount DECIMAL(18,2) DEFAULT 0,
    remaining_amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KRW',
    unit_price DECIMAL(18,2) DEFAULT 0,
    start_date DATE, end_date DATE,
    status VARCHAR(20) DEFAULT '유효',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""blanket_order_releases""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    blanket_id INT, po_id INT,
    release_qty INT NOT NULL,
    release_amount DECIMAL(18,2) NOT NULL,
    release_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""purchase_approvals""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    approval_number VARCHAR(100) UNIQUE NOT NULL,
    pr_id INT, title VARCHAR(200) NOT NULL,
    requester VARCHAR(100) NOT NULL, department VARCHAR(100),
    item_name VARCHAR(200) NOT NULL, quantity INT NOT NULL,
    estimated_amount DECIMAL(18,2) DEFAULT 0,
    reason TEXT, contract_type VARCHAR(50) DEFAULT '경쟁입찰',
    sole_source_reason TEXT,
    step1_approver VARCHAR(100), step1_status VARCHAR(20) DEFAULT '대기',
    step1_comment TEXT, step1_at DATETIME,
    step2_approver VARCHAR(100), step2_status VARCHAR(20) DEFAULT '대기',
    step2_comment TEXT, step2_at DATETIME,
    step3_approver VARCHAR(100), step3_status VARCHAR(20) DEFAULT '대기',
    step3_comment TEXT, step3_at DATETIME,
    final_status VARCHAR(20) DEFAULT '검토중',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""purchase_tax_invoices""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    ti_number VARCHAR(100),
    iv_id INT, po_id INT, supplier_id INT,
    supplier VARCHAR(200), supplier_name VARCHAR(200),
    tax_invoice_no VARCHAR(100),
    supply_amount DECIMAL(18,2) DEFAULT 0,
    tax_amount DECIMAL(18,2) DEFAULT 0,
    total_amount DECIMAL(18,2) DEFAULT 0,
    issue_date DATE, due_date DATE,
    payment_terms VARCHAR(50) DEFAULT '30일',
    payment_method VARCHAR(50) DEFAULT '계좌이체',
    payment_status VARCHAR(20) DEFAULT '미지급',
    paid_at DATETIME, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""payment_schedule""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_number VARCHAR(100),
    tax_inv_id INT, ti_number VARCHAR(100),
    supplier VARCHAR(200), supplier_name VARCHAR(200),
    payment_amount DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KRW',
    due_date DATE NOT NULL,
    payment_method VARCHAR(50) DEFAULT '계좌이체',
    status VARCHAR(20) DEFAULT '미지급',
    paid_at DATETIME, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""po_change_log""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    po_id INT NOT NULL, po_number VARCHAR(100) NOT NULL,
    version INT DEFAULT 1, changed_field VARCHAR(100) NOT NULL,
    old_value TEXT, new_value TEXT,
    changed_by VARCHAR(100), change_reason TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""po_receipt_summary""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    po_id INT UNIQUE NOT NULL,
    ordered_qty INT NOT NULL, received_qty INT DEFAULT 0, remaining_qty INT NOT NULL,
    last_gr_date DATE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"""),

("""supplier_contracts""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    contract_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id INT, name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    contract_qty INT NOT NULL, unit_price DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KRW',
    start_date DATE, end_date DATE,
    status VARCHAR(20) DEFAULT '유효',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""quotations""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    quote_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id INT, material_id INT, name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL, unit_price DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KRW',
    valid_until DATE,
    status VARCHAR(20) DEFAULT '검토중',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""vmi_agreements""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    vmi_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_id INT, supplier_name VARCHAR(200),
    material_name VARCHAR(200) NOT NULL,
    min_qty INT DEFAULT 0, max_qty INT DEFAULT 0,
    replenish_trigger INT DEFAULT 0,
    review_cycle VARCHAR(50) DEFAULT '주간',
    status VARCHAR(20) DEFAULT '활성',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""vmi_replenishments""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    vmi_id INT, supplier_name VARCHAR(200),
    material_name VARCHAR(200) NOT NULL,
    current_stock INT DEFAULT 0, replenish_qty INT NOT NULL,
    status VARCHAR(20) DEFAULT '발주필요',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

# ── SD 판매출하 ──────────────────────────────────────
("""customers""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_code VARCHAR(100) UNIQUE NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    contact VARCHAR(100), email VARCHAR(200), phone VARCHAR(50), address TEXT,
    customer_group VARCHAR(50) DEFAULT '일반',
    credit_limit DECIMAL(18,2) DEFAULT 0,
    credit_used DECIMAL(18,2) DEFAULT 0,
    credit_status VARCHAR(20) DEFAULT '정상',
    tax_number VARCHAR(100), region VARCHAR(100),
    payment_terms VARCHAR(100),
    status VARCHAR(20) DEFAULT '활성',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""sales_orders""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(100) UNIQUE NOT NULL,
    customer_id INT, sd_quote_id INT, customer_name VARCHAR(200),
    platform VARCHAR(100),
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL, unit_price DECIMAL(18,2) NOT NULL,
    discount_rate DECIMAL(5,2) DEFAULT 0,
    requested_delivery DATE, confirmed_delivery DATE,
    confirmed_delivery_date DATE, actual_delivery_date DATE,
    shipped_qty INT DEFAULT 0,
    sales_rep VARCHAR(100), plan_number VARCHAR(100),
    planned_qty INT DEFAULT 0, monthly_target DECIMAL(18,2) DEFAULT 0,
    start_date DATE, end_date DATE,
    atp_checked TINYINT(1) DEFAULT 0, credit_checked TINYINT(1) DEFAULT 0,
    status VARCHAR(20) DEFAULT '주문접수',
    tracking_number VARCHAR(200),
    ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""deliveries""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    delivery_number VARCHAR(100) UNIQUE NOT NULL,
    order_id INT, order_number VARCHAR(100), customer_name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    delivery_qty INT NOT NULL, quantity INT DEFAULT 0,
    pick_qty INT DEFAULT 0, pack_qty INT DEFAULT 0,
    delivery_date DATE, actual_delivery DATE,
    address VARCHAR(300), partial_seq INT DEFAULT 1,
    carrier VARCHAR(100), tracking_number VARCHAR(200),
    status VARCHAR(20) DEFAULT '출하준비',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""returns""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    return_number VARCHAR(100) UNIQUE NOT NULL,
    order_id INT, order_number VARCHAR(100),
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL, reason TEXT,
    refund_amount DECIMAL(18,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT '반품접수',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""sd_quotations""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    sd_quote_number VARCHAR(100) UNIQUE NOT NULL,
    customer_id INT, customer_name VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL, unit_price DECIMAL(18,2) NOT NULL,
    discount_rate DECIMAL(5,2) DEFAULT 0,
    final_price DECIMAL(18,2) NOT NULL,
    valid_until DATE,
    status VARCHAR(20) DEFAULT '검토중',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""price_conditions""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT, item_name VARCHAR(200) NOT NULL,
    price_type VARCHAR(50) DEFAULT '고정가',
    unit_price DECIMAL(18,2) NOT NULL,
    discount_rate DECIMAL(5,2) DEFAULT 0,
    valid_from DATE, valid_to DATE,
    currency VARCHAR(10) DEFAULT 'KRW',
    min_qty INT DEFAULT 1, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""sales_tax_invoices""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    sti_number VARCHAR(100) UNIQUE NOT NULL,
    order_id INT, customer_name VARCHAR(200),
    tax_invoice_no VARCHAR(100),
    supply_amount DECIMAL(18,2) DEFAULT 0,
    tax_amount DECIMAL(18,2) DEFAULT 0,
    total_amount DECIMAL(18,2) DEFAULT 0,
    issue_date DATE, due_date DATE,
    payment_terms VARCHAR(50) DEFAULT '30일',
    payment_method VARCHAR(50) DEFAULT '계좌이체',
    payment_status VARCHAR(20) DEFAULT '미수금',
    paid_at DATETIME,
    status VARCHAR(20) DEFAULT '미수금',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""ar_receipts""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    receipt_number VARCHAR(100) UNIQUE NOT NULL,
    sti_id INT, customer_id INT, customer_name VARCHAR(200),
    amount DECIMAL(18,2) NOT NULL,
    receipt_amount DECIMAL(18,2) DEFAULT 0,
    receipt_method VARCHAR(50) DEFAULT '계좌이체',
    payment_method VARCHAR(50) DEFAULT '계좌이체',
    receipt_date DATE, bank_ref VARCHAR(200), note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""invoices""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    order_id INT, customer_name VARCHAR(200),
    amount DECIMAL(18,2) NOT NULL,
    tax_amount DECIMAL(18,2) NOT NULL,
    issue_date DATE, due_date DATE,
    paid TINYINT(1) DEFAULT 0, paid_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""sales_reps""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    rep_code VARCHAR(100) UNIQUE NOT NULL,
    rep_name VARCHAR(200) NOT NULL,
    region VARCHAR(100), team VARCHAR(100),
    phone VARCHAR(50), email VARCHAR(200),
    monthly_target DECIMAL(18,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT '활성',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""sales_targets""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL, month INT NOT NULL,
    item_name VARCHAR(200), channel VARCHAR(100),
    target_qty INT DEFAULT 0, target_amount DECIMAL(18,2) DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""prepayments""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    prepay_number VARCHAR(100) UNIQUE NOT NULL,
    order_id INT, customer_name VARCHAR(200),
    prepay_amount DECIMAL(18,2) DEFAULT 0,
    applied_amount DECIMAL(18,2) DEFAULT 0,
    received_date DATE, bank_ref VARCHAR(200),
    status VARCHAR(20) DEFAULT '미적용',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""packing_lists""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    pl_number VARCHAR(100) UNIQUE NOT NULL,
    delivery_id INT, delivery_number VARCHAR(100),
    item_name VARCHAR(200) NOT NULL,
    total_boxes INT DEFAULT 0, qty_per_box INT DEFAULT 0,
    box_number VARCHAR(100),
    gross_weight DECIMAL(10,2) DEFAULT 0,
    net_weight DECIMAL(10,2) DEFAULT 0,
    dimensions VARCHAR(200), marks TEXT, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""as_requests""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    as_number VARCHAR(100) UNIQUE NOT NULL,
    order_id INT, customer_name VARCHAR(200), delivery_number VARCHAR(100),
    item_name VARCHAR(200) NOT NULL,
    as_type VARCHAR(50) DEFAULT '수리',
    symptom TEXT, action_taken TEXT,
    priority VARCHAR(20) DEFAULT '보통',
    assigned_to VARCHAR(100),
    received_date DATE, completed_date DATE,
    qm_claim_linked INT DEFAULT 0,
    status VARCHAR(20) DEFAULT '접수',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

# ── PP 생산계획 ──────────────────────────────────────
("""production_plans""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_number VARCHAR(100) UNIQUE NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    planned_qty INT NOT NULL, actual_qty INT DEFAULT 0, defect_qty INT DEFAULT 0,
    completion_rate DECIMAL(5,2) DEFAULT 0,
    start_date DATE, end_date DATE,
    work_center VARCHAR(100), worker VARCHAR(100),
    status VARCHAR(20) DEFAULT '계획',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""bom""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    component_name VARCHAR(200) NOT NULL,
    component_code VARCHAR(100),
    quantity DECIMAL(18,4) NOT NULL,
    unit VARCHAR(20) DEFAULT 'EA',
    bom_level INT DEFAULT 1,
    valid_from DATE, valid_to DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""work_orders""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    wo_number VARCHAR(100) UNIQUE NOT NULL,
    plan_id INT, product_name VARCHAR(200) NOT NULL,
    planned_qty INT NOT NULL, actual_qty INT DEFAULT 0, defect_qty INT DEFAULT 0,
    work_center VARCHAR(100), worker VARCHAR(100), machine VARCHAR(100),
    start_date DATE, end_date DATE,
    actual_start DATE, actual_end DATE,
    started_at DATETIME, finished_at DATETIME,
    status VARCHAR(20) DEFAULT '대기',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""routings""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    operation_seq INT NOT NULL,
    operation_name VARCHAR(200) NOT NULL,
    work_center VARCHAR(100),
    standard_time DECIMAL(10,2) DEFAULT 0,
    machine VARCHAR(100), note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""work_centers""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    wc_code VARCHAR(100) UNIQUE NOT NULL,
    wc_name VARCHAR(200) NOT NULL,
    capacity_per_day DECIMAL(10,2) DEFAULT 8,
    machine_count INT DEFAULT 1,
    status VARCHAR(20) DEFAULT '가동',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""mrp_requests""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    mrp_number VARCHAR(100) UNIQUE NOT NULL,
    material_name VARCHAR(200) NOT NULL,
    required_qty INT NOT NULL, required_date DATE,
    source VARCHAR(50) DEFAULT 'MRP자동',
    status VARCHAR(20) DEFAULT '요청',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""production_results""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    wo_id INT, product_name VARCHAR(200) NOT NULL,
    planned_qty INT NOT NULL, actual_qty INT DEFAULT 0, defect_qty INT DEFAULT 0,
    work_center VARCHAR(100), worker VARCHAR(100),
    started_at DATETIME, finished_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""sop_plans""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL, month INT NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    sales_forecast INT DEFAULT 0, production_plan INT DEFAULT 0,
    opening_stock INT DEFAULT 0, closing_stock INT DEFAULT 0,
    inventory_target INT DEFAULT 0, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""subcon_orders""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    sc_number VARCHAR(100) UNIQUE NOT NULL,
    supplier VARCHAR(200) NOT NULL, product_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL, unit_cost DECIMAL(18,2) DEFAULT 0,
    send_date DATE, due_date DATE, receive_date DATE,
    receive_qty INT DEFAULT 0, defect_qty INT DEFAULT 0,
    status VARCHAR(20) DEFAULT '외주중',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

# ── QM 품질관리 ──────────────────────────────────────
("""quality_inspections""", """
    id VARCHAR(100),
    inspection_number VARCHAR(100) UNIQUE NOT NULL,
    inspection_type VARCHAR(50) DEFAULT '수입검사',
    item_name VARCHAR(200) NOT NULL,
    lot_number VARCHAR(100), lot_size INT DEFAULT 0,
    sample_qty INT NOT NULL, pass_qty INT DEFAULT 0, fail_qty INT DEFAULT 0,
    inspector VARCHAR(100),
    result VARCHAR(20) DEFAULT '합격',
    note TEXT, supplier_name VARCHAR(200), po_number VARCHAR(100),
    inspected_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""nonconformance""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    nc_number VARCHAR(100) UNIQUE NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    defect_type VARCHAR(100), quantity INT NOT NULL,
    severity VARCHAR(20) DEFAULT '경미',
    root_cause TEXT, corrective_action TEXT, preventive_action TEXT,
    status VARCHAR(20) DEFAULT '조사중',
    supplier_name VARCHAR(200), po_number VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""inspection_plans""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(200) NOT NULL,
    inspection_type VARCHAR(50) DEFAULT '수입검사',
    aql_level VARCHAR(50), sample_method VARCHAR(100),
    min_sample INT DEFAULT 1, spec_items TEXT, pass_criteria TEXT,
    valid_from DATE, valid_to DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""capa_actions""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    nc_id INT, nc_number VARCHAR(100),
    capa_number VARCHAR(100) UNIQUE NOT NULL,
    action_type VARCHAR(50) DEFAULT '시정조치',
    item_name VARCHAR(200), description TEXT, responsible VARCHAR(100),
    due_date DATE, effectiveness TEXT,
    status VARCHAR(20) DEFAULT '진행중',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""customer_complaints""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_number VARCHAR(100) UNIQUE NOT NULL,
    customer_name VARCHAR(200), item_name VARCHAR(200) NOT NULL,
    complaint_type VARCHAR(100), description TEXT,
    severity VARCHAR(20) DEFAULT '보통',
    quantity INT DEFAULT 0, received_date DATE, due_date DATE,
    root_cause TEXT, countermeasure TEXT,
    status VARCHAR(20) DEFAULT '접수',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""measuring_instruments""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    instrument_code VARCHAR(100) UNIQUE NOT NULL,
    instrument_name VARCHAR(200) NOT NULL,
    model VARCHAR(100), serial_number VARCHAR(100), location VARCHAR(100),
    calibration_cycle INT DEFAULT 365, calib_interval INT DEFAULT 365,
    last_calibration DATE, last_calib_date DATE,
    next_calibration DATE, next_calib_date DATE,
    status VARCHAR(20) DEFAULT '정상',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""inspection_results""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspection_number VARCHAR(100), item_name VARCHAR(200) NOT NULL,
    spec_item VARCHAR(200), spec_value VARCHAR(100), actual_value VARCHAR(100),
    result VARCHAR(20) DEFAULT '합격',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""d8_reports""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    d8_number VARCHAR(100) UNIQUE NOT NULL,
    nc_id INT, title VARCHAR(200) NOT NULL, owner VARCHAR(100),
    d1_team TEXT, d2_problem TEXT, d3_containment TEXT, d4_root_cause TEXT,
    d5_corrective TEXT, d6_implementation TEXT, d7_prevention TEXT, d8_closure TEXT,
    due_date DATE,
    status VARCHAR(20) DEFAULT '진행중',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""supplier_audits""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    audit_number VARCHAR(100) UNIQUE NOT NULL,
    supplier_name VARCHAR(200) NOT NULL,
    audit_type VARCHAR(50) DEFAULT '정기감사',
    scope TEXT, planned_date DATE, actual_date DATE,
    lead_auditor VARCHAR(100), team_members TEXT, checklist TEXT,
    status VARCHAR(20) DEFAULT '계획',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""audit_findings""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    audit_id INT, finding_type VARCHAR(50) DEFAULT '부적합',
    category VARCHAR(100), requirement TEXT, description TEXT, evidence TEXT,
    severity VARCHAR(20) DEFAULT '경미', corrective_action TEXT, due_date DATE,
    status VARCHAR(20) DEFAULT '미조치',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

# ── WM 창고관리 ──────────────────────────────────────
("""warehouses""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    warehouse_code VARCHAR(100) UNIQUE NOT NULL,
    warehouse_name VARCHAR(200) NOT NULL,
    location VARCHAR(200),
    warehouse_type VARCHAR(50) DEFAULT '일반창고',
    capacity DECIMAL(18,2) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""inventory""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_code VARCHAR(100) UNIQUE NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    material_id INT, category VARCHAR(100),
    warehouse_id INT, warehouse VARCHAR(100), bin_code VARCHAR(100),
    stock_qty INT DEFAULT 0, system_qty INT DEFAULT 0,
    unit_price DECIMAL(18,2) DEFAULT 0, min_stock INT DEFAULT 0,
    lot_number VARCHAR(100), expiry_date DATE, serial_number VARCHAR(100),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"""),

("""stock_movements""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    movement_number VARCHAR(100) UNIQUE NOT NULL,
    movement_type VARCHAR(50) NOT NULL,
    item_code VARCHAR(100), item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL,
    from_location VARCHAR(100), to_location VARCHAR(100), warehouse VARCHAR(100),
    lot_number VARCHAR(100),
    reference_number VARCHAR(200), reference VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""storage_bins""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    bin_code VARCHAR(100) UNIQUE NOT NULL,
    warehouse_id INT, warehouse_name VARCHAR(200),
    zone VARCHAR(50), bin_type VARCHAR(50) DEFAULT '일반',
    max_weight DECIMAL(10,2) DEFAULT 0,
    is_occupied TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""asn""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    asn_number VARCHAR(100) UNIQUE NOT NULL,
    po_id INT, item_name VARCHAR(200) NOT NULL,
    expected_qty INT NOT NULL, expected_date DATE, warehouse VARCHAR(100),
    status VARCHAR(20) DEFAULT '예정',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""inbound_inspection""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    asn_id INT, item_name VARCHAR(200) NOT NULL,
    expected_qty INT NOT NULL, received_qty INT NOT NULL, defect_qty INT DEFAULT 0,
    inspector VARCHAR(100), result VARCHAR(20) DEFAULT '정상', note TEXT,
    inspected_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""disposal""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    disposal_number VARCHAR(100) UNIQUE NOT NULL,
    item_name VARCHAR(200) NOT NULL, quantity INT NOT NULL,
    reason TEXT, disposal_type VARCHAR(50) DEFAULT '폐기',
    approved_by VARCHAR(100),
    status VARCHAR(20) DEFAULT '승인대기',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""pick_waves""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    wave_number VARCHAR(100) UNIQUE NOT NULL,
    wave_type VARCHAR(50) DEFAULT '일반',
    wave_date DATE, picker VARCHAR(100),
    total_lines INT DEFAULT 0, picked_lines INT DEFAULT 0,
    status VARCHAR(20) DEFAULT '대기',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""pick_wave_lines""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    wave_id INT, delivery_id INT,
    item_name VARCHAR(200) NOT NULL,
    bin_location VARCHAR(100),
    required_qty INT DEFAULT 0, picked_qty INT DEFAULT 0,
    status VARCHAR(20) DEFAULT '대기',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""putaway_tasks""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_number VARCHAR(100) UNIQUE NOT NULL,
    item_name VARCHAR(200) NOT NULL, quantity INT DEFAULT 0,
    from_location VARCHAR(100), to_zone VARCHAR(50), to_bin VARCHAR(100),
    assigned_to VARCHAR(100),
    status VARCHAR(20) DEFAULT '대기',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""putaway_rules""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(200), item_category VARCHAR(100),
    preferred_zone VARCHAR(50), preferred_bin VARCHAR(100),
    rule_type VARCHAR(50) DEFAULT '품목',
    priority INT DEFAULT 1, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

# ── TM 무역관리 ──────────────────────────────────────
("""exchange_rates""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    currency VARCHAR(10) NOT NULL,
    rate_to_krw DECIMAL(18,4) NOT NULL,
    rate_date DATE NOT NULL,
    source VARCHAR(50) DEFAULT '수동입력',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""logistics""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    bl_number VARCHAR(100) UNIQUE NOT NULL,
    ci_id INT, transport_type VARCHAR(20) DEFAULT '해상',
    carrier VARCHAR(100), departure_date DATE, arrival_date DATE,
    status VARCHAR(20) DEFAULT '운송중',
    customs_cleared TINYINT(1) DEFAULT 0,
    freight_cost DECIMAL(18,2) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""freight_orders""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    freight_number VARCHAR(100) UNIQUE NOT NULL,
    transport_mode VARCHAR(20) DEFAULT '육상',
    carrier VARCHAR(100), vehicle_number VARCHAR(100),
    forwarder_name VARCHAR(200),
    origin VARCHAR(200), destination VARCHAR(200),
    planned_departure DATETIME, planned_arrival DATETIME,
    actual_departure DATETIME, actual_arrival DATETIME,
    freight_cost DECIMAL(18,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT '계획',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""commercial_invoices""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    ci_number VARCHAR(100) UNIQUE NOT NULL,
    po_id INT, supplier VARCHAR(200) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL, unit_price DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    origin_country VARCHAR(100), hs_code VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""tax_invoices""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    po_id INT, supplier VARCHAR(200) NOT NULL,
    amount DECIMAL(18,2) NOT NULL, tax_amount DECIMAL(18,2) NOT NULL,
    issue_date DATE, paid TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""containers""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    container_number VARCHAR(100) UNIQUE NOT NULL,
    container_type VARCHAR(20) DEFAULT '20GP',
    bl_id INT, forwarder_id INT,
    seal_number VARCHAR(100),
    origin_port VARCHAR(100), dest_port VARCHAR(100),
    etd DATE, eta DATE,
    free_days INT DEFAULT 14, demurrage_rate DECIMAL(10,2) DEFAULT 0,
    return_deadline DATE,
    status VARCHAR(20) DEFAULT '예약',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""hs_codes""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    hs_code VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(500) NOT NULL,
    import_duty_rate DECIMAL(5,2) DEFAULT 0,
    vat_rate DECIMAL(5,2) DEFAULT 10.0,
    unit VARCHAR(20) DEFAULT 'KG',
    special_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""fta_agreements""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    agreement_name VARCHAR(200) NOT NULL,
    partner_country VARCHAR(100) NOT NULL,
    hs_code VARCHAR(50),
    preferential_rate DECIMAL(5,2) DEFAULT 0,
    origin_criteria TEXT, effective_date DATE,
    status VARCHAR(20) DEFAULT '유효',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""import_declarations""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    decl_number VARCHAR(100) UNIQUE NOT NULL,
    ci_id INT, bl_id INT,
    item_name VARCHAR(200) NOT NULL, hs_code VARCHAR(50),
    quantity DECIMAL(18,4) NOT NULL,
    invoice_value DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    exchange_rate DECIMAL(10,4) DEFAULT 0,
    krw_value DECIMAL(18,2) DEFAULT 0,
    customs_duty DECIMAL(18,2) DEFAULT 0,
    vat_amount DECIMAL(18,2) DEFAULT 0,
    total_tax DECIMAL(18,2) DEFAULT 0,
    fta_applied TINYINT(1) DEFAULT 0, fta_agreement VARCHAR(200),
    origin_country VARCHAR(100),
    declaration_date DATE, clearance_date DATE,
    customs_ref VARCHAR(100), import_requirement TEXT,
    status VARCHAR(20) DEFAULT '신고대기',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""export_declarations""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    decl_number VARCHAR(100) UNIQUE NOT NULL,
    exporter VARCHAR(200) NOT NULL, consignee VARCHAR(200) NOT NULL,
    destination_country VARCHAR(100) NOT NULL,
    item_name VARCHAR(200) NOT NULL, hs_code VARCHAR(50),
    quantity DECIMAL(18,4) NOT NULL,
    invoice_value DECIMAL(18,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    incoterms VARCHAR(20) DEFAULT 'FOB',
    port_of_loading VARCHAR(100), port_of_discharge VARCHAR(100),
    declaration_date DATE, clearance_date DATE,
    customs_ref VARCHAR(100), export_license VARCHAR(100),
    status VARCHAR(20) DEFAULT '신고대기',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""letters_of_credit""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    lc_number VARCHAR(100) UNIQUE NOT NULL,
    po_id INT, beneficiary VARCHAR(200), applicant VARCHAR(200),
    issuing_bank VARCHAR(200), advising_bank VARCHAR(200),
    amount DECIMAL(18,2) NOT NULL, currency VARCHAR(10) DEFAULT 'USD',
    issue_date DATE, expiry_date DATE, shipment_date DATE,
    lc_type VARCHAR(50) DEFAULT '취소불능',
    incoterms VARCHAR(20) DEFAULT 'FOB',
    port_of_loading VARCHAR(100), port_of_discharge VARCHAR(100),
    partial_shipment VARCHAR(20) DEFAULT '허용',
    transhipment VARCHAR(20) DEFAULT '금지',
    documents_required TEXT,
    status VARCHAR(20) DEFAULT '개설',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""forwarders""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    forwarder_code VARCHAR(100) UNIQUE NOT NULL,
    forwarder_name VARCHAR(200) NOT NULL,
    contact VARCHAR(100), phone VARCHAR(50), email VARCHAR(200),
    country VARCHAR(100), region VARCHAR(100),
    transport_modes VARCHAR(200),
    rating DECIMAL(3,1) DEFAULT 0,
    status VARCHAR(20) DEFAULT '활성',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""settlements""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    settlement_number VARCHAR(100) UNIQUE NOT NULL,
    platform VARCHAR(100) NOT NULL, period VARCHAR(50) NOT NULL,
    gross_sales DECIMAL(18,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    commission_amount DECIMAL(18,2) NOT NULL,
    net_amount DECIMAL(18,2) NOT NULL,
    status VARCHAR(20) DEFAULT '정산대기',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""shipment_events""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    bl_id INT, container_id INT,
    event_type VARCHAR(100) NOT NULL,
    event_date DATETIME, location VARCHAR(200), description TEXT,
    source VARCHAR(100) DEFAULT '수동입력',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""freight_quotes""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    fq_number VARCHAR(100) UNIQUE NOT NULL,
    transport_mode VARCHAR(20) DEFAULT '해상',
    origin VARCHAR(200), destination VARCHAR(200), carrier VARCHAR(100),
    weight_kg DECIMAL(10,2) DEFAULT 0, cbm DECIMAL(10,3) DEFAULT 0,
    freight_cost DECIMAL(18,2) DEFAULT 0, surcharges DECIMAL(18,2) DEFAULT 0,
    total_cost_krw DECIMAL(18,2) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'USD', valid_until DATE, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""trade_payments""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    payment_number VARCHAR(100) UNIQUE NOT NULL,
    ci_id INT, payment_type VARCHAR(50) DEFAULT 'T/T',
    direction VARCHAR(20) DEFAULT '지급', counterpart VARCHAR(200),
    amount DECIMAL(18,2) NOT NULL, currency VARCHAR(10) DEFAULT 'USD',
    exchange_rate DECIMAL(10,4) DEFAULT 0, krw_amount DECIMAL(18,2) DEFAULT 0,
    due_date DATE, paid_date DATE,
    bank_name VARCHAR(200), bank_ref VARCHAR(200),
    status VARCHAR(20) DEFAULT '미지급',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""customs_payments""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    payment_number VARCHAR(100) UNIQUE NOT NULL,
    import_decl_id INT, decl_number VARCHAR(100), item_name VARCHAR(200),
    duty_amount DECIMAL(18,2) DEFAULT 0, vat_amount DECIMAL(18,2) DEFAULT 0,
    other_tax DECIMAL(18,2) DEFAULT 0, total_amount DECIMAL(18,2) DEFAULT 0,
    due_date DATE, paid_date DATE,
    payment_method VARCHAR(50) DEFAULT '계좌이체', bank_ref VARCHAR(200),
    installment TINYINT(1) DEFAULT 0, installment_seq INT DEFAULT 1,
    status VARCHAR(20) DEFAULT '미납',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""origin_certificates""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    co_number VARCHAR(100) UNIQUE NOT NULL,
    co_type VARCHAR(50) DEFAULT '일반원산지증명서',
    fta_agreement VARCHAR(200),
    item_name VARCHAR(200) NOT NULL, hs_code VARCHAR(50),
    origin_country VARCHAR(100), dest_country VARCHAR(100),
    quantity DECIMAL(18,4) DEFAULT 0, unit VARCHAR(20) DEFAULT 'EA',
    fob_value DECIMAL(18,2) DEFAULT 0, currency VARCHAR(10) DEFAULT 'USD',
    exporter_name VARCHAR(200), importer_name VARCHAR(200),
    issue_date DATE, valid_to DATE,
    status VARCHAR(20) DEFAULT '발급완료',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""export_packing_lists""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    epl_number VARCHAR(100) UNIQUE NOT NULL,
    ci_id INT, export_decl_id INT, bl_number VARCHAR(100),
    shipper VARCHAR(200), consignee VARCHAR(200),
    item_name VARCHAR(200) NOT NULL,
    total_boxes INT DEFAULT 0, qty_per_box INT DEFAULT 0, total_qty INT DEFAULT 0,
    gross_weight DECIMAL(10,2) DEFAULT 0, net_weight DECIMAL(10,2) DEFAULT 0,
    dimensions VARCHAR(200), marks TEXT,
    vessel_name VARCHAR(200),
    port_of_loading VARCHAR(100), port_of_discharge VARCHAR(100),
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""export_refunds""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    refund_number VARCHAR(100) UNIQUE NOT NULL,
    export_decl_id INT, decl_number VARCHAR(100), hs_code VARCHAR(50),
    item_name VARCHAR(200) NOT NULL,
    export_qty DECIMAL(18,4) DEFAULT 0,
    paid_duty DECIMAL(18,2) DEFAULT 0, refund_rate DECIMAL(5,2) DEFAULT 0,
    refund_amount DECIMAL(18,2) DEFAULT 0,
    apply_date DATE, receive_date DATE, customs_ref VARCHAR(100),
    status VARCHAR(20) DEFAULT '신청예정',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""trade_insurance""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    insurance_number VARCHAR(100) UNIQUE NOT NULL,
    insurance_type VARCHAR(50) DEFAULT '수출보험',
    insurer VARCHAR(200), insured VARCHAR(200),
    coverage_amount DECIMAL(18,2) DEFAULT 0, premium DECIMAL(18,2) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'USD',
    start_date DATE, end_date DATE, claim_amount DECIMAL(18,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT '유효',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""strategic_goods_checks""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    check_number VARCHAR(100) UNIQUE NOT NULL,
    check_type VARCHAR(50) DEFAULT '수출허가',
    item_name VARCHAR(200) NOT NULL, hs_code VARCHAR(50),
    destination_country VARCHAR(100), end_user VARCHAR(200),
    restriction_level VARCHAR(20) DEFAULT '일반',
    result VARCHAR(20) DEFAULT '검토중',
    checker VARCHAR(100), checked_at DATETIME, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

("""import_requirements""", """
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(200) NOT NULL, hs_code VARCHAR(50),
    requirement_type VARCHAR(100), description TEXT, required_docs TEXT,
    agency VARCHAR(200), status VARCHAR(20) DEFAULT '확인필요',
    checked_at DATE, note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP"""),

    ]  # end tbls

    for name, cols in tbls:
        c.execute(f"CREATE TABLE IF NOT EXISTS {name} ({cols}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

    conn.commit()
    c.close()
    conn.close()
    print("✅ MySQL DB 초기화 완료 — 총", len(tbls), "테이블")


def insert_default_data():
    import bcrypt
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT IGNORE INTO allowed_domains (domain) VALUES (%s)", ("company.com",))
    pw = bcrypt.hashpw("admin1234".encode(), bcrypt.gensalt()).decode()
    c.execute("INSERT IGNORE INTO users (email,name,password,department,is_admin) VALUES (%s,%s,%s,%s,1)",
              ("admin@company.com","시스템관리자",pw,"IT"))
    today = datetime.now().strftime('%Y-%m-%d')
    for cur, rate in [('USD',1350),('EUR',1450),('JPY',9),('CNY',186)]:
        c.execute("INSERT IGNORE INTO exchange_rates (currency,rate_to_krw,rate_date) VALUES (%s,%s,%s)",
                  (cur,rate,today))
    conn.commit()
    c.close()
    conn.close()
    print("✅ 기본 데이터 삽입 완료")
