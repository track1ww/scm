import sqlite3
import os
from datetime import datetime

try:
    DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'scm.db')
except NameError:
    DB_PATH = os.path.join(os.getcwd(), 'scm.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def gen_number(prefix):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── MM ──────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, contact TEXT, email TEXT,
        phone TEXT, address TEXT,
        payment_terms TEXT, return_policy TEXT,
        status TEXT DEFAULT '활성',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_code TEXT UNIQUE NOT NULL,
        material_name TEXT NOT NULL,
        material_type TEXT DEFAULT '원자재',
        unit TEXT DEFAULT 'EA',
        category TEXT, storage_condition TEXT,
        standard_price REAL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS purchase_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pr_number TEXT UNIQUE NOT NULL,
        requester TEXT NOT NULL,
        department TEXT,
        material_id INTEGER,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        required_date TEXT,
        reason TEXT,
        status TEXT DEFAULT '승인대기',
        approved_by TEXT,
        approved_at TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_number TEXT UNIQUE NOT NULL,
        supplier_id INTEGER, material_id INTEGER,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL, unit_price REAL NOT NULL,
        currency TEXT DEFAULT 'KRW',
        valid_until TEXT, status TEXT DEFAULT '검토중',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS supplier_contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_number TEXT UNIQUE NOT NULL,
        supplier_id INTEGER,
        item_name TEXT NOT NULL,
        contract_qty INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        currency TEXT DEFAULT 'KRW',
        start_date TEXT, end_date TEXT,
        status TEXT DEFAULT '유효',
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_number TEXT UNIQUE NOT NULL,
        pr_id INTEGER,
        supplier_id INTEGER, material_id INTEGER,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL, unit_price REAL NOT NULL,
        currency TEXT DEFAULT 'KRW',
        delivery_date TEXT, warehouse TEXT,
        status TEXT DEFAULT '발주완료', note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (pr_id) REFERENCES purchase_requests(id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS goods_receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gr_number TEXT UNIQUE NOT NULL,
        po_id INTEGER,
        item_name TEXT NOT NULL,
        ordered_qty INTEGER NOT NULL,
        received_qty INTEGER NOT NULL,
        rejected_qty INTEGER DEFAULT 0,
        warehouse TEXT, bin_code TEXT,
        receiver TEXT, note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS invoice_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        iv_number TEXT UNIQUE NOT NULL,
        po_id INTEGER, gr_id INTEGER,
        supplier TEXT NOT NULL,
        invoice_ref TEXT,
        po_amount REAL DEFAULT 0,
        gr_amount REAL DEFAULT 0,
        invoice_amount REAL NOT NULL,
        tax_amount REAL DEFAULT 0,
        match_status TEXT DEFAULT '검증중',
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id),
        FOREIGN KEY (gr_id) REFERENCES goods_receipts(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS supplier_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        eval_number TEXT UNIQUE NOT NULL,
        supplier_id INTEGER,
        eval_period TEXT,
        delivery_score REAL DEFAULT 0,
        quality_score REAL DEFAULT 0,
        price_score REAL DEFAULT 0,
        service_score REAL DEFAULT 0,
        total_score REAL DEFAULT 0,
        grade TEXT,
        evaluator TEXT, note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )''')

    # ── SD ──────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_code TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        contact TEXT, email TEXT, phone TEXT, address TEXT,
        customer_group TEXT DEFAULT '일반',
        credit_limit REAL DEFAULT 0,
        credit_used REAL DEFAULT 0,
        status TEXT DEFAULT '활성',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sd_quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sd_quote_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        discount_rate REAL DEFAULT 0,
        final_price REAL NOT NULL,
        valid_until TEXT,
        status TEXT DEFAULT '검토중',
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sales_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        sd_quote_id INTEGER,
        platform TEXT, customer_name TEXT,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL, unit_price REAL NOT NULL,
        discount_rate REAL DEFAULT 0,
        requested_delivery TEXT,
        confirmed_delivery TEXT,
        atp_checked INTEGER DEFAULT 0,
        credit_checked INTEGER DEFAULT 0,
        status TEXT DEFAULT '주문접수',
        tracking_number TEXT,
        ordered_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (sd_quote_id) REFERENCES sd_quotations(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        delivery_number TEXT UNIQUE NOT NULL,
        order_id INTEGER,
        item_name TEXT NOT NULL,
        delivery_qty INTEGER NOT NULL,
        pick_qty INTEGER DEFAULT 0,
        pack_qty INTEGER DEFAULT 0,
        delivery_date TEXT,
        carrier TEXT, tracking_number TEXT,
        status TEXT DEFAULT '출하준비',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (order_id) REFERENCES sales_orders(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        order_id INTEGER,
        customer_name TEXT,
        amount REAL NOT NULL, tax_amount REAL NOT NULL,
        issue_date TEXT, due_date TEXT,
        paid INTEGER DEFAULT 0,
        paid_at TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (order_id) REFERENCES sales_orders(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        return_number TEXT UNIQUE NOT NULL,
        order_id INTEGER, item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL, reason TEXT,
        refund_amount REAL DEFAULT 0,
        status TEXT DEFAULT '반품접수',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (order_id) REFERENCES sales_orders(id)
    )''')

    # ── PP ──────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS production_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_number TEXT UNIQUE NOT NULL,
        product_name TEXT NOT NULL,
        planned_qty INTEGER NOT NULL,
        start_date TEXT, end_date TEXT,
        work_center TEXT,
        status TEXT DEFAULT '계획',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bom (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        component_name TEXT NOT NULL,
        component_code TEXT,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'EA',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS mrp_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mrp_number TEXT UNIQUE NOT NULL,
        material_name TEXT NOT NULL,
        required_qty INTEGER NOT NULL,
        required_date TEXT,
        source TEXT DEFAULT 'MRP자동',
        status TEXT DEFAULT '요청',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # ── QM ──────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS quality_inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_number TEXT UNIQUE NOT NULL,
        inspection_type TEXT DEFAULT '수입검사',
        item_name TEXT NOT NULL,
        lot_number TEXT,
        sample_qty INTEGER NOT NULL,
        pass_qty INTEGER DEFAULT 0,
        fail_qty INTEGER DEFAULT 0,
        inspector TEXT,
        result TEXT DEFAULT '합격',
        note TEXT,
        inspected_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS nonconformance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nc_number TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        defect_type TEXT,
        quantity INTEGER NOT NULL,
        severity TEXT DEFAULT '경미',
        root_cause TEXT,
        corrective_action TEXT,
        status TEXT DEFAULT '조사중',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # ── WM ──────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        warehouse_code TEXT UNIQUE NOT NULL,
        warehouse_name TEXT NOT NULL,
        location TEXT,
        warehouse_type TEXT DEFAULT '일반창고',
        capacity REAL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS storage_bins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bin_code TEXT UNIQUE NOT NULL,
        warehouse_id INTEGER,
        zone TEXT,
        bin_type TEXT DEFAULT '일반',
        max_weight REAL DEFAULT 0,
        is_occupied INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        material_id INTEGER,
        category TEXT,
        warehouse_id INTEGER,
        warehouse TEXT,
        bin_code TEXT,
        stock_qty INTEGER DEFAULT 0,
        system_qty INTEGER DEFAULT 0,
        unit_price REAL DEFAULT 0,
        min_stock INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (material_id) REFERENCES materials(id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movement_number TEXT UNIQUE NOT NULL,
        movement_type TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        from_location TEXT,
        to_location TEXT,
        reference TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS asn (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asn_number TEXT UNIQUE NOT NULL,
        po_id INTEGER, item_name TEXT NOT NULL,
        expected_qty INTEGER NOT NULL, expected_date TEXT,
        warehouse TEXT, status TEXT DEFAULT '예정',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS inbound_inspection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asn_id INTEGER, item_name TEXT NOT NULL,
        expected_qty INTEGER NOT NULL, received_qty INTEGER NOT NULL,
        defect_qty INTEGER DEFAULT 0, inspector TEXT,
        result TEXT DEFAULT '정상', note TEXT,
        inspected_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (asn_id) REFERENCES asn(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS disposal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        disposal_number TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL, quantity INTEGER NOT NULL,
        reason TEXT, disposal_type TEXT DEFAULT '폐기',
        approved_by TEXT, status TEXT DEFAULT '승인대기',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # ── TM ──────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS commercial_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ci_number TEXT UNIQUE NOT NULL,
        po_id INTEGER, supplier TEXT NOT NULL,
        item_name TEXT NOT NULL, quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL, currency TEXT DEFAULT 'USD',
        origin_country TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS logistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bl_number TEXT UNIQUE NOT NULL,
        ci_id INTEGER, transport_type TEXT DEFAULT '해상',
        carrier TEXT, departure_date TEXT, arrival_date TEXT,
        status TEXT DEFAULT '운송중', customs_cleared INTEGER DEFAULT 0,
        freight_cost REAL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (ci_id) REFERENCES commercial_invoices(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS freight_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        freight_number TEXT UNIQUE NOT NULL,
        transport_mode TEXT DEFAULT '육상',
        carrier TEXT, vehicle_number TEXT,
        origin TEXT, destination TEXT,
        planned_departure TEXT, planned_arrival TEXT,
        actual_departure TEXT, actual_arrival TEXT,
        freight_cost REAL DEFAULT 0,
        status TEXT DEFAULT '계획',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # ── 정산 ──────────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS tax_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        po_id INTEGER, supplier TEXT NOT NULL,
        amount REAL NOT NULL, tax_amount REAL NOT NULL,
        issue_date TEXT, paid INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS settlements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        settlement_number TEXT UNIQUE NOT NULL,
        platform TEXT NOT NULL, period TEXT NOT NULL,
        gross_sales REAL NOT NULL, commission_rate REAL NOT NULL,
        commission_amount REAL NOT NULL, net_amount REAL NOT NULL,
        status TEXT DEFAULT '정산대기',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    conn.commit()
    conn.close()

def init_trade_db():
    """수출입 관련 테이블 추가 초기화"""
    conn = get_db()
    c = conn.cursor()

    # HS Code 마스터
    c.execute('''CREATE TABLE IF NOT EXISTS hs_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hs_code TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL,
        import_duty_rate REAL DEFAULT 0,
        vat_rate REAL DEFAULT 10.0,
        unit TEXT DEFAULT 'KG',
        special_notes TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # FTA 협정 마스터
    c.execute('''CREATE TABLE IF NOT EXISTS fta_agreements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agreement_name TEXT NOT NULL,
        partner_country TEXT NOT NULL,
        hs_code TEXT,
        preferential_rate REAL DEFAULT 0,
        origin_criteria TEXT,
        effective_date TEXT,
        status TEXT DEFAULT '유효',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # 환율 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS exchange_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        currency TEXT NOT NULL,
        rate_to_krw REAL NOT NULL,
        rate_date TEXT NOT NULL,
        source TEXT DEFAULT '수동입력',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # 수입신고서
    c.execute('''CREATE TABLE IF NOT EXISTS import_declarations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decl_number TEXT UNIQUE NOT NULL,
        bl_id INTEGER,
        ci_id INTEGER,
        hs_code TEXT,
        item_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'KG',
        invoice_value REAL NOT NULL,
        currency TEXT DEFAULT 'USD',
        exchange_rate REAL DEFAULT 0,
        krw_value REAL DEFAULT 0,
        customs_duty REAL DEFAULT 0,
        vat_amount REAL DEFAULT 0,
        total_tax REAL DEFAULT 0,
        fta_applied INTEGER DEFAULT 0,
        fta_agreement TEXT,
        origin_country TEXT,
        import_requirement TEXT,
        declaration_date TEXT,
        clearance_date TEXT,
        customs_ref TEXT,
        status TEXT DEFAULT '신고대기',
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (bl_id) REFERENCES logistics(id),
        FOREIGN KEY (ci_id) REFERENCES commercial_invoices(id)
    )''')

    # 수출신고서 (수출면장)
    c.execute('''CREATE TABLE IF NOT EXISTS export_declarations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decl_number TEXT UNIQUE NOT NULL,
        exporter TEXT NOT NULL,
        consignee TEXT NOT NULL,
        destination_country TEXT NOT NULL,
        hs_code TEXT,
        item_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'KG',
        invoice_value REAL NOT NULL,
        currency TEXT DEFAULT 'USD',
        incoterms TEXT DEFAULT 'FOB',
        port_of_loading TEXT,
        port_of_discharge TEXT,
        strategic_check INTEGER DEFAULT 0,
        strategic_result TEXT DEFAULT '미확인',
        export_license TEXT,
        declaration_date TEXT,
        clearance_date TEXT,
        customs_ref TEXT,
        status TEXT DEFAULT '신고대기',
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # L/C (신용장)
    c.execute('''CREATE TABLE IF NOT EXISTS letters_of_credit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lc_number TEXT UNIQUE NOT NULL,
        lc_type TEXT DEFAULT '취소불능',
        issuing_bank TEXT NOT NULL,
        advising_bank TEXT,
        applicant TEXT NOT NULL,
        beneficiary TEXT NOT NULL,
        currency TEXT DEFAULT 'USD',
        amount REAL NOT NULL,
        expiry_date TEXT,
        shipment_date TEXT,
        incoterms TEXT DEFAULT 'FOB',
        port_of_loading TEXT,
        port_of_discharge TEXT,
        partial_shipment TEXT DEFAULT '불허',
        transhipment TEXT DEFAULT '불허',
        documents_required TEXT,
        status TEXT DEFAULT '개설',
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # 수입요건 확인
    c.execute('''CREATE TABLE IF NOT EXISTS import_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hs_code TEXT,
        item_name TEXT NOT NULL,
        requirement_type TEXT NOT NULL,
        agency TEXT,
        description TEXT,
        required_docs TEXT,
        status TEXT DEFAULT '확인필요',
        checked_at TEXT,
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # 전략물자 체크 이력
    c.execute('''CREATE TABLE IF NOT EXISTS strategic_goods_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_number TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        hs_code TEXT,
        destination_country TEXT,
        end_user TEXT,
        check_type TEXT DEFAULT '수출',
        result TEXT DEFAULT '미확인',
        restriction_level TEXT DEFAULT '없음',
        checker TEXT,
        checked_at TEXT,
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')

    # 기본 환율 데이터 삽입
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    default_rates = [
        ('USD', 1350.0), ('EUR', 1450.0), ('JPY', 9.0),
        ('CNY', 186.0), ('GBP', 1700.0), ('SGD', 1000.0)
    ]
    for currency, rate in default_rates:
        c.execute("""INSERT OR IGNORE INTO exchange_rates(currency, rate_to_krw, rate_date, source)
            VALUES(?,?,?,'기본값(수동수정필요)')""", (currency, rate, today))

    # 기본 HS Code 샘플
    sample_hs = [
        ('8471.30', '휴대용 자동자료처리기계', 0.0, 10.0, 'EA', '전략물자 해당가능'),
        ('8517.12', '휴대전화기', 0.0, 10.0, 'EA', '전파인증 필요'),
        ('6203.42', '면제 바지류', 13.0, 10.0, 'KG', None),
        ('8703.23', '승용자동차(1000~1500cc)', 8.0, 10.0, 'EA', None),
        ('0201.10', '신선 쇠고기(도체)', 40.0, 10.0, 'KG', '검역 필요'),
        ('2709.00', '원유', 3.0, 0.0, 'L', '에너지세 별도'),
    ]
    for row in sample_hs:
        c.execute("""INSERT OR IGNORE INTO hs_codes
            (hs_code,description,import_duty_rate,vat_rate,unit,special_notes)
            VALUES(?,?,?,?,?,?)""", row)

    # 기본 FTA 데이터
    sample_fta = [
        ('한-미 FTA', '미국', '8471.30', 0.0, '완전생산기준(WO) 또는 세번변경기준'),
        ('한-EU FTA', '독일', '8471.30', 0.0, '부가가치기준 45% 이상'),
        ('한-중 FTA', '중국', '6203.42', 8.0, '세번변경기준(CTH)'),
        ('한-ASEAN FTA', '베트남', '6203.42', 5.0, '부가가치기준 40% 이상'),
        ('RCEP', '일본', '8703.23', 0.0, '원산지 누적기준 적용'),
    ]
    for row in sample_fta:
        c.execute("""INSERT OR IGNORE INTO fta_agreements
            (agreement_name,partner_country,hs_code,preferential_rate,origin_criteria)
            VALUES(?,?,?,?,?)""", row)

    conn.commit()
    conn.close()

def init_mm_extended_db():
    """MM 확장 테이블 초기화"""
    conn = get_db()
    c = conn.cursor()

    # 구매정보 레코드 (PIR) - 공급사+자재 조합별 협의가격
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_info_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pir_number TEXT UNIQUE NOT NULL,
        supplier_id INTEGER NOT NULL,
        material_id INTEGER,
        item_name TEXT NOT NULL,
        unit TEXT DEFAULT 'EA',
        agreed_price REAL NOT NULL,
        currency TEXT DEFAULT 'KRW',
        min_order_qty INTEGER DEFAULT 1,
        lead_time_days INTEGER DEFAULT 0,
        valid_from TEXT,
        valid_to TEXT,
        status TEXT DEFAULT '유효',
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')

    # PO 변경이력
    c.execute('''CREATE TABLE IF NOT EXISTS po_change_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id INTEGER NOT NULL,
        po_number TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        changed_field TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        changed_by TEXT,
        change_reason TEXT,
        changed_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
    )''')

    # 세금계산서 (공급사→우리 회사 수취분)
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_tax_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tax_inv_number TEXT UNIQUE NOT NULL,
        iv_id INTEGER,
        po_id INTEGER,
        gr_id INTEGER,
        supplier TEXT NOT NULL,
        supply_amount REAL NOT NULL,
        tax_amount REAL NOT NULL,
        total_amount REAL NOT NULL,
        issue_date TEXT,
        due_date TEXT,
        payment_status TEXT DEFAULT '미결',
        paid_at TEXT,
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (iv_id) REFERENCES invoice_verifications(id),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
    )''')

    # 지급 스케줄
    c.execute('''CREATE TABLE IF NOT EXISTS payment_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_number TEXT UNIQUE NOT NULL,
        tax_inv_id INTEGER,
        supplier TEXT NOT NULL,
        payment_amount REAL NOT NULL,
        currency TEXT DEFAULT 'KRW',
        due_date TEXT NOT NULL,
        payment_method TEXT DEFAULT '계좌이체',
        status TEXT DEFAULT '예정',
        paid_at TEXT,
        note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (tax_inv_id) REFERENCES purchase_tax_invoices(id)
    )''')

    # 부분입고 잔량 추적 (PO별 누적 입고량)
    c.execute('''CREATE TABLE IF NOT EXISTS po_receipt_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id INTEGER UNIQUE NOT NULL,
        ordered_qty INTEGER NOT NULL,
        received_qty INTEGER DEFAULT 0,
        remaining_qty INTEGER NOT NULL,
        last_gr_date TEXT,
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (po_id) REFERENCES purchase_orders(id)
    )''')

    conn.commit()
    conn.close()
