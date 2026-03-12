import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number, init_mm_extended_db
from utils.design import inject_css, apply_plotly_theme
from datetime import datetime, timedelta

try:
    init_mm_extended_db()
except:
    pass

def _add_col(c, table, col, col_type="TEXT"):
    """컬럼이 없으면 추가, 있으면 무시"""
    try:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
    except:
        pass

def init_mm_extra():
    conn = get_db()
    c = conn.cursor()

    # ── 기존 테이블 컬럼 자동 마이그레이션 ──────────────
    _add_col(c, "invoice_verifications", "supplier_invoice_no", "TEXT")
    _add_col(c, "invoice_verifications", "variance_amount", "REAL DEFAULT 0")
    _add_col(c, "invoice_verifications", "match_result", "TEXT DEFAULT '검토중'")
    _add_col(c, "invoice_verifications", "status", "TEXT DEFAULT '검토중'")

    _add_col(c, "supplier_evaluations", "evaluation_period", "TEXT")
    _add_col(c, "supplier_evaluations", "comment", "TEXT")
    _add_col(c, "supplier_evaluations", "grade", "TEXT")

    _add_col(c, "purchase_tax_invoices", "ti_number", "TEXT")
    _add_col(c, "purchase_tax_invoices", "supplier_id", "INTEGER")
    _add_col(c, "purchase_tax_invoices", "supplier_name", "TEXT")
    _add_col(c, "purchase_tax_invoices", "tax_invoice_no", "TEXT")
    _add_col(c, "purchase_tax_invoices", "payment_terms", "TEXT DEFAULT '30일'")
    _add_col(c, "purchase_tax_invoices", "payment_method", "TEXT DEFAULT '계좌이체'")
    _add_col(c, "purchase_tax_invoices", "payment_status", "TEXT DEFAULT '미지급'")

    _add_col(c, "payment_schedule", "ti_number", "TEXT")
    _add_col(c, "payment_schedule", "supplier_name", "TEXT")

    _add_col(c, "purchase_orders", "delivery_date", "TEXT")
    _add_col(c, "purchase_orders", "warehouse", "TEXT")

    _add_col(c, "goods_receipts", "bin_code", "TEXT")
    _add_col(c, "goods_receipts", "lot_number", "TEXT")

    conn.commit()

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
    conn.commit()
    conn.close()

try:
    init_mm_extra()
except:
    pass

st.title("🛒 MM – Materials Management (자재관리)")
inject_css()
apply_plotly_theme()

# ── 대분류 탭 (4개) ──────────────────────────────
main_tabs = st.tabs([
    "🏭 공급사 · 자재",
    "📝 구매 프로세스",
    "📦 입출고",
    "💰 정산 · 분석",
])

# ── 대분류별 소분류 탭 인덱스 매핑 ──────────────────
# tabs[0~18] 기존 인덱스 그대로 유지하되, 대분류 컨텍스트 안에서 선언
# 대분류0: 공급사(0), 자재마스터(1), 대체자재(2), PIR(3), 공급사평가(17)
# 대분류1: PR(4), 품의서(5), RFQ(6), 견적비교(7), 계약(8), 블랭킷PO(9), PO(10)
# 대분류2: 입고GR(11), 반품RTV(12), 이동평균단가(13)
# 대분류3: 송장검증(14), 세금계산서(15), 지급관리(16), KPI(18)

with main_tabs[0]:
    sub0 = st.tabs(["🏭 공급사", "📦 자재 마스터", "🔗 대체자재", "💡 구매정보(PIR)", "⭐ 공급사 평가", "🔄 재발주점·자동발주", "🤝 VMI", "📊 공급사 분석"])
    tabs = {0: sub0[0], 1: sub0[1], 2: sub0[2], 3: sub0[3], 17: sub0[4], "rop": sub0[5], "vmi": sub0[6], "bi_sup": sub0[7]}

with main_tabs[1]:
    sub1 = st.tabs(["📝 구매요청(PR)", "📋 구매품의서", "💬 견적(RFQ)", "🔀 견적 비교", "📄 계약", "🗂️ 블랭킷PO", "📋 발주서(PO)", "📊 구매 분석"])
    tabs.update({4: sub1[0], 5: sub1[1], 6: sub1[2], 7: sub1[3], 8: sub1[4], 9: sub1[5], 10: sub1[6], "bi_po": sub1[7]})

with main_tabs[2]:
    sub2 = st.tabs(["📥 입고(GR)", "↩️ 반품(RTV)", "📈 이동평균단가", "📊 입출고 분석"])
    tabs.update({11: sub2[0], 12: sub2[1], 13: sub2[2], "bi_gr": sub2[3]})

with main_tabs[3]:
    sub3 = st.tabs(["🧾 송장검증", "🧾 세금계산서", "💰 지급관리", "📊 구매 KPI", "📊 정산 분석"])
    tabs.update({14: sub3[0], 15: sub3[1], 16: sub3[2], 18: sub3[3], "bi_pay": sub3[4]})


# ── 1. 공급사 ──────────────────────────────────────
with tabs[0]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("공급사 등록")
        with st.form("supplier_form", clear_on_submit=True):
            name    = st.text_input("공급사명 *")
            col_a, col_b = st.columns(2)
            contact = col_a.text_input("담당자")
            phone   = col_b.text_input("전화번호")
            col_c, col_d = st.columns(2)
            email   = col_c.text_input("이메일")
            biz_no  = col_d.text_input("사업자번호")
            address = st.text_area("주소", height=60)
            col_e, col_f = st.columns(2)
            payment = col_e.selectbox("결제조건", ["현금","30일","60일","90일","선불"])
            status  = col_f.selectbox("상태", ["활성","휴면","거래중지"])
            col_g, col_h = st.columns(2)
            sup_cat = col_g.selectbox("공급사 구분", ["일반","우선공급사","전략공급사","1회성"])
            currency_s = col_h.selectbox("기본통화", ["KRW","USD","EUR","JPY","CNY"])
            ret_pol = st.text_area("반품규정", height=60)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not name:
                    st.error("공급사명 필수")
                else:
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO suppliers
                            (name,contact,phone,email,address,payment_terms,return_policy,status)
                            VALUES(?,?,?,?,?,?,?,?)""",
                            (name,contact,phone,email,address,payment,ret_pol,status))
                        conn.commit(); conn.close()
                        st.success(f"'{name}' 등록 완료!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("공급사 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT s.id AS ID, s.name AS 공급사명, s.contact AS 담당자,
                   s.phone AS 전화, s.payment_terms AS 결제조건, s.status AS 상태,
                   ROUND(AVG(e.total_score),1) AS 평균평점,
                   COUNT(DISTINCT p.id) AS 발주건수
            FROM suppliers s
            LEFT JOIN supplier_evaluations e ON s.id=e.supplier_id
            LEFT JOIN purchase_orders p ON s.id=p.supplier_id
            GROUP BY s.id ORDER BY s.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("등록된 공급사 없음")
        else:
            search = st.text_input("🔍 검색")
            if search:
                df = df[df['공급사명'].str.contains(search, na=False)]
            def sup_color(row):
                if row['상태'] == '거래중지': return ['background-color:#fee2e2']*len(row)
                if row['상태'] == '휴면': return ['background-color:#fef3c7']*len(row)
                return ['']*len(row)
            st.dataframe(df.style.apply(sup_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (공급사) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_suppliers = {}
                for _, _r in df.iterrows():
                    _k = f"{_r.get('ID','?')} | {_r.get('공급사명', _r.iloc[1] if len(_r)>1 else '')}"
                    _row_opts_suppliers[_k] = int(_r['ID'])

                if _row_opts_suppliers:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_suppliers = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_suppliers.keys()),
                        key="_rbsel_suppliers", label_visibility="collapsed"
                    )
                    _rb_id_suppliers = _row_opts_suppliers[_rb_sel_suppliers]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_suppliers"):
                        st.session_state[f"_edit_suppliers"] = _rb_id_suppliers
                        st.session_state[f"_del_suppliers"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_suppliers"):
                        st.session_state[f"_del_suppliers"]  = _rb_id_suppliers
                        st.session_state[f"_edit_suppliers"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_suppliers"):
                    _del_id_suppliers = st.session_state[f"_del_suppliers"]
                    st.warning(f"⚠️ ID **{_del_id_suppliers}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_suppliers"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM suppliers WHERE id = ?", (_del_id_suppliers,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_suppliers"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_suppliers"):
                        st.session_state[f"_del_suppliers"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_suppliers"):
                    _edit_id_suppliers = st.session_state[f"_edit_suppliers"]
                    try:
                        _cx_e = get_db()
                        _edit_row_suppliers = dict(_cx_e.execute(
                            "SELECT * FROM suppliers WHERE id=?", (_edit_id_suppliers,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_suppliers = {}
                    with st.expander(f"✏️ 공급사 수정 — ID {_edit_id_suppliers}", expanded=True):
                        if not _edit_row_suppliers:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_suppliers = [c for c in _edit_row_suppliers if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_suppliers)))
                            _ecols = st.columns(_ncols)
                            _new_vals_suppliers = {}
                            for _i, _fc in enumerate(_edit_fields_suppliers):
                                _cv = _edit_row_suppliers[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_suppliers[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_suppliers}_{_fc}_suppliers")
                                else:
                                    _new_vals_suppliers[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_suppliers}_{_fc}_suppliers")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_suppliers"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_suppliers])
                                _set_params = list(_new_vals_suppliers.values()) + [_edit_id_suppliers]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE suppliers SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_suppliers"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_suppliers"):
                                st.session_state[f"_edit_suppliers"] = None; st.rerun()

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("총 공급사", len(df))
            col_m2.metric("활성", len(df[df['상태']=='활성']))
            col_m3.metric("거래중지", len(df[df['상태']=='거래중지']))
        st.divider()
        st.subheader("상태 변경")
        conn = get_db()
        sups = [dict(r) for r in conn.execute("SELECT id, name, status FROM suppliers").fetchall()]
        conn.close()
        if sups:
            sup_map = {f"{s['id']}. {s['name']} ({s['status']})": s['id'] for s in sups}
            sel = st.selectbox("공급사 선택", list(sup_map.keys()))
            new_st = st.selectbox("변경 상태", ["활성","휴면","거래중지"])
            if st.button("🔄 변경", use_container_width=True):
                conn = get_db()
                conn.execute("UPDATE suppliers SET status=? WHERE id=?", (new_st, sup_map[sel]))
                conn.commit(); conn.close()
                st.success("완료!"); st.rerun()

# ── 2. 자재 마스터 ──────────────────────────────────────
with tabs[1]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("자재 마스터 등록/수정")
        with st.form("mat_form", clear_on_submit=True):
            mat_code = st.text_input("자재코드 *")
            mat_name = st.text_input("자재명 *")
            col_a, col_b = st.columns(2)
            mat_type = col_a.selectbox("유형", ["원자재","반제품","완제품","소모품","포장재","서비스"])
            unit     = col_b.selectbox("단위", ["EA","KG","L","M","BOX","SET","TON","G","ML"])
            col_c, col_d = st.columns(2)
            category = col_c.text_input("카테고리")
            storage  = col_d.text_input("보관조건")
            col_e, col_f = st.columns(2)
            std_price= col_e.number_input("표준단가", min_value=0.0, format="%.2f")
            min_stock= col_f.number_input("안전재고", min_value=0, value=0)
            col_g, col_h = st.columns(2)
            lead_time_mat = col_g.number_input("표준납기(일)", min_value=0, value=7)
            mat_status = col_h.selectbox("상태", ["활성","비활성","단종"])
            note_mat = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 저장", use_container_width=True):
                if not mat_code or not mat_name:
                    st.error("코드, 자재명 필수")
                else:
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO materials
                            (material_code,material_name,material_type,unit,category,storage_condition,standard_price)
                            VALUES(?,?,?,?,?,?,?)
                            ON CONFLICT(material_code) DO UPDATE SET
                            material_name=excluded.material_name,material_type=excluded.material_type,
                            unit=excluded.unit,category=excluded.category,
                            storage_condition=excluded.storage_condition,
                            standard_price=excluded.standard_price""",
                            (mat_code,mat_name,mat_type,unit,category,storage,std_price))
                        conn.commit(); conn.close()
                        st.success("저장 완료!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("자재 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT m.material_code AS 자재코드, m.material_name AS 자재명,
                   m.material_type AS 유형, m.unit AS 단위,
                   m.category AS 카테고리, m.standard_price AS 표준단가,
                   COALESCE(i.stock_qty,0) AS 현재고,
                   COALESCE(pir.cnt,0) AS PIR수,
                   COALESCE(alt.cnt,0) AS 대체자재수
            FROM materials m
            LEFT JOIN inventory i ON m.material_code=i.item_code
            LEFT JOIN (SELECT material_id, COUNT(*) AS cnt FROM purchase_info_records WHERE status='유효' GROUP BY material_id) pir ON m.id=pir.material_id
            LEFT JOIN (SELECT material_id, COUNT(*) AS cnt FROM alternative_materials GROUP BY material_id) alt ON m.id=alt.material_id
            ORDER BY m.material_code""", conn)
        conn.close()
        if df.empty:
            st.info("자재 없음")
        else:
            search_m = st.text_input("🔍 자재 검색")
            if search_m:
                df = df[df['자재코드'].str.contains(search_m, na=False) | df['자재명'].str.contains(search_m, na=False)]
            st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (inventory) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_inventory = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM inventory ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('item_name','')}"
                        _row_opts_inventory[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_inventory:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_inventory = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_inventory.keys()),
                        key="_rbsel_inventory", label_visibility="collapsed"
                    )
                    _rb_id_inventory = _row_opts_inventory[_rb_sel_inventory]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_inventory"):
                        st.session_state[f"_edit_inventory"] = _rb_id_inventory
                        st.session_state[f"_del_inventory"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_inventory"):
                        st.session_state[f"_del_inventory"]  = _rb_id_inventory
                        st.session_state[f"_edit_inventory"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_inventory"):
                    _del_id_inventory = st.session_state[f"_del_inventory"]
                    st.warning(f"⚠️ ID **{_del_id_inventory}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_inventory"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM inventory WHERE id = ?", (_del_id_inventory,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_inventory"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_inventory"):
                        st.session_state[f"_del_inventory"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_inventory"):
                    _edit_id_inventory = st.session_state[f"_edit_inventory"]
                    try:
                        _cx_e = get_db()
                        _edit_row_inventory = dict(_cx_e.execute(
                            "SELECT * FROM inventory WHERE id=?", (_edit_id_inventory,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_inventory = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_inventory}", expanded=True):
                        if not _edit_row_inventory:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_inventory = [c for c in _edit_row_inventory if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_inventory)))
                            _ecols = st.columns(_ncols)
                            _new_vals_inventory = {}
                            for _i, _fc in enumerate(_edit_fields_inventory):
                                _cv = _edit_row_inventory[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_inventory[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_inventory}_{_fc}_inventory")
                                else:
                                    _new_vals_inventory[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_inventory}_{_fc}_inventory")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_inventory"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_inventory])
                                _set_params = list(_new_vals_inventory.values()) + [_edit_id_inventory]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE inventory SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_inventory"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_inventory"):
                                st.session_state[f"_edit_inventory"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (moving_avg_price) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_moving_avg_price = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM moving_avg_price ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('item_name','')}"
                        _row_opts_moving_avg_price[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_moving_avg_price:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_moving_avg_price = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_moving_avg_price.keys()),
                        key="_rbsel_moving_avg_price", label_visibility="collapsed"
                    )
                    _rb_id_moving_avg_price = _row_opts_moving_avg_price[_rb_sel_moving_avg_price]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_moving_avg_price"):
                        st.session_state[f"_edit_moving_avg_price"] = _rb_id_moving_avg_price
                        st.session_state[f"_del_moving_avg_price"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"]  = _rb_id_moving_avg_price
                        st.session_state[f"_edit_moving_avg_price"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_moving_avg_price"):
                    _del_id_moving_avg_price = st.session_state[f"_del_moving_avg_price"]
                    st.warning(f"⚠️ ID **{_del_id_moving_avg_price}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_moving_avg_price"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM moving_avg_price WHERE id = ?", (_del_id_moving_avg_price,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_moving_avg_price"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_moving_avg_price"):
                    _edit_id_moving_avg_price = st.session_state[f"_edit_moving_avg_price"]
                    try:
                        _cx_e = get_db()
                        _edit_row_moving_avg_price = dict(_cx_e.execute(
                            "SELECT * FROM moving_avg_price WHERE id=?", (_edit_id_moving_avg_price,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_moving_avg_price = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_moving_avg_price}", expanded=True):
                        if not _edit_row_moving_avg_price:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_moving_avg_price = [c for c in _edit_row_moving_avg_price if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_moving_avg_price)))
                            _ecols = st.columns(_ncols)
                            _new_vals_moving_avg_price = {}
                            for _i, _fc in enumerate(_edit_fields_moving_avg_price):
                                _cv = _edit_row_moving_avg_price[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_moving_avg_price[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                                else:
                                    _new_vals_moving_avg_price[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_moving_avg_price"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_moving_avg_price])
                                _set_params = list(_new_vals_moving_avg_price.values()) + [_edit_id_moving_avg_price]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE moving_avg_price SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_moving_avg_price"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_moving_avg_price"):
                                st.session_state[f"_edit_moving_avg_price"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (자재) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_materials = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 자재명 FROM materials ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('자재명','')}"
                        _row_opts_materials[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_materials:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_materials = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_materials.keys()),
                        key="_rbsel_materials", label_visibility="collapsed"
                    )
                    _rb_id_materials = _row_opts_materials[_rb_sel_materials]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_materials"):
                        st.session_state[f"_edit_materials"] = _rb_id_materials
                        st.session_state[f"_del_materials"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_materials"):
                        st.session_state[f"_del_materials"]  = _rb_id_materials
                        st.session_state[f"_edit_materials"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_materials"):
                    _del_id_materials = st.session_state[f"_del_materials"]
                    st.warning(f"⚠️ ID **{_del_id_materials}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_materials"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM materials WHERE id = ?", (_del_id_materials,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_materials"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_materials"):
                        st.session_state[f"_del_materials"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_materials"):
                    _edit_id_materials = st.session_state[f"_edit_materials"]
                    try:
                        _cx_e = get_db()
                        _edit_row_materials = dict(_cx_e.execute(
                            "SELECT * FROM materials WHERE id=?", (_edit_id_materials,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_materials = {}
                    with st.expander(f"✏️ 자재 수정 — ID {_edit_id_materials}", expanded=True):
                        if not _edit_row_materials:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_materials = [c for c in _edit_row_materials if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_materials)))
                            _ecols = st.columns(_ncols)
                            _new_vals_materials = {}
                            for _i, _fc in enumerate(_edit_fields_materials):
                                _cv = _edit_row_materials[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_materials[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_materials}_{_fc}_materials")
                                else:
                                    _new_vals_materials[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_materials}_{_fc}_materials")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_materials"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_materials])
                                _set_params = list(_new_vals_materials.values()) + [_edit_id_materials]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE materials SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_materials"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_materials"):
                                st.session_state[f"_edit_materials"] = None; st.rerun()

            col_m1, col_m2 = st.columns(2)
            col_m1.metric("총 자재수", len(df))
            if not df.empty:
                zero_stock_cnt = len(df[df['현재고'] == 0])
                col_m2.metric("⚠️ 재고 0 자재", zero_stock_cnt, delta_color="inverse")
        st.divider()
        st.subheader("공급사 연결 자재 조회")
        conn = get_db()
        sups_mat = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers WHERE status='활성'").fetchall()]
        conn.close()
        if sups_mat:
            sel_sup_mat = st.selectbox("공급사 선택", [s['name'] for s in sups_mat], key="sup_mat_view")
            conn = get_db()
            df_sup_mat = pd.read_sql_query("""
                SELECT p.item_name AS 품목, p.unit_price AS 협의단가, p.currency AS 통화,
                       p.lead_time_days AS 납기일수, p.min_order_qty AS 최소발주량,
                       p.valid_to AS 유효기간
                FROM purchase_info_records p JOIN suppliers s ON p.supplier_id=s.id
                WHERE s.name=?""", conn, params=[sel_sup_mat])
            conn.close()
            if df_sup_mat.empty:
                st.info("해당 공급사 PIR 없음")
            else:
                st.dataframe(df_sup_mat, use_container_width=True, hide_index=True)

# ── 3. 대체자재 ──────────────────────────────────────
with tabs[2]:
    st.subheader("🔗 대체자재 관리")
    st.caption("품절·단종 시 사용할 수 있는 대체 자재를 등록합니다")
    col_form, col_list = st.columns([1, 2])
    with col_form:
        conn = get_db()
        mats_alt = [dict(r) for r in conn.execute("SELECT id, material_code, material_name FROM materials").fetchall()]
        conn.close()
        mat_alt_opts = {f"{m['material_code']} - {m['material_name']}": m for m in mats_alt}
        with st.form("alt_form", clear_on_submit=True):
            st.markdown("**원자재 (대체 대상)**")
            main_sel = st.selectbox("원자재 *", list(mat_alt_opts.keys()) if mat_alt_opts else ["없음"])
            st.markdown("**대체 자재**")
            alt_from_master = st.checkbox("자재 마스터에서 선택", value=True)
            if alt_from_master:
                alt_sel = st.selectbox("대체 자재 *", list(mat_alt_opts.keys()) if mat_alt_opts else ["없음"])
                alt_code_in = mat_alt_opts[alt_sel]['material_code'] if mat_alt_opts and alt_sel in mat_alt_opts else ""
                alt_name_in = mat_alt_opts[alt_sel]['material_name'] if mat_alt_opts and alt_sel in mat_alt_opts else ""
            else:
                alt_code_in = st.text_input("대체 자재코드 *")
                alt_name_in = st.text_input("대체 자재명 *")
            col_a, col_b = st.columns(2)
            conv_factor = col_a.number_input("환산계수", min_value=0.01, value=1.0, format="%.3f",
                                              help="원자재 1단위 = 대체자재 몇 단위")
            priority    = col_b.number_input("우선순위", min_value=1, value=1)
            note_alt = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not mat_alt_opts or not alt_code_in:
                    st.error("자재 정보 필수")
                else:
                    main_data = mat_alt_opts.get(main_sel)
                    main_id = main_data['id'] if main_data else None
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO alternative_materials
                            (material_id,alt_material_code,alt_material_name,conversion_factor,priority,note)
                            VALUES(?,?,?,?,?,?)""",
                            (main_id, alt_code_in, alt_name_in, conv_factor, priority, note_alt))
                        conn.commit(); conn.close()
                        st.success("대체자재 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("대체자재 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT m.material_code AS 원자재코드, m.material_name AS 원자재명,
                   a.alt_material_code AS 대체코드, a.alt_material_name AS 대체자재명,
                   a.conversion_factor AS 환산계수, a.priority AS 우선순위, a.note AS 비고
            FROM alternative_materials a LEFT JOIN materials m ON a.material_id=m.id
            ORDER BY m.material_code, a.priority""", conn)
        conn.close()
        if df.empty:
            st.info("등록된 대체자재 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (moving_avg_price) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_moving_avg_price = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM moving_avg_price ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('item_name','')}"
                        _row_opts_moving_avg_price[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_moving_avg_price:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_moving_avg_price = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_moving_avg_price.keys()),
                        key="_rbsel_moving_avg_price", label_visibility="collapsed"
                    )
                    _rb_id_moving_avg_price = _row_opts_moving_avg_price[_rb_sel_moving_avg_price]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_moving_avg_price"):
                        st.session_state[f"_edit_moving_avg_price"] = _rb_id_moving_avg_price
                        st.session_state[f"_del_moving_avg_price"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"]  = _rb_id_moving_avg_price
                        st.session_state[f"_edit_moving_avg_price"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_moving_avg_price"):
                    _del_id_moving_avg_price = st.session_state[f"_del_moving_avg_price"]
                    st.warning(f"⚠️ ID **{_del_id_moving_avg_price}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_moving_avg_price"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM moving_avg_price WHERE id = ?", (_del_id_moving_avg_price,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_moving_avg_price"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_moving_avg_price"):
                    _edit_id_moving_avg_price = st.session_state[f"_edit_moving_avg_price"]
                    try:
                        _cx_e = get_db()
                        _edit_row_moving_avg_price = dict(_cx_e.execute(
                            "SELECT * FROM moving_avg_price WHERE id=?", (_edit_id_moving_avg_price,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_moving_avg_price = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_moving_avg_price}", expanded=True):
                        if not _edit_row_moving_avg_price:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_moving_avg_price = [c for c in _edit_row_moving_avg_price if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_moving_avg_price)))
                            _ecols = st.columns(_ncols)
                            _new_vals_moving_avg_price = {}
                            for _i, _fc in enumerate(_edit_fields_moving_avg_price):
                                _cv = _edit_row_moving_avg_price[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_moving_avg_price[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                                else:
                                    _new_vals_moving_avg_price[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_moving_avg_price"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_moving_avg_price])
                                _set_params = list(_new_vals_moving_avg_price.values()) + [_edit_id_moving_avg_price]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE moving_avg_price SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_moving_avg_price"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_moving_avg_price"):
                                st.session_state[f"_edit_moving_avg_price"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (대체자재) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_alternative_materials = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 자재명 FROM alternative_materials ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('자재명','')}"
                        _row_opts_alternative_materials[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_alternative_materials:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_alternative_materials = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_alternative_materials.keys()),
                        key="_rbsel_alternative_materials", label_visibility="collapsed"
                    )
                    _rb_id_alternative_materials = _row_opts_alternative_materials[_rb_sel_alternative_materials]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_alternative_materials"):
                        st.session_state[f"_edit_alternative_materials"] = _rb_id_alternative_materials
                        st.session_state[f"_del_alternative_materials"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_alternative_materials"):
                        st.session_state[f"_del_alternative_materials"]  = _rb_id_alternative_materials
                        st.session_state[f"_edit_alternative_materials"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_alternative_materials"):
                    _del_id_alternative_materials = st.session_state[f"_del_alternative_materials"]
                    st.warning(f"⚠️ ID **{_del_id_alternative_materials}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_alternative_materials"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM alternative_materials WHERE id = ?", (_del_id_alternative_materials,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_alternative_materials"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_alternative_materials"):
                        st.session_state[f"_del_alternative_materials"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_alternative_materials"):
                    _edit_id_alternative_materials = st.session_state[f"_edit_alternative_materials"]
                    try:
                        _cx_e = get_db()
                        _edit_row_alternative_materials = dict(_cx_e.execute(
                            "SELECT * FROM alternative_materials WHERE id=?", (_edit_id_alternative_materials,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_alternative_materials = {}
                    with st.expander(f"✏️ 대체자재 수정 — ID {_edit_id_alternative_materials}", expanded=True):
                        if not _edit_row_alternative_materials:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_alternative_materials = [c for c in _edit_row_alternative_materials if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_alternative_materials)))
                            _ecols = st.columns(_ncols)
                            _new_vals_alternative_materials = {}
                            for _i, _fc in enumerate(_edit_fields_alternative_materials):
                                _cv = _edit_row_alternative_materials[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_alternative_materials[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_alternative_materials}_{_fc}_alternative_materials")
                                else:
                                    _new_vals_alternative_materials[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_alternative_materials}_{_fc}_alternative_materials")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_alternative_materials"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_alternative_materials])
                                _set_params = list(_new_vals_alternative_materials.values()) + [_edit_id_alternative_materials]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE alternative_materials SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_alternative_materials"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_alternative_materials"):
                                st.session_state[f"_edit_alternative_materials"] = None; st.rerun()

        st.divider()
        st.subheader("💡 품절 대체자재 즉시 조회")
        conn = get_db()
        zero_mats = [dict(r) for r in conn.execute("""
            SELECT m.id, m.material_code, m.material_name
            FROM materials m LEFT JOIN inventory i ON m.material_code=i.item_code
            WHERE COALESCE(i.stock_qty,0)=0""").fetchall()]
        conn.close()
        if zero_mats:
            zs_map = {f"{z['material_code']} - {z['material_name']}": z['id'] for z in zero_mats}
            sel_zs = st.selectbox("재고 0 자재", list(zs_map.keys()))
            conn = get_db()
            df_alt = pd.read_sql_query("""
                SELECT alt_material_code AS 대체코드, alt_material_name AS 대체자재,
                       conversion_factor AS 환산계수, priority AS 우선순위, note AS 비고
                FROM alternative_materials WHERE material_id=? ORDER BY priority""",
                conn, params=[zs_map[sel_zs]])
            conn.close()
            if df_alt.empty:
                st.warning("등록된 대체자재 없음")
            else:
                st.success(f"✅ {len(df_alt)}개 대체자재 사용 가능")
                st.dataframe(df_alt, use_container_width=True, hide_index=True)
        else:
            st.success("✅ 재고 0 자재 없음")

# ── 4. PIR ──────────────────────────────────────
with tabs[3]:
    st.subheader("💡 구매정보 레코드 (PIR)")
    st.caption("공급사 + 자재 조합별 협의가격 — PO 등록 시 단가 자동 참조")
    col_form, col_list = st.columns([1, 2])
    with col_form:
        conn = get_db()
        sups_p = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers WHERE status='활성'").fetchall()]
        mats_p = [dict(r) for r in conn.execute("SELECT id, material_code, material_name, unit FROM materials").fetchall()]
        conn.close()
        sup_p_opts = {s['name']: s['id'] for s in sups_p}
        mat_p_opts = {"직접입력": None}
        mat_p_opts.update({f"{m['material_code']} - {m['material_name']}": m for m in mats_p})
        with st.form("pir_form", clear_on_submit=True):
            sup_p_sel = st.selectbox("공급사 *", list(sup_p_opts.keys()) if sup_p_opts else ["없음"])
            mat_p_sel = st.selectbox("자재", list(mat_p_opts.keys()))
            item_p    = st.text_input("품목명 (직접입력 시)")
            col_a, col_b = st.columns(2)
            unit_price_p = col_a.number_input("협의단가 *", min_value=0.0, format="%.2f")
            currency_p   = col_b.selectbox("통화", ["KRW","USD","EUR","JPY","CNY"])
            col_c, col_d = st.columns(2)
            min_qty_p    = col_c.number_input("최소발주량", min_value=1, value=1)
            lead_time_p  = col_d.number_input("납기일수", min_value=0, value=7)
            col_e, col_f = st.columns(2)
            disc_p       = col_e.number_input("할인율(%)", min_value=0.0, max_value=100.0, format="%.1f")
            price_unit_p = col_f.number_input("가격단위", min_value=1, value=1)
            col_g, col_h = st.columns(2)
            valid_from_p = col_g.date_input("유효시작일")
            valid_to_p   = col_h.date_input("유효종료일")
            memo_p       = st.text_input("메모")
            status_p     = st.selectbox("상태", ["유효","만료","검토중"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not sup_p_opts or unit_price_p == 0:
                    st.error("공급사, 단가 필수")
                else:
                    mat_data = mat_p_opts.get(mat_p_sel)
                    final_name = item_p if not mat_data else mat_data['material_name']
                    mat_id_val = mat_data['id'] if mat_data else None
                    try:
                        pnum = gen_number("PIR")
                        conn = get_db()
                        conn.execute("""INSERT INTO purchase_info_records
                            (pir_number,supplier_id,material_id,item_name,unit_price,currency,
                             min_order_qty,lead_time_days,discount_rate,price_unit,
                             valid_from,valid_to,memo,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (pnum,sup_p_opts.get(sup_p_sel),mat_id_val,final_name,
                             unit_price_p,currency_p,min_qty_p,lead_time_p,
                             disc_p,price_unit_p,str(valid_from_p),str(valid_to_p),memo_p,status_p))
                        conn.commit(); conn.close()
                        st.success(f"PIR {pnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("PIR 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT p.pir_number AS PIR번호, s.name AS 공급사,
                   p.item_name AS 품목, p.unit_price AS 단가, p.currency AS 통화,
                   p.discount_rate AS 할인율,
                   ROUND(p.unit_price*(1-p.discount_rate/100),2) AS 실단가,
                   p.min_order_qty AS 최소발주량, p.lead_time_days AS 납기일수,
                   p.valid_from AS 유효시작, p.valid_to AS 유효종료, p.status AS 상태
            FROM purchase_info_records p LEFT JOIN suppliers s ON p.supplier_id=s.id
            ORDER BY p.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("PIR 없음")
        else:
            search_p = st.text_input("🔍 검색")
            if search_p:
                df = df[df['품목'].str.contains(search_p, na=False) | df['공급사'].str.contains(search_p, na=False)]
            exp_soon_pir = df[(df['상태']=='유효') & (df['유효종료'] <= (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d"))]
            if not exp_soon_pir.empty:
                st.warning(f"⚠️ 30일 내 만료 PIR: {len(exp_soon_pir)}건")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (moving_avg_price) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_moving_avg_price = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM moving_avg_price ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('item_name','')}"
                        _row_opts_moving_avg_price[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_moving_avg_price:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_moving_avg_price = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_moving_avg_price.keys()),
                        key="_rbsel_moving_avg_price", label_visibility="collapsed"
                    )
                    _rb_id_moving_avg_price = _row_opts_moving_avg_price[_rb_sel_moving_avg_price]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_moving_avg_price"):
                        st.session_state[f"_edit_moving_avg_price"] = _rb_id_moving_avg_price
                        st.session_state[f"_del_moving_avg_price"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"]  = _rb_id_moving_avg_price
                        st.session_state[f"_edit_moving_avg_price"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_moving_avg_price"):
                    _del_id_moving_avg_price = st.session_state[f"_del_moving_avg_price"]
                    st.warning(f"⚠️ ID **{_del_id_moving_avg_price}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_moving_avg_price"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM moving_avg_price WHERE id = ?", (_del_id_moving_avg_price,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_moving_avg_price"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_moving_avg_price"):
                    _edit_id_moving_avg_price = st.session_state[f"_edit_moving_avg_price"]
                    try:
                        _cx_e = get_db()
                        _edit_row_moving_avg_price = dict(_cx_e.execute(
                            "SELECT * FROM moving_avg_price WHERE id=?", (_edit_id_moving_avg_price,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_moving_avg_price = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_moving_avg_price}", expanded=True):
                        if not _edit_row_moving_avg_price:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_moving_avg_price = [c for c in _edit_row_moving_avg_price if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_moving_avg_price)))
                            _ecols = st.columns(_ncols)
                            _new_vals_moving_avg_price = {}
                            for _i, _fc in enumerate(_edit_fields_moving_avg_price):
                                _cv = _edit_row_moving_avg_price[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_moving_avg_price[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                                else:
                                    _new_vals_moving_avg_price[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_moving_avg_price"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_moving_avg_price])
                                _set_params = list(_new_vals_moving_avg_price.values()) + [_edit_id_moving_avg_price]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE moving_avg_price SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_moving_avg_price"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_moving_avg_price"):
                                st.session_state[f"_edit_moving_avg_price"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (PIR) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_purchase_info_records = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목 FROM purchase_info_records ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목','')}"
                        _row_opts_purchase_info_records[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_purchase_info_records:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_purchase_info_records = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_purchase_info_records.keys()),
                        key="_rbsel_purchase_info_records", label_visibility="collapsed"
                    )
                    _rb_id_purchase_info_records = _row_opts_purchase_info_records[_rb_sel_purchase_info_records]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_purchase_info_records"):
                        st.session_state[f"_edit_purchase_info_records"] = _rb_id_purchase_info_records
                        st.session_state[f"_del_purchase_info_records"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_purchase_info_records"):
                        st.session_state[f"_del_purchase_info_records"]  = _rb_id_purchase_info_records
                        st.session_state[f"_edit_purchase_info_records"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_purchase_info_records"):
                    _del_id_purchase_info_records = st.session_state[f"_del_purchase_info_records"]
                    st.warning(f"⚠️ ID **{_del_id_purchase_info_records}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_purchase_info_records"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM purchase_info_records WHERE id = ?", (_del_id_purchase_info_records,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_purchase_info_records"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_purchase_info_records"):
                        st.session_state[f"_del_purchase_info_records"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_purchase_info_records"):
                    _edit_id_purchase_info_records = st.session_state[f"_edit_purchase_info_records"]
                    try:
                        _cx_e = get_db()
                        _edit_row_purchase_info_records = dict(_cx_e.execute(
                            "SELECT * FROM purchase_info_records WHERE id=?", (_edit_id_purchase_info_records,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_purchase_info_records = {}
                    with st.expander(f"✏️ PIR 수정 — ID {_edit_id_purchase_info_records}", expanded=True):
                        if not _edit_row_purchase_info_records:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_purchase_info_records = [c for c in _edit_row_purchase_info_records if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_purchase_info_records)))
                            _ecols = st.columns(_ncols)
                            _new_vals_purchase_info_records = {}
                            for _i, _fc in enumerate(_edit_fields_purchase_info_records):
                                _cv = _edit_row_purchase_info_records[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_purchase_info_records[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_purchase_info_records}_{_fc}_purchase_info_records")
                                else:
                                    _new_vals_purchase_info_records[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_purchase_info_records}_{_fc}_purchase_info_records")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_purchase_info_records"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_purchase_info_records])
                                _set_params = list(_new_vals_purchase_info_records.values()) + [_edit_id_purchase_info_records]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE purchase_info_records SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_purchase_info_records"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_purchase_info_records"):
                                st.session_state[f"_edit_purchase_info_records"] = None; st.rerun()

        st.divider()
        st.subheader("💡 자재별 최저단가 공급사")
        conn = get_db()
        mats_chk = [dict(r) for r in conn.execute("SELECT material_name FROM materials").fetchall()]
        conn.close()
        if mats_chk:
            chk_item = st.selectbox("자재 선택", [m['material_name'] for m in mats_chk])
            conn = get_db()
            pir_res = pd.read_sql_query("""
                SELECT s.name AS 공급사, p.unit_price AS 단가, p.currency AS 통화,
                       p.discount_rate AS 할인율,
                       ROUND(p.unit_price*(1-p.discount_rate/100),2) AS 실단가,
                       p.lead_time_days AS 납기일수, p.min_order_qty AS 최소발주량, p.valid_to AS 유효기간
                FROM purchase_info_records p LEFT JOIN suppliers s ON p.supplier_id=s.id
                WHERE p.item_name=? AND p.status='유효'
                ORDER BY p.unit_price*(1-p.discount_rate/100)""", conn, params=[chk_item])
            conn.close()
            if pir_res.empty:
                st.info("해당 자재 PIR 없음")
            else:
                st.success(f"✅ {len(pir_res)}개 공급사 (단가 낮은 순)")
                st.dataframe(pir_res, use_container_width=True, hide_index=True)
                best = pir_res.iloc[0]
                st.info(f"🏆 최저가: **{best['공급사']}** — 실단가 {best['실단가']:,.2f} {best['통화']} (납기 {best['납기일수']}일)")


# ── 5. 구매요청 PR ──────────────────────────────────────
with tabs[4]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("구매요청서(PR) 등록")
        conn = get_db()
        mats = [dict(r) for r in conn.execute("SELECT id, material_code, material_name FROM materials").fetchall()]
        conn.close()
        mat_opts = {"직접입력": None}
        mat_opts.update({f"{m['material_code']} - {m['material_name']}": m['id'] for m in mats})
        with st.form("pr_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            requester = col_a.text_input("요청자 *")
            dept      = col_b.text_input("부서")
            mat_sel   = st.selectbox("자재 선택", list(mat_opts.keys()))
            item_name = st.text_input("품목명 (직접입력 시)")
            col_c, col_d = st.columns(2)
            qty       = col_c.number_input("요청수량 *", min_value=1, value=1)
            req_date  = col_d.date_input("필요일")
            col_e, col_f = st.columns(2)
            priority_pr = col_e.selectbox("긴급도", ["일반","긴급","초긴급"])
            est_price   = col_f.number_input("예상단가", min_value=0.0, format="%.0f")
            reason    = st.text_area("요청사유", height=70)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not requester:
                    st.error("요청자 필수")
                else:
                    final_name = item_name if mat_sel == "직접입력" else mat_sel.split(" - ")[1]
                    try:
                        pr_num = gen_number("PR")
                        conn = get_db()
                        conn.execute("""INSERT INTO purchase_requests
                            (pr_number,requester,department,material_id,item_name,quantity,required_date,reason)
                            VALUES(?,?,?,?,?,?,?,?)""",
                            (pr_num,requester,dept,mat_opts.get(mat_sel),
                             final_name,qty,str(req_date),reason))
                        conn.commit(); conn.close()
                        st.success(f"PR {pr_num} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("구매요청 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT pr_number AS PR번호, requester AS 요청자, department AS 부서,
                   item_name AS 품목, quantity AS 수량, required_date AS 필요일,
                   status AS 상태, approved_by AS 승인자, created_at AS 등록일
            FROM purchase_requests ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("구매요청 없음")
        else:
            tab_pr1, tab_pr2 = st.tabs(["전체", "승인대기"])
            with tab_pr1:
                st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (moving_avg_price) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_moving_avg_price = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM moving_avg_price ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('item_name','')}"
                        _row_opts_moving_avg_price[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_moving_avg_price:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_moving_avg_price = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_moving_avg_price.keys()),
                        key="_rbsel_moving_avg_price", label_visibility="collapsed"
                    )
                    _rb_id_moving_avg_price = _row_opts_moving_avg_price[_rb_sel_moving_avg_price]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_moving_avg_price"):
                        st.session_state[f"_edit_moving_avg_price"] = _rb_id_moving_avg_price
                        st.session_state[f"_del_moving_avg_price"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"]  = _rb_id_moving_avg_price
                        st.session_state[f"_edit_moving_avg_price"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_moving_avg_price"):
                    _del_id_moving_avg_price = st.session_state[f"_del_moving_avg_price"]
                    st.warning(f"⚠️ ID **{_del_id_moving_avg_price}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_moving_avg_price"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM moving_avg_price WHERE id = ?", (_del_id_moving_avg_price,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_moving_avg_price"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_moving_avg_price"):
                    _edit_id_moving_avg_price = st.session_state[f"_edit_moving_avg_price"]
                    try:
                        _cx_e = get_db()
                        _edit_row_moving_avg_price = dict(_cx_e.execute(
                            "SELECT * FROM moving_avg_price WHERE id=?", (_edit_id_moving_avg_price,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_moving_avg_price = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_moving_avg_price}", expanded=True):
                        if not _edit_row_moving_avg_price:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_moving_avg_price = [c for c in _edit_row_moving_avg_price if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_moving_avg_price)))
                            _ecols = st.columns(_ncols)
                            _new_vals_moving_avg_price = {}
                            for _i, _fc in enumerate(_edit_fields_moving_avg_price):
                                _cv = _edit_row_moving_avg_price[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_moving_avg_price[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                                else:
                                    _new_vals_moving_avg_price[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_moving_avg_price"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_moving_avg_price])
                                _set_params = list(_new_vals_moving_avg_price.values()) + [_edit_id_moving_avg_price]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE moving_avg_price SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_moving_avg_price"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_moving_avg_price"):
                                st.session_state[f"_edit_moving_avg_price"] = None; st.rerun()


    # ── 행 수정/삭제 버튼 (PR) ──────────────────────────
    if not df.empty if hasattr(df, 'empty') else df is not None:
        _row_opts_purchase_requests = {}
        try:
            _cx_opt = get_db()
            _opt_rs = [dict(r) for r in _cx_opt.execute(
                "SELECT id, 품목명 FROM purchase_requests ORDER BY id DESC LIMIT 300"
            ).fetchall()]
            _cx_opt.close()
            for _r in _opt_rs:
                _k = f"{_r['id']} | {_r.get('품목명','')}"
                _row_opts_purchase_requests[_k] = _r['id']
        except Exception:
            pass

        if _row_opts_purchase_requests:
            _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
            _rb_sel_purchase_requests = _rb_sel_col.selectbox(
                "행 선택", list(_row_opts_purchase_requests.keys()),
                key="_rbsel_purchase_requests", label_visibility="collapsed"
            )
            _rb_id_purchase_requests = _row_opts_purchase_requests[_rb_sel_purchase_requests]

            if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_purchase_requests"):
                st.session_state[f"_edit_purchase_requests"] = _rb_id_purchase_requests
                st.session_state[f"_del_purchase_requests"]  = None

            if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_purchase_requests"):
                st.session_state[f"_del_purchase_requests"]  = _rb_id_purchase_requests
                st.session_state[f"_edit_purchase_requests"] = None

        # ── 삭제 확인 ──────────────────────────────────────────
        if st.session_state.get(f"_del_purchase_requests"):
            _del_id_purchase_requests = st.session_state[f"_del_purchase_requests"]
            st.warning(f"⚠️ ID **{_del_id_purchase_requests}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
            _dc1, _dc2 = st.columns(2)
            if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_purchase_requests"):
                _cx_d = get_db()
                _cx_d.execute("DELETE FROM purchase_requests WHERE id = ?", (_del_id_purchase_requests,))
                _cx_d.commit(); _cx_d.close()
                st.session_state[f"_del_purchase_requests"] = None
                st.success("✅ 삭제 완료!"); st.rerun()
            if _dc2.button("취소", use_container_width=True, key="_delcancel_purchase_requests"):
                st.session_state[f"_del_purchase_requests"] = None; st.rerun()

        # ── 수정 인라인 폼 ─────────────────────────────────────
        if st.session_state.get(f"_edit_purchase_requests"):
            _edit_id_purchase_requests = st.session_state[f"_edit_purchase_requests"]
            try:
                _cx_e = get_db()
                _edit_row_purchase_requests = dict(_cx_e.execute(
                    "SELECT * FROM purchase_requests WHERE id=?", (_edit_id_purchase_requests,)
                ).fetchone() or {})
                _cx_e.close()
            except Exception:
                _edit_row_purchase_requests = {}
            with st.expander(f"✏️ PR 수정 — ID {_edit_id_purchase_requests}", expanded=True):
                if not _edit_row_purchase_requests:
                    st.warning("데이터를 불러올 수 없습니다.")
                else:
                    _skip_cols = {'id','created_at','updated_at'}
                    _edit_fields_purchase_requests = [c for c in _edit_row_purchase_requests if c not in _skip_cols]
                    _ncols = min(3, max(1, len(_edit_fields_purchase_requests)))
                    _ecols = st.columns(_ncols)
                    _new_vals_purchase_requests = {}
                    for _i, _fc in enumerate(_edit_fields_purchase_requests):
                        _cv = _edit_row_purchase_requests[_fc]
                        _ec = _ecols[_i % _ncols]
                        if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                            _new_vals_purchase_requests[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_purchase_requests}_{_fc}_purchase_requests")
                        else:
                            _new_vals_purchase_requests[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_purchase_requests}_{_fc}_purchase_requests")
                    _s1, _s2 = st.columns(2)
                    if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_purchase_requests"):
                        _set_sql = ", ".join([f"{c}=?" for c in _new_vals_purchase_requests])
                        _set_params = list(_new_vals_purchase_requests.values()) + [_edit_id_purchase_requests]
                        _cx_s = get_db()
                        _cx_s.execute(f"UPDATE purchase_requests SET {_set_sql} WHERE id=?", _set_params)
                        _cx_s.commit(); _cx_s.close()
                        st.session_state[f"_edit_purchase_requests"] = None
                        st.success("✅ 수정 저장 완료!"); st.rerun()
                    if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_purchase_requests"):
                        st.session_state[f"_edit_purchase_requests"] = None; st.rerun()

            with tab_pr2:
                st.dataframe(df[df['상태']=='승인대기'], use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("✅ PR 승인/반려")
        conn = get_db()
        prs = [dict(r) for r in conn.execute(
            "SELECT id, pr_number, item_name, quantity FROM purchase_requests WHERE status='승인대기'").fetchall()]
        conn.close()
        if not prs:
            st.info("승인 대기 PR 없음")
        else:
            pr_map = {f"{p['pr_number']} - {p['item_name']} ({p['quantity']}개)": p['id'] for p in prs}
            sel_pr = st.selectbox("PR 선택", list(pr_map.keys()))
            col_a, col_b, col_c = st.columns(3)
            approver = col_a.text_input("승인자명")
            new_st   = col_b.selectbox("처리", ["승인","반려"])
            comment_pr = col_c.text_input("코멘트")
            if st.button("처리 확정", use_container_width=True, key="pr_approve"):
                conn = get_db()
                conn.execute("""UPDATE purchase_requests SET status=?, approved_by=?,
                    approved_at=datetime('now','localtime') WHERE id=?""",
                    (new_st, approver, pr_map[sel_pr]))
                conn.commit(); conn.close()
                st.success(f"{new_st} 처리!"); st.rerun()

# ── 6. 구매품의서 ──────────────────────────────────────
with tabs[5]:
    st.subheader("📋 구매 품의서 (다단계 결재)")
    st.caption("PR 기반 정식 구매 품의 — 팀장 → 부장 → 임원 순차 결재")
    col_form, col_list = st.columns([1, 2])
    with col_form:
        conn = get_db()
        prs_ap = [dict(r) for r in conn.execute(
            "SELECT id, pr_number, item_name, quantity FROM purchase_requests WHERE status='승인'").fetchall()]
        conn.close()
        pr_ap_opts = {"PR 없이 직접 작성": None}
        pr_ap_opts.update({f"{p['pr_number']} - {p['item_name']}": p for p in prs_ap})
        with st.form("approval_form", clear_on_submit=True):
            pr_ap_sel = st.selectbox("연결 PR", list(pr_ap_opts.keys()))
            pr_ap_data = pr_ap_opts.get(pr_ap_sel)
            ap_title  = st.text_input("품의 제목 *")
            col_a, col_b = st.columns(2)
            ap_requester = col_a.text_input("기안자 *")
            ap_dept    = col_b.text_input("부서")
            ap_item    = st.text_input("구매 품목 *",
                value=pr_ap_data['item_name'] if pr_ap_data else "")
            col_c, col_d = st.columns(2)
            ap_qty     = col_c.number_input("수량 *", min_value=1,
                value=int(pr_ap_data['quantity']) if pr_ap_data else 1)
            ap_est_amt = col_d.number_input("예상금액", min_value=0.0, format="%.0f")
            ap_contract= st.selectbox("계약방식", ["경쟁입찰","수의계약","단가계약","긴급구매"])
            ap_sole = ""
            if ap_contract == "수의계약":
                ap_sole = st.text_area("수의계약 사유 (필수)", height=60)
            ap_reason  = st.text_area("구매 사유", height=70)
            st.markdown("**결재선 설정**")
            col_s1, col_s2, col_s3 = st.columns(3)
            s1_name = col_s1.text_input("1차 결재자 (팀장)")
            s2_name = col_s2.text_input("2차 결재자 (부장)")
            s3_name = col_s3.text_input("3차 결재자 (임원)")
            if st.form_submit_button("✅ 품의 상신", use_container_width=True):
                if not ap_title or not ap_requester or not ap_item:
                    st.error("제목, 기안자, 품목 필수")
                elif ap_contract == "수의계약" and not ap_sole:
                    st.error("수의계약 사유 필수")
                else:
                    try:
                        ap_num = gen_number("AP")
                        conn = get_db()
                        conn.execute("""INSERT INTO purchase_approvals
                            (approval_number,pr_id,title,requester,department,item_name,quantity,
                             estimated_amount,reason,contract_type,sole_source_reason,
                             step1_approver,step2_approver,step3_approver)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (ap_num, pr_ap_data['id'] if pr_ap_data else None,
                             ap_title, ap_requester, ap_dept, ap_item, ap_qty,
                             ap_est_amt, ap_reason, ap_contract, ap_sole,
                             s1_name, s2_name, s3_name))
                        conn.commit(); conn.close()
                        st.success(f"품의서 {ap_num} 상신 완료!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("품의서 목록")
        conn = get_db()
        df_ap = pd.read_sql_query("""
            SELECT approval_number AS 품의번호, title AS 제목, requester AS 기안자,
                   department AS 부서, item_name AS 품목, quantity AS 수량,
                   estimated_amount AS 예상금액, contract_type AS 계약방식,
                   step1_status AS 결재1차, step2_status AS 결재2차, step3_status AS 결재3차,
                   final_status AS 최종, created_at AS 상신일
            FROM purchase_approvals ORDER BY id DESC""", conn)
        conn.close()
        if df_ap.empty:
            st.info("품의서 없음")
        else:
            def ap_color(row):
                if row['최종'] == '승인': return ['background-color:#d1fae5']*len(row)
                if row['최종'] == '반려': return ['background-color:#fee2e2']*len(row)
                return ['']*len(row)
            st.dataframe(df_ap.style.apply(ap_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (품의서) ──────────────────────────
            if not df_ap.empty if hasattr(df_ap, 'empty') else df_ap is not None:
                _row_opts_purchase_approvals = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM purchase_approvals ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_purchase_approvals[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_purchase_approvals:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_purchase_approvals = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_purchase_approvals.keys()),
                        key="_rbsel_purchase_approvals", label_visibility="collapsed"
                    )
                    _rb_id_purchase_approvals = _row_opts_purchase_approvals[_rb_sel_purchase_approvals]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_purchase_approvals"):
                        st.session_state[f"_edit_purchase_approvals"] = _rb_id_purchase_approvals
                        st.session_state[f"_del_purchase_approvals"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_purchase_approvals"):
                        st.session_state[f"_del_purchase_approvals"]  = _rb_id_purchase_approvals
                        st.session_state[f"_edit_purchase_approvals"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_purchase_approvals"):
                    _del_id_purchase_approvals = st.session_state[f"_del_purchase_approvals"]
                    st.warning(f"⚠️ ID **{_del_id_purchase_approvals}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_purchase_approvals"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM purchase_approvals WHERE id = ?", (_del_id_purchase_approvals,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_purchase_approvals"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_purchase_approvals"):
                        st.session_state[f"_del_purchase_approvals"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_purchase_approvals"):
                    _edit_id_purchase_approvals = st.session_state[f"_edit_purchase_approvals"]
                    try:
                        _cx_e = get_db()
                        _edit_row_purchase_approvals = dict(_cx_e.execute(
                            "SELECT * FROM purchase_approvals WHERE id=?", (_edit_id_purchase_approvals,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_purchase_approvals = {}
                    with st.expander(f"✏️ 품의서 수정 — ID {_edit_id_purchase_approvals}", expanded=True):
                        if not _edit_row_purchase_approvals:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_purchase_approvals = [c for c in _edit_row_purchase_approvals if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_purchase_approvals)))
                            _ecols = st.columns(_ncols)
                            _new_vals_purchase_approvals = {}
                            for _i, _fc in enumerate(_edit_fields_purchase_approvals):
                                _cv = _edit_row_purchase_approvals[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_purchase_approvals[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_purchase_approvals}_{_fc}_purchase_approvals")
                                else:
                                    _new_vals_purchase_approvals[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_purchase_approvals}_{_fc}_purchase_approvals")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_purchase_approvals"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_purchase_approvals])
                                _set_params = list(_new_vals_purchase_approvals.values()) + [_edit_id_purchase_approvals]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE purchase_approvals SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_purchase_approvals"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_purchase_approvals"):
                                st.session_state[f"_edit_purchase_approvals"] = None; st.rerun()

        st.divider()
        st.subheader("⚡ 결재 처리")
        conn = get_db()
        pending_ap = [dict(r) for r in conn.execute("""
            SELECT id, approval_number, title, item_name,
                   step1_approver, step1_status,
                   step2_approver, step2_status,
                   step3_approver, step3_status
            FROM purchase_approvals WHERE final_status='검토중'""").fetchall()]
        conn.close()
        if not pending_ap:
            st.success("✅ 결재 대기 품의서 없음")
        else:
            ap_map2 = {f"{p['approval_number']} - {p['title']}": p for p in pending_ap}
            sel_ap = st.selectbox("품의서 선택", list(ap_map2.keys()))
            ap_obj = ap_map2[sel_ap]
            if ap_obj['step1_status'] == '대기':
                step_label = f"1차 결재 ({ap_obj['step1_approver'] or '미설정'})"; step_key = 1
            elif ap_obj['step2_status'] == '대기' and ap_obj['step1_status'] == '승인':
                step_label = f"2차 결재 ({ap_obj['step2_approver'] or '미설정'})"; step_key = 2
            elif ap_obj['step3_status'] == '대기' and ap_obj['step2_status'] == '승인':
                step_label = f"3차 결재 ({ap_obj['step3_approver'] or '미설정'})"; step_key = 3
            else:
                step_label = "결재 완료"; step_key = 0
            if step_key > 0:
                st.info(f"현재 단계: **{step_label}**")
                col_a2, col_b2 = st.columns(2)
                ap_action = col_a2.selectbox("결재 처리", ["승인","반려"])
                ap_comment = col_b2.text_input("결재 의견")
                if st.button("✅ 결재 처리", use_container_width=True, key="ap_process"):
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn = get_db()
                    if step_key == 1:
                        conn.execute("UPDATE purchase_approvals SET step1_status=?,step1_comment=?,step1_at=? WHERE id=?",
                                     (ap_action, ap_comment, now_str, ap_obj['id']))
                        if ap_action == '반려':
                            conn.execute("UPDATE purchase_approvals SET final_status='반려' WHERE id=?", (ap_obj['id'],))
                        elif not ap_obj['step2_approver']:
                            conn.execute("UPDATE purchase_approvals SET final_status='승인' WHERE id=?", (ap_obj['id'],))
                    elif step_key == 2:
                        conn.execute("UPDATE purchase_approvals SET step2_status=?,step2_comment=?,step2_at=? WHERE id=?",
                                     (ap_action, ap_comment, now_str, ap_obj['id']))
                        if ap_action == '반려':
                            conn.execute("UPDATE purchase_approvals SET final_status='반려' WHERE id=?", (ap_obj['id'],))
                        elif not ap_obj['step3_approver']:
                            conn.execute("UPDATE purchase_approvals SET final_status='승인' WHERE id=?", (ap_obj['id'],))
                    elif step_key == 3:
                        conn.execute("UPDATE purchase_approvals SET step3_status=?,step3_comment=?,step3_at=? WHERE id=?",
                                     (ap_action, ap_comment, now_str, ap_obj['id']))
                        conn.execute("UPDATE purchase_approvals SET final_status=? WHERE id=?",
                                     ('승인' if ap_action=='승인' else '반려', ap_obj['id']))
                    conn.commit(); conn.close()
                    st.success(f"{ap_action} 처리 완료!"); st.rerun()


# ── 7. 견적 RFQ ──────────────────────────────────────
with tabs[6]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("견적서(RFQ) 등록")
        conn = get_db()
        sups3 = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers WHERE status='활성'").fetchall()]
        mats3 = [dict(r) for r in conn.execute("SELECT id, material_code, material_name FROM materials").fetchall()]
        conn.close()
        sup3 = {s['name']: s['id'] for s in sups3}
        mat3 = {"직접입력": None}
        mat3.update({f"{m['material_code']} - {m['material_name']}": m['id'] for m in mats3})
        with st.form("quote_form", clear_on_submit=True):
            sup_q   = st.selectbox("공급사 *", list(sup3.keys()) if sup3 else ["없음"])
            mat_q   = st.selectbox("자재", list(mat3.keys()))
            item_q  = st.text_input("품목명 (직접입력 시)")
            col_a, col_b = st.columns(2)
            qty_q   = col_a.number_input("수량", min_value=1, value=1)
            price_q = col_b.number_input("단가 *", min_value=0.0, format="%.2f")
            col_c, col_d = st.columns(2)
            currency= col_c.selectbox("통화", ["KRW","USD","EUR","JPY","CNY"])
            valid   = col_d.date_input("유효기간")
            col_e, col_f = st.columns(2)
            delivery_q = col_e.number_input("납기일수", min_value=0, value=7)
            incoterm_q = col_f.selectbox("인코텀즈", ["없음","EXW","FOB","CIF","CFR","DAP","DDP"])
            status_q= st.selectbox("상태", ["검토중","승인","반려","만료"])
            note_q  = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not sup3 or price_q == 0:
                    st.error("공급사, 단가 필수")
                else:
                    final_name = item_q if mat_q == "직접입력" else mat_q.split(" - ")[1]
                    try:
                        qnum = gen_number("QT")
                        conn = get_db()
                        conn.execute("""INSERT INTO quotations
                            (quote_number,supplier_id,material_id,item_name,quantity,unit_price,currency,valid_until,status)
                            VALUES(?,?,?,?,?,?,?,?,?)""",
                            (qnum,sup3.get(sup_q),mat3.get(mat_q),
                             final_name,qty_q,price_q,currency,str(valid),status_q))
                        conn.commit(); conn.close()
                        st.success(f"견적서 {qnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("견적서 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT q.quote_number AS 견적번호, s.name AS 공급사,
                   q.item_name AS 품목, q.quantity AS 수량, q.unit_price AS 단가,
                   q.currency AS 통화, ROUND(q.quantity*q.unit_price,0) AS 총액,
                   q.valid_until AS 유효기간, q.status AS 상태
            FROM quotations q LEFT JOIN suppliers s ON q.supplier_id=s.id
            ORDER BY q.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("견적서 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (moving_avg_price) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_moving_avg_price = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM moving_avg_price ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('item_name','')}"
                        _row_opts_moving_avg_price[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_moving_avg_price:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_moving_avg_price = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_moving_avg_price.keys()),
                        key="_rbsel_moving_avg_price", label_visibility="collapsed"
                    )
                    _rb_id_moving_avg_price = _row_opts_moving_avg_price[_rb_sel_moving_avg_price]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_moving_avg_price"):
                        st.session_state[f"_edit_moving_avg_price"] = _rb_id_moving_avg_price
                        st.session_state[f"_del_moving_avg_price"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"]  = _rb_id_moving_avg_price
                        st.session_state[f"_edit_moving_avg_price"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_moving_avg_price"):
                    _del_id_moving_avg_price = st.session_state[f"_del_moving_avg_price"]
                    st.warning(f"⚠️ ID **{_del_id_moving_avg_price}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_moving_avg_price"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM moving_avg_price WHERE id = ?", (_del_id_moving_avg_price,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_moving_avg_price"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_moving_avg_price"):
                    _edit_id_moving_avg_price = st.session_state[f"_edit_moving_avg_price"]
                    try:
                        _cx_e = get_db()
                        _edit_row_moving_avg_price = dict(_cx_e.execute(
                            "SELECT * FROM moving_avg_price WHERE id=?", (_edit_id_moving_avg_price,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_moving_avg_price = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_moving_avg_price}", expanded=True):
                        if not _edit_row_moving_avg_price:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_moving_avg_price = [c for c in _edit_row_moving_avg_price if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_moving_avg_price)))
                            _ecols = st.columns(_ncols)
                            _new_vals_moving_avg_price = {}
                            for _i, _fc in enumerate(_edit_fields_moving_avg_price):
                                _cv = _edit_row_moving_avg_price[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_moving_avg_price[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                                else:
                                    _new_vals_moving_avg_price[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_moving_avg_price"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_moving_avg_price])
                                _set_params = list(_new_vals_moving_avg_price.values()) + [_edit_id_moving_avg_price]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE moving_avg_price SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_moving_avg_price"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_moving_avg_price"):
                                st.session_state[f"_edit_moving_avg_price"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (견적(RFQ)) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_quotations = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목 FROM quotations ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목','')}"
                        _row_opts_quotations[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_quotations:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_quotations = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_quotations.keys()),
                        key="_rbsel_quotations", label_visibility="collapsed"
                    )
                    _rb_id_quotations = _row_opts_quotations[_rb_sel_quotations]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_quotations"):
                        st.session_state[f"_edit_quotations"] = _rb_id_quotations
                        st.session_state[f"_del_quotations"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_quotations"):
                        st.session_state[f"_del_quotations"]  = _rb_id_quotations
                        st.session_state[f"_edit_quotations"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_quotations"):
                    _del_id_quotations = st.session_state[f"_del_quotations"]
                    st.warning(f"⚠️ ID **{_del_id_quotations}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_quotations"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM quotations WHERE id = ?", (_del_id_quotations,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_quotations"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_quotations"):
                        st.session_state[f"_del_quotations"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_quotations"):
                    _edit_id_quotations = st.session_state[f"_edit_quotations"]
                    try:
                        _cx_e = get_db()
                        _edit_row_quotations = dict(_cx_e.execute(
                            "SELECT * FROM quotations WHERE id=?", (_edit_id_quotations,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_quotations = {}
                    with st.expander(f"✏️ 견적(RFQ) 수정 — ID {_edit_id_quotations}", expanded=True):
                        if not _edit_row_quotations:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_quotations = [c for c in _edit_row_quotations if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_quotations)))
                            _ecols = st.columns(_ncols)
                            _new_vals_quotations = {}
                            for _i, _fc in enumerate(_edit_fields_quotations):
                                _cv = _edit_row_quotations[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_quotations[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_quotations}_{_fc}_quotations")
                                else:
                                    _new_vals_quotations[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_quotations}_{_fc}_quotations")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_quotations"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_quotations])
                                _set_params = list(_new_vals_quotations.values()) + [_edit_id_quotations]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE quotations SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_quotations"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_quotations"):
                                st.session_state[f"_edit_quotations"] = None; st.rerun()

        st.divider()
        st.subheader("견적 상태 변경")
        conn = get_db()
        qts = [dict(r) for r in conn.execute("SELECT id, quote_number, item_name, status FROM quotations").fetchall()]
        conn.close()
        if qts:
            qt_map = {f"{q['quote_number']} - {q['item_name']} ({q['status']})": q['id'] for q in qts}
            sel_qt = st.selectbox("견적 선택", list(qt_map.keys()))
            new_qt_st = st.selectbox("변경 상태", ["검토중","승인","반려","만료"])
            if st.button("🔄 변경", use_container_width=True, key="qt_st"):
                conn = get_db()
                conn.execute("UPDATE quotations SET status=? WHERE id=?", (new_qt_st, qt_map[sel_qt]))
                conn.commit(); conn.close()
                st.success("완료!"); st.rerun()

# ── 8. 견적 비교 ──────────────────────────────────────
with tabs[7]:
    st.subheader("🔀 복수 공급사 견적 비교표")
    st.caption("동일 품목에 대한 공급사별 단가, 납기, 조건을 한눈에 비교")
    conn = get_db()
    df_all_q = pd.read_sql_query("""
        SELECT q.item_name AS 품목, s.name AS 공급사,
               q.quantity AS 수량, q.unit_price AS 단가, q.currency AS 통화,
               ROUND(q.quantity*q.unit_price,0) AS 총액,
               q.valid_until AS 유효기간, q.status AS 상태, q.quote_number AS 견적번호
        FROM quotations q LEFT JOIN suppliers s ON q.supplier_id=s.id
        ORDER BY q.item_name, q.unit_price""", conn)
    conn.close()
    if df_all_q.empty:
        st.info("견적서가 없습니다. 먼저 견적(RFQ) 탭에서 등록하세요.")
    else:
        items = df_all_q['품목'].unique().tolist()
        sel_item = st.selectbox("비교할 품목 선택", items)
        filtered = df_all_q[df_all_q['품목'] == sel_item].reset_index(drop=True)
        st.markdown(f"**'{sel_item}' 견적 비교 — {len(filtered)}개 공급사**")
        if not filtered.empty:
            min_price = filtered['단가'].min()
            def highlight_best(row):
                return ['background-color:#d1fae5;font-weight:bold']*len(row) if row['단가'] == min_price else ['']*len(row)
            st.dataframe(filtered.style.apply(highlight_best, axis=1), use_container_width=True, hide_index=True)
            col1, col2, col3 = st.columns(3)
            col1.metric("최저단가", f"{filtered['단가'].min():,.0f}")
            col2.metric("최고단가", f"{filtered['단가'].max():,.0f}")
            col3.metric("단가 차이", f"{filtered['단가'].max()-filtered['단가'].min():,.0f}")
            st.caption("🟢 초록색 = 최저단가 공급사")
            st.divider()
            st.subheader("견적 → PO 전환")
            best_q = filtered[filtered['상태']=='승인']
            if best_q.empty:
                st.info("승인된 견적이 없습니다. 견적 탭에서 상태를 '승인'으로 변경하세요.")
            else:
                q_opts = {f"{r['견적번호']} - {r['공급사']} ({r['단가']:,.0f})": r['견적번호']
                          for _, r in best_q.iterrows()}
                sel_q2po = st.selectbox("전환할 견적", list(q_opts.keys()))
                if st.button("📋 발주서(PO)로 전환", use_container_width=True):
                    conn = get_db()
                    q_data = conn.execute("""
                        SELECT q.*, s.id as sid FROM quotations q
                        LEFT JOIN suppliers s ON q.supplier_id=s.id
                        WHERE q.quote_number=?""", (q_opts[sel_q2po],)).fetchone()
                    if q_data:
                        po_num = gen_number("PO")
                        conn.execute("""INSERT INTO purchase_orders
                            (po_number,supplier_id,material_id,item_name,quantity,unit_price,currency,status)
                            VALUES(?,?,?,?,?,?,?,?)""",
                            (po_num,q_data['supplier_id'],q_data['material_id'],
                             q_data['item_name'],q_data['quantity'],q_data['unit_price'],
                             q_data['currency'],'발주완료'))
                        po_id = conn.execute("SELECT id FROM purchase_orders WHERE po_number=?", (po_num,)).fetchone()['id']
                        try:
                            conn.execute("INSERT INTO po_receipt_summary(po_id,ordered_qty,received_qty,remaining_qty) VALUES(?,?,0,?)",
                                         (po_id, q_data['quantity'], q_data['quantity']))
                        except: pass
                        conn.commit(); conn.close()
                        st.success(f"PO {po_num} 생성!"); st.rerun()
                    else:
                        conn.close()

# ── 9. 계약 ──────────────────────────────────────
with tabs[8]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("공급사 계약 등록")
        conn = get_db()
        sups4 = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers WHERE status='활성'").fetchall()]
        conn.close()
        sup4 = {s['name']: s['id'] for s in sups4}
        with st.form("contract_form", clear_on_submit=True):
            sup_c   = st.selectbox("공급사 *", list(sup4.keys()) if sup4 else ["없음"])
            item_c  = st.text_input("계약 품목 *")
            col_a, col_b = st.columns(2)
            qty_c   = col_a.number_input("계약수량", min_value=1, value=1)
            price_c = col_b.number_input("계약단가", min_value=0.0, format="%.2f")
            col_c2, col_d2 = st.columns(2)
            currency_c = col_c2.selectbox("통화", ["KRW","USD","EUR"])
            contract_type_c = col_d2.selectbox("계약유형", ["일반계약","연간계약","단가계약","MOU"])
            col_e, col_f = st.columns(2)
            start_c = col_e.date_input("계약시작")
            end_c   = col_f.date_input("계약종료")
            col_g, col_h = st.columns(2)
            status_c   = col_g.selectbox("상태", ["유효","만료","해지"])
            renewal_notice = col_h.selectbox("갱신 알림", ["없음","30일전","60일전","90일전"])
            note_c  = st.text_area("특이사항", height=60)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_c or not sup4:
                    st.error("공급사, 품목 필수")
                else:
                    try:
                        cnum = gen_number("CT")
                        conn = get_db()
                        conn.execute("""INSERT INTO supplier_contracts
                            (contract_number,supplier_id,item_name,contract_qty,unit_price,
                             currency,start_date,end_date,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (cnum,sup4.get(sup_c),item_c,qty_c,price_c,
                             currency_c,str(start_c),str(end_c),status_c,note_c))
                        conn.commit(); conn.close()
                        st.success(f"계약 {cnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("계약 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT c.contract_number AS 계약번호, s.name AS 공급사,
                   c.item_name AS 품목, c.contract_qty AS 계약수량,
                   c.unit_price AS 단가, c.currency AS 통화,
                   c.start_date AS 시작일, c.end_date AS 종료일, c.status AS 상태
            FROM supplier_contracts c LEFT JOIN suppliers s ON c.supplier_id=s.id
            ORDER BY c.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("계약 없음")
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            day30 = (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d")
            day90 = (datetime.now()+timedelta(days=90)).strftime("%Y-%m-%d")
            def exp_color(row):
                if row['상태'] == '만료' or row['종료일'] < today: return ['background-color:#fee2e2']*len(row)
                if row['종료일'] <= day30: return ['background-color:#fef9c3']*len(row)
                if row['종료일'] <= day90: return ['background-color:#e0f2fe']*len(row)
                return ['']*len(row)
            st.dataframe(df.style.apply(exp_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (po_receipt_summary) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_po_receipt_summary = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM po_receipt_summary ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('po_id','')}"
                        _row_opts_po_receipt_summary[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_po_receipt_summary:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_po_receipt_summary = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_po_receipt_summary.keys()),
                        key="_rbsel_po_receipt_summary", label_visibility="collapsed"
                    )
                    _rb_id_po_receipt_summary = _row_opts_po_receipt_summary[_rb_sel_po_receipt_summary]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_po_receipt_summary"):
                        st.session_state[f"_edit_po_receipt_summary"] = _rb_id_po_receipt_summary
                        st.session_state[f"_del_po_receipt_summary"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_po_receipt_summary"):
                        st.session_state[f"_del_po_receipt_summary"]  = _rb_id_po_receipt_summary
                        st.session_state[f"_edit_po_receipt_summary"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_po_receipt_summary"):
                    _del_id_po_receipt_summary = st.session_state[f"_del_po_receipt_summary"]
                    st.warning(f"⚠️ ID **{_del_id_po_receipt_summary}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_po_receipt_summary"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM po_receipt_summary WHERE id = ?", (_del_id_po_receipt_summary,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_po_receipt_summary"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_po_receipt_summary"):
                        st.session_state[f"_del_po_receipt_summary"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_po_receipt_summary"):
                    _edit_id_po_receipt_summary = st.session_state[f"_edit_po_receipt_summary"]
                    try:
                        _cx_e = get_db()
                        _edit_row_po_receipt_summary = dict(_cx_e.execute(
                            "SELECT * FROM po_receipt_summary WHERE id=?", (_edit_id_po_receipt_summary,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_po_receipt_summary = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_po_receipt_summary}", expanded=True):
                        if not _edit_row_po_receipt_summary:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_po_receipt_summary = [c for c in _edit_row_po_receipt_summary if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_po_receipt_summary)))
                            _ecols = st.columns(_ncols)
                            _new_vals_po_receipt_summary = {}
                            for _i, _fc in enumerate(_edit_fields_po_receipt_summary):
                                _cv = _edit_row_po_receipt_summary[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_po_receipt_summary[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_po_receipt_summary}_{_fc}_po_receipt_summary")
                                else:
                                    _new_vals_po_receipt_summary[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_po_receipt_summary}_{_fc}_po_receipt_summary")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_po_receipt_summary"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_po_receipt_summary])
                                _set_params = list(_new_vals_po_receipt_summary.values()) + [_edit_id_po_receipt_summary]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE po_receipt_summary SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_po_receipt_summary"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_po_receipt_summary"):
                                st.session_state[f"_edit_po_receipt_summary"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (계약) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_supplier_contracts = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 공급사 FROM supplier_contracts ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('공급사','')}"
                        _row_opts_supplier_contracts[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_supplier_contracts:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_supplier_contracts = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_supplier_contracts.keys()),
                        key="_rbsel_supplier_contracts", label_visibility="collapsed"
                    )
                    _rb_id_supplier_contracts = _row_opts_supplier_contracts[_rb_sel_supplier_contracts]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_supplier_contracts"):
                        st.session_state[f"_edit_supplier_contracts"] = _rb_id_supplier_contracts
                        st.session_state[f"_del_supplier_contracts"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_supplier_contracts"):
                        st.session_state[f"_del_supplier_contracts"]  = _rb_id_supplier_contracts
                        st.session_state[f"_edit_supplier_contracts"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_supplier_contracts"):
                    _del_id_supplier_contracts = st.session_state[f"_del_supplier_contracts"]
                    st.warning(f"⚠️ ID **{_del_id_supplier_contracts}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_supplier_contracts"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM supplier_contracts WHERE id = ?", (_del_id_supplier_contracts,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_supplier_contracts"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_supplier_contracts"):
                        st.session_state[f"_del_supplier_contracts"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_supplier_contracts"):
                    _edit_id_supplier_contracts = st.session_state[f"_edit_supplier_contracts"]
                    try:
                        _cx_e = get_db()
                        _edit_row_supplier_contracts = dict(_cx_e.execute(
                            "SELECT * FROM supplier_contracts WHERE id=?", (_edit_id_supplier_contracts,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_supplier_contracts = {}
                    with st.expander(f"✏️ 계약 수정 — ID {_edit_id_supplier_contracts}", expanded=True):
                        if not _edit_row_supplier_contracts:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_supplier_contracts = [c for c in _edit_row_supplier_contracts if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_supplier_contracts)))
                            _ecols = st.columns(_ncols)
                            _new_vals_supplier_contracts = {}
                            for _i, _fc in enumerate(_edit_fields_supplier_contracts):
                                _cv = _edit_row_supplier_contracts[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_supplier_contracts[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_supplier_contracts}_{_fc}_supplier_contracts")
                                else:
                                    _new_vals_supplier_contracts[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_supplier_contracts}_{_fc}_supplier_contracts")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_supplier_contracts"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_supplier_contracts])
                                _set_params = list(_new_vals_supplier_contracts.values()) + [_edit_id_supplier_contracts]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE supplier_contracts SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_supplier_contracts"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_supplier_contracts"):
                                st.session_state[f"_edit_supplier_contracts"] = None; st.rerun()

            exp_30 = df[(df['상태']=='유효') & (df['종료일'] <= day30)]
            exp_90 = df[(df['상태']=='유효') & (df['종료일'] <= day90) & (df['종료일'] > day30)]
            if not exp_30.empty:
                st.error(f"🔴 30일 내 만료: {len(exp_30)}건 — 즉시 갱신 검토 필요")
            if not exp_90.empty:
                st.warning(f"🟡 90일 내 만료 예정: {len(exp_90)}건")

# ── 10. 블랭킷 PO ──────────────────────────────────────
with tabs[9]:
    st.subheader("🗂️ 블랭킷 PO (한도계약)")
    st.caption("연간 총액 한도를 설정하고 개별 발주 시 잔액 자동 차감")
    col_form, col_list = st.columns([1, 2])
    with col_form:
        conn = get_db()
        sups_bl = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers WHERE status='활성'").fetchall()]
        conn.close()
        sup_bl = {s['name']: s['id'] for s in sups_bl}
        with st.form("blanket_form", clear_on_submit=True):
            sup_bl_sel = st.selectbox("공급사 *", list(sup_bl.keys()) if sup_bl else ["없음"])
            item_bl  = st.text_input("계약 품목 *")
            col_a, col_b = st.columns(2)
            limit_amt = col_a.number_input("총 한도금액 *", min_value=0.0, format="%.0f")
            unit_price_bl = col_b.number_input("기준 단가", min_value=0.0, format="%.2f")
            col_c, col_d = st.columns(2)
            currency_bl = col_c.selectbox("통화", ["KRW","USD","EUR"])
            status_bl = col_d.selectbox("상태", ["유효","만료","정지"])
            col_e, col_f = st.columns(2)
            start_bl = col_e.date_input("시작일")
            end_bl   = col_f.date_input("종료일")
            note_bl  = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not sup_bl or not item_bl or limit_amt == 0:
                    st.error("공급사, 품목, 한도금액 필수")
                else:
                    try:
                        blnum = gen_number("BL")
                        conn = get_db()
                        conn.execute("""INSERT INTO blanket_orders
                            (blanket_number,supplier_id,item_name,total_limit_amount,
                             remaining_amount,currency,unit_price,start_date,end_date,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (blnum,sup_bl[sup_bl_sel],item_bl,limit_amt,
                             limit_amt,currency_bl,unit_price_bl,str(start_bl),str(end_bl),status_bl,note_bl))
                        conn.commit(); conn.close()
                        st.success(f"블랭킷PO {blnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("블랭킷 PO 목록")
        conn = get_db()
        df_bl = pd.read_sql_query("""
            SELECT b.blanket_number AS 계약번호, s.name AS 공급사,
                   b.item_name AS 품목, b.total_limit_amount AS 총한도,
                   b.used_amount AS 사용금액, b.remaining_amount AS 잔액,
                   ROUND(b.used_amount/NULLIF(b.total_limit_amount,0)*100,1) AS 사용률,
                   b.currency AS 통화, b.end_date AS 종료일, b.status AS 상태
            FROM blanket_orders b LEFT JOIN suppliers s ON b.supplier_id=s.id
            ORDER BY b.id DESC""", conn)
        conn.close()
        if df_bl.empty:
            st.info("블랭킷 PO 없음")
        else:
            def bl_color(row):
                u = row.get('사용률') or 0
                if u >= 90: return ['background-color:#fee2e2']*len(row)
                if u >= 70: return ['background-color:#fef3c7']*len(row)
                return ['']*len(row)
            st.dataframe(df_bl.style.apply(bl_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (블랭킷PO) ──────────────────────────
            if not df_bl.empty if hasattr(df_bl, 'empty') else df_bl is not None:
                _row_opts_blanket_orders = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 공급사 FROM blanket_orders ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('공급사','')}"
                        _row_opts_blanket_orders[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_blanket_orders:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_blanket_orders = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_blanket_orders.keys()),
                        key="_rbsel_blanket_orders", label_visibility="collapsed"
                    )
                    _rb_id_blanket_orders = _row_opts_blanket_orders[_rb_sel_blanket_orders]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_blanket_orders"):
                        st.session_state[f"_edit_blanket_orders"] = _rb_id_blanket_orders
                        st.session_state[f"_del_blanket_orders"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_blanket_orders"):
                        st.session_state[f"_del_blanket_orders"]  = _rb_id_blanket_orders
                        st.session_state[f"_edit_blanket_orders"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_blanket_orders"):
                    _del_id_blanket_orders = st.session_state[f"_del_blanket_orders"]
                    st.warning(f"⚠️ ID **{_del_id_blanket_orders}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_blanket_orders"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM blanket_orders WHERE id = ?", (_del_id_blanket_orders,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_blanket_orders"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_blanket_orders"):
                        st.session_state[f"_del_blanket_orders"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_blanket_orders"):
                    _edit_id_blanket_orders = st.session_state[f"_edit_blanket_orders"]
                    try:
                        _cx_e = get_db()
                        _edit_row_blanket_orders = dict(_cx_e.execute(
                            "SELECT * FROM blanket_orders WHERE id=?", (_edit_id_blanket_orders,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_blanket_orders = {}
                    with st.expander(f"✏️ 블랭킷PO 수정 — ID {_edit_id_blanket_orders}", expanded=True):
                        if not _edit_row_blanket_orders:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_blanket_orders = [c for c in _edit_row_blanket_orders if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_blanket_orders)))
                            _ecols = st.columns(_ncols)
                            _new_vals_blanket_orders = {}
                            for _i, _fc in enumerate(_edit_fields_blanket_orders):
                                _cv = _edit_row_blanket_orders[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_blanket_orders[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_blanket_orders}_{_fc}_blanket_orders")
                                else:
                                    _new_vals_blanket_orders[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_blanket_orders}_{_fc}_blanket_orders")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_blanket_orders"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_blanket_orders])
                                _set_params = list(_new_vals_blanket_orders.values()) + [_edit_id_blanket_orders]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE blanket_orders SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_blanket_orders"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_blanket_orders"):
                                st.session_state[f"_edit_blanket_orders"] = None; st.rerun()

            warn_bl = df_bl[(df_bl['상태']=='유효') & (df_bl['사용률'] >= 80)]
            if not warn_bl.empty:
                st.warning(f"⚠️ 한도 80% 초과: {len(warn_bl)}건")
        st.divider()
        st.subheader("📤 릴리즈 (발주 생성)")
        conn = get_db()
        bl_active = [dict(r) for r in conn.execute("""
            SELECT b.id, b.blanket_number, s.name AS sup_name, b.item_name,
                   b.remaining_amount, b.unit_price, b.currency, b.supplier_id
            FROM blanket_orders b JOIN suppliers s ON b.supplier_id=s.id
            WHERE b.status='유효' AND b.remaining_amount > 0""").fetchall()]
        conn.close()
        if not bl_active:
            st.info("릴리즈 가능한 블랭킷 PO 없음")
        else:
            bl_map = {f"{b['blanket_number']} - {b['sup_name']} / {b['item_name']} (잔:{b['remaining_amount']:,.0f})": b
                      for b in bl_active}
            sel_bl = st.selectbox("블랭킷 PO 선택", list(bl_map.keys()))
            bl_obj = bl_map[sel_bl]
            col_r1, col_r2 = st.columns(2)
            release_qty = col_r1.number_input("릴리즈 수량", min_value=1, value=1)
            release_amt = release_qty * bl_obj['unit_price']
            col_r2.metric("릴리즈 금액", f"₩{release_amt:,.0f}")
            if st.button("🚀 PO 생성 (릴리즈)", use_container_width=True, key="bl_release"):
                if release_amt > bl_obj['remaining_amount']:
                    st.error("잔액 초과")
                else:
                    try:
                        conn = get_db()
                        po_num = gen_number("PO")
                        conn.execute("""INSERT INTO purchase_orders
                            (po_number,supplier_id,item_name,quantity,unit_price,currency,status)
                            VALUES(?,?,?,?,?,?,'발주완료')""",
                            (po_num, bl_obj['supplier_id'], bl_obj['item_name'],
                             release_qty, bl_obj['unit_price'], bl_obj['currency']))
                        po_id = conn.execute("SELECT id FROM purchase_orders WHERE po_number=?", (po_num,)).fetchone()['id']
                        conn.execute("INSERT INTO po_receipt_summary(po_id,ordered_qty,received_qty,remaining_qty) VALUES(?,?,0,?)",
                                     (po_id, release_qty, release_qty))
                        conn.execute("UPDATE blanket_orders SET used_amount=used_amount+?,remaining_amount=remaining_amount-? WHERE id=?",
                                     (release_amt, release_amt, bl_obj['id']))
                        conn.execute("INSERT INTO blanket_order_releases(blanket_id,po_id,release_qty,release_amount,release_date) VALUES(?,?,?,?,date('now'))",
                                     (bl_obj['id'], po_id, release_qty, release_amt))
                        conn.commit(); conn.close()
                        st.success(f"PO {po_num} 생성! 잔액 ₩{bl_obj['remaining_amount']-release_amt:,.0f}"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")


# ── 11. 발주서 PO ──────────────────────────────────────
with tabs[10]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("발주서(PO) 등록")
        conn = get_db()
        sups5 = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers WHERE status='활성'").fetchall()]
        mats5 = [dict(r) for r in conn.execute("SELECT id, material_code, material_name FROM materials").fetchall()]
        prs5  = [dict(r) for r in conn.execute("SELECT id, pr_number, item_name FROM purchase_requests WHERE status='승인'").fetchall()]
        conn.close()
        sup5 = {s['name']: s['id'] for s in sups5}
        mat5 = {"직접입력": None}
        mat5.update({f"{m['material_code']} - {m['material_name']}": m['id'] for m in mats5})
        pr5 = {"없음": None}
        pr5.update({f"{p['pr_number']} - {p['item_name']}": p['id'] for p in prs5})
        with st.form("po_form", clear_on_submit=True):
            pr_sel   = st.selectbox("연결 PR (선택)", list(pr5.keys()))
            sup_p2   = st.selectbox("공급사 *", list(sup5.keys()) if sup5 else ["없음"])
            mat_p2   = st.selectbox("자재", list(mat5.keys()))
            item_p2  = st.text_input("품목명 (직접입력 시)")
            col_a, col_b = st.columns(2)
            qty_p2   = col_a.number_input("수량 *", min_value=1, value=1)
            price_p2 = col_b.number_input("단가 *", min_value=0.0, format="%.2f")
            col_c2, col_d2 = st.columns(2)
            currency_p2 = col_c2.selectbox("통화", ["KRW","USD","EUR","JPY","CNY"])
            status_p2   = col_d2.selectbox("상태", ["발주완료","납품중","입고완료","취소"])
            col_e, col_f = st.columns(2)
            delivery = col_e.date_input("납기일")
            warehouse= col_f.text_input("입고창고")
            note_p2  = st.text_area("비고", height=50)
            if sup5 and sup_p2 in sup5:
                conn = get_db()
                pir_auto = conn.execute("""
                    SELECT unit_price, currency, lead_time_days FROM purchase_info_records
                    WHERE supplier_id=? AND status='유효' ORDER BY id DESC LIMIT 1""", (sup5[sup_p2],)).fetchone()
                conn.close()
                if pir_auto:
                    st.info(f"💡 PIR 참조가: {pir_auto['unit_price']:,.2f} {pir_auto['currency']} (납기 {pir_auto['lead_time_days']}일)")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not sup5 or price_p2 == 0:
                    st.error("공급사, 단가 필수")
                else:
                    final_name = item_p2 if mat_p2 == "직접입력" else mat_p2.split(" - ")[1]
                    try:
                        po_num = gen_number("PO")
                        conn = get_db()
                        conn.execute("""INSERT INTO purchase_orders
                            (po_number,pr_id,supplier_id,material_id,item_name,quantity,
                             unit_price,currency,delivery_date,warehouse,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (po_num,pr5.get(pr_sel),sup5.get(sup_p2),mat5.get(mat_p2),
                             final_name,qty_p2,price_p2,currency_p2,str(delivery),warehouse,status_p2,note_p2))
                        po_id = conn.execute("SELECT id FROM purchase_orders WHERE po_number=?", (po_num,)).fetchone()['id']
                        try:
                            conn.execute("INSERT INTO po_receipt_summary(po_id,ordered_qty,received_qty,remaining_qty) VALUES(?,?,0,?)",
                                         (po_id, qty_p2, qty_p2))
                        except: pass
                        conn.commit(); conn.close()
                        st.success(f"발주서 {po_num} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("발주서 목록 (부분입고 잔량 포함)")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT p.po_number AS 발주번호, s.name AS 공급사,
                   p.item_name AS 품목, p.quantity AS 발주수량,
                   COALESCE(r.received_qty,0) AS 입고수량,
                   COALESCE(r.remaining_qty,p.quantity) AS 잔량,
                   p.unit_price AS 단가, p.currency AS 통화,
                   ROUND(p.quantity*p.unit_price,0) AS 총액,
                   p.delivery_date AS 납기일, p.status AS 상태, p.created_at AS 등록일
            FROM purchase_orders p
            LEFT JOIN suppliers s ON p.supplier_id=s.id
            LEFT JOIN po_receipt_summary r ON p.id=r.po_id
            ORDER BY p.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("발주서 없음")
        else:
            sf = st.multiselect("상태 필터", df['상태'].unique().tolist(), default=df['상태'].unique().tolist())
            filtered = df[df['상태'].isin(sf)]
            today_po = datetime.now().strftime("%Y-%m-%d")
            def po_color(row):
                if row['상태'] == '취소': return ['background-color:#f3f4f6']*len(row)
                if row['납기일'] < today_po and row['상태'] not in ['입고완료','취소']:
                    return ['background-color:#fee2e2']*len(row)
                if row['잔량'] > 0 and row['상태'] not in ['취소','입고완료']:
                    return ['background-color:#fef3c7']*len(row)
                return ['']*len(row)
            st.dataframe(filtered.style.apply(po_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (blanket_order_releases) ──────────────────────────
            if not filtered.empty if hasattr(filtered, 'empty') else filtered is not None:
                _row_opts_blanket_order_releases = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM blanket_order_releases ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('id','')}"
                        _row_opts_blanket_order_releases[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_blanket_order_releases:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_blanket_order_releases = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_blanket_order_releases.keys()),
                        key="_rbsel_blanket_order_releases", label_visibility="collapsed"
                    )
                    _rb_id_blanket_order_releases = _row_opts_blanket_order_releases[_rb_sel_blanket_order_releases]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_blanket_order_releases"):
                        st.session_state[f"_edit_blanket_order_releases"] = _rb_id_blanket_order_releases
                        st.session_state[f"_del_blanket_order_releases"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_blanket_order_releases"):
                        st.session_state[f"_del_blanket_order_releases"]  = _rb_id_blanket_order_releases
                        st.session_state[f"_edit_blanket_order_releases"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_blanket_order_releases"):
                    _del_id_blanket_order_releases = st.session_state[f"_del_blanket_order_releases"]
                    st.warning(f"⚠️ ID **{_del_id_blanket_order_releases}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_blanket_order_releases"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM blanket_order_releases WHERE id = ?", (_del_id_blanket_order_releases,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_blanket_order_releases"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_blanket_order_releases"):
                        st.session_state[f"_del_blanket_order_releases"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_blanket_order_releases"):
                    _edit_id_blanket_order_releases = st.session_state[f"_edit_blanket_order_releases"]
                    try:
                        _cx_e = get_db()
                        _edit_row_blanket_order_releases = dict(_cx_e.execute(
                            "SELECT * FROM blanket_order_releases WHERE id=?", (_edit_id_blanket_order_releases,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_blanket_order_releases = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_blanket_order_releases}", expanded=True):
                        if not _edit_row_blanket_order_releases:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_blanket_order_releases = [c for c in _edit_row_blanket_order_releases if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_blanket_order_releases)))
                            _ecols = st.columns(_ncols)
                            _new_vals_blanket_order_releases = {}
                            for _i, _fc in enumerate(_edit_fields_blanket_order_releases):
                                _cv = _edit_row_blanket_order_releases[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_blanket_order_releases[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_blanket_order_releases}_{_fc}_blanket_order_releases")
                                else:
                                    _new_vals_blanket_order_releases[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_blanket_order_releases}_{_fc}_blanket_order_releases")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_blanket_order_releases"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_blanket_order_releases])
                                _set_params = list(_new_vals_blanket_order_releases.values()) + [_edit_id_blanket_order_releases]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE blanket_order_releases SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_blanket_order_releases"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_blanket_order_releases"):
                                st.session_state[f"_edit_blanket_order_releases"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (PO) ──────────────────────────
            if not filtered.empty if hasattr(filtered, 'empty') else filtered is not None:
                _row_opts_purchase_orders = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM purchase_orders ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_purchase_orders[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_purchase_orders:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_purchase_orders = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_purchase_orders.keys()),
                        key="_rbsel_purchase_orders", label_visibility="collapsed"
                    )
                    _rb_id_purchase_orders = _row_opts_purchase_orders[_rb_sel_purchase_orders]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_purchase_orders"):
                        st.session_state[f"_edit_purchase_orders"] = _rb_id_purchase_orders
                        st.session_state[f"_del_purchase_orders"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_purchase_orders"):
                        st.session_state[f"_del_purchase_orders"]  = _rb_id_purchase_orders
                        st.session_state[f"_edit_purchase_orders"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_purchase_orders"):
                    _del_id_purchase_orders = st.session_state[f"_del_purchase_orders"]
                    st.warning(f"⚠️ ID **{_del_id_purchase_orders}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_purchase_orders"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM purchase_orders WHERE id = ?", (_del_id_purchase_orders,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_purchase_orders"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_purchase_orders"):
                        st.session_state[f"_del_purchase_orders"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_purchase_orders"):
                    _edit_id_purchase_orders = st.session_state[f"_edit_purchase_orders"]
                    try:
                        _cx_e = get_db()
                        _edit_row_purchase_orders = dict(_cx_e.execute(
                            "SELECT * FROM purchase_orders WHERE id=?", (_edit_id_purchase_orders,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_purchase_orders = {}
                    with st.expander(f"✏️ PO 수정 — ID {_edit_id_purchase_orders}", expanded=True):
                        if not _edit_row_purchase_orders:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_purchase_orders = [c for c in _edit_row_purchase_orders if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_purchase_orders)))
                            _ecols = st.columns(_ncols)
                            _new_vals_purchase_orders = {}
                            for _i, _fc in enumerate(_edit_fields_purchase_orders):
                                _cv = _edit_row_purchase_orders[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_purchase_orders[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_purchase_orders}_{_fc}_purchase_orders")
                                else:
                                    _new_vals_purchase_orders[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_purchase_orders}_{_fc}_purchase_orders")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_purchase_orders"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_purchase_orders])
                                _set_params = list(_new_vals_purchase_orders.values()) + [_edit_id_purchase_orders]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE purchase_orders SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_purchase_orders"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_purchase_orders"):
                                st.session_state[f"_edit_purchase_orders"] = None; st.rerun()

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("총 발주금액", f"₩{filtered['총액'].sum():,.0f}")
            col_m2.metric("미입고 잔량 PO", len(filtered[filtered['잔량']>0]))
            col_m3.metric("입고완료", len(filtered[filtered['상태']=='입고완료']))
            late_po = filtered[(filtered['납기일'] < today_po) & (~filtered['상태'].isin(['입고완료','취소']))]
            col_m4.metric("🔴 납기지연", len(late_po), delta_color="inverse")
        st.divider()
        st.subheader("🔄 PO 상태 변경 + 변경이력")
        conn = get_db()
        pos_chg = [dict(r) for r in conn.execute(
            "SELECT id, po_number, item_name, status FROM purchase_orders WHERE status NOT IN ('입고완료','취소')").fetchall()]
        conn.close()
        if pos_chg:
            po_map2 = {f"{p['po_number']} - {p['item_name']} ({p['status']})": p for p in pos_chg}
            sel_po2 = st.selectbox("PO 선택", list(po_map2.keys()))
            col_a, col_b, col_c = st.columns(3)
            new_po_st = col_a.selectbox("변경 상태", ["발주완료","납품중","입고완료","취소"])
            changer   = col_b.text_input("변경자")
            chg_reason= col_c.text_input("변경사유")
            if st.button("🔄 상태 변경", use_container_width=True, key="po_status"):
                po_obj = po_map2[sel_po2]
                conn = get_db()
                conn.execute("UPDATE purchase_orders SET status=? WHERE id=?", (new_po_st, po_obj['id']))
                try:
                    conn.execute("""INSERT INTO po_change_log(po_id,po_number,changed_field,old_value,new_value,changed_by,change_reason)
                        VALUES(?,?,?,?,?,?,?)""",
                        (po_obj['id'],po_obj['po_number'],'status',po_obj['status'],new_po_st,changer,chg_reason))
                except: pass
                conn.commit(); conn.close()
                st.success("변경 완료!"); st.rerun()
        st.divider()
        st.subheader("📋 PO 변경이력")
        conn = get_db()
        df_chg = pd.read_sql_query("""
            SELECT po_number AS PO번호, changed_field AS 변경항목,
                   old_value AS 이전값, new_value AS 변경값,
                   changed_by AS 변경자, change_reason AS 사유, changed_at AS 변경일시
            FROM po_change_log ORDER BY id DESC LIMIT 30""", conn)
        conn.close()
        if df_chg.empty:
            st.info("변경이력 없음")
        else:
            st.dataframe(df_chg, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (po_change_log) ──────────────────────────
            if not df_chg.empty if hasattr(df_chg, 'empty') else df_chg is not None:
                _row_opts_po_change_log = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM po_change_log ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('changed_field','')}"
                        _row_opts_po_change_log[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_po_change_log:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_po_change_log = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_po_change_log.keys()),
                        key="_rbsel_po_change_log", label_visibility="collapsed"
                    )
                    _rb_id_po_change_log = _row_opts_po_change_log[_rb_sel_po_change_log]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_po_change_log"):
                        st.session_state[f"_edit_po_change_log"] = _rb_id_po_change_log
                        st.session_state[f"_del_po_change_log"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_po_change_log"):
                        st.session_state[f"_del_po_change_log"]  = _rb_id_po_change_log
                        st.session_state[f"_edit_po_change_log"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_po_change_log"):
                    _del_id_po_change_log = st.session_state[f"_del_po_change_log"]
                    st.warning(f"⚠️ ID **{_del_id_po_change_log}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_po_change_log"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM po_change_log WHERE id = ?", (_del_id_po_change_log,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_po_change_log"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_po_change_log"):
                        st.session_state[f"_del_po_change_log"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_po_change_log"):
                    _edit_id_po_change_log = st.session_state[f"_edit_po_change_log"]
                    try:
                        _cx_e = get_db()
                        _edit_row_po_change_log = dict(_cx_e.execute(
                            "SELECT * FROM po_change_log WHERE id=?", (_edit_id_po_change_log,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_po_change_log = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_po_change_log}", expanded=True):
                        if not _edit_row_po_change_log:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_po_change_log = [c for c in _edit_row_po_change_log if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_po_change_log)))
                            _ecols = st.columns(_ncols)
                            _new_vals_po_change_log = {}
                            for _i, _fc in enumerate(_edit_fields_po_change_log):
                                _cv = _edit_row_po_change_log[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_po_change_log[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_po_change_log}_{_fc}_po_change_log")
                                else:
                                    _new_vals_po_change_log[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_po_change_log}_{_fc}_po_change_log")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_po_change_log"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_po_change_log])
                                _set_params = list(_new_vals_po_change_log.values()) + [_edit_id_po_change_log]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE po_change_log SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_po_change_log"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_po_change_log"):
                                st.session_state[f"_edit_po_change_log"] = None; st.rerun()


# ── 12. 입고 GR ──────────────────────────────────────
with tabs[11]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("입고(GR) 등록")
        conn = get_db()
        pos_gr = [dict(r) for r in conn.execute("""
            SELECT p.id, p.po_number, p.item_name, p.quantity, p.unit_price,
                   COALESCE(r.remaining_qty, p.quantity) AS remaining
            FROM purchase_orders p LEFT JOIN po_receipt_summary r ON p.id=r.po_id
            WHERE p.status IN ('발주완료','납품중') AND COALESCE(r.remaining_qty, p.quantity) > 0""").fetchall()]
        conn.close()
        po_gr_opts = {f"{p['po_number']} - {p['item_name']} (잔량:{p['remaining']})":
                      (p['id'], p['item_name'], p['quantity'], p['remaining'], p['unit_price']) for p in pos_gr}
        with st.form("gr_form", clear_on_submit=True):
            po_sel_gr = st.selectbox("발주서(PO) *", list(po_gr_opts.keys()) if po_gr_opts else ["발주 PO 없음"])
            if po_gr_opts and po_sel_gr in po_gr_opts:
                po_id_val, item_auto, ord_qty, remaining, unit_price_gr = po_gr_opts[po_sel_gr]
            else:
                po_id_val, item_auto, ord_qty, remaining, unit_price_gr = None, "", 0, 0, 0
            item_gr = st.text_input("품목명", value=item_auto)
            col_a, col_b, col_c = st.columns(3)
            col_a.number_input("발주수량", value=ord_qty, disabled=True)
            recv_qty = col_b.number_input("입고수량 *", min_value=0, value=int(remaining))
            rej_qty  = col_c.number_input("불량수량", min_value=0, value=0)
            col_d, col_e = st.columns(2)
            warehouse_gr = col_d.text_input("입고창고")
            bin_gr    = col_e.text_input("Bin 위치")
            col_f, col_g = st.columns(2)
            receiver  = col_f.text_input("입고담당자")
            lot_no    = col_g.text_input("LOT번호")
            # 이동평균단가 미리보기
            if unit_price_gr > 0 and recv_qty > 0:
                conn = get_db()
                prev_map_row = conn.execute("""
                    SELECT new_qty, new_avg_price FROM moving_avg_price WHERE item_code=?
                    ORDER BY id DESC LIMIT 1""", (item_auto,)).fetchone()
                conn.close()
                if prev_map_row:
                    p_qty = prev_map_row['new_qty']; p_avg = prev_map_row['new_avg_price']
                    new_tot = p_qty + recv_qty
                    new_avg_prev = (p_qty * p_avg + recv_qty * unit_price_gr) / new_tot
                    st.info(f"📊 이동평균단가: {p_avg:,.2f} → **{new_avg_prev:,.2f}** (재고 {p_qty}→{new_tot})")
            note_gr = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 입고 등록", use_container_width=True):
                if not po_gr_opts:
                    st.error("발주 PO 없음")
                elif recv_qty == 0:
                    st.error("입고수량 필수")
                else:
                    try:
                        gr_num = gen_number("GR")
                        conn = get_db()
                        conn.execute("""INSERT INTO goods_receipts
                            (gr_number,po_id,item_name,ordered_qty,received_qty,
                             rejected_qty,warehouse,bin_code,receiver,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (gr_num,po_id_val,item_gr,ord_qty,recv_qty,rej_qty,warehouse_gr,bin_gr,receiver,note_gr))
                        conn.execute("""INSERT INTO po_receipt_summary(po_id,ordered_qty,received_qty,remaining_qty,last_gr_date)
                            VALUES(?,?,?,?,date('now'))
                            ON CONFLICT(po_id) DO UPDATE SET
                            received_qty=received_qty+?,
                            remaining_qty=MAX(0,remaining_qty-?),
                            last_gr_date=date('now'),
                            updated_at=datetime('now','localtime')""",
                            (po_id_val,ord_qty,recv_qty,ord_qty-recv_qty,recv_qty,recv_qty))
                        remaining_new = remaining - recv_qty
                        if remaining_new <= 0:
                            conn.execute("UPDATE purchase_orders SET status='입고완료' WHERE id=?", (po_id_val,))
                        else:
                            conn.execute("UPDATE purchase_orders SET status='납품중' WHERE id=?", (po_id_val,))
                        net_qty = recv_qty - rej_qty
                        if net_qty > 0:
                            conn.execute("""INSERT INTO inventory(item_code,item_name,warehouse,stock_qty,system_qty)
                                VALUES(?,?,?,?,?)
                                ON CONFLICT(item_code) DO UPDATE SET
                                stock_qty=stock_qty+excluded.stock_qty,
                                system_qty=system_qty+excluded.system_qty,
                                updated_at=datetime('now','localtime')""",
                                (item_gr,item_gr,warehouse_gr,net_qty,net_qty))
                            # 이동평균단가 자동 계산
                            if unit_price_gr > 0:
                                prev_r = conn.execute("""
                                    SELECT new_qty, new_avg_price FROM moving_avg_price WHERE item_code=?
                                    ORDER BY id DESC LIMIT 1""", (item_gr,)).fetchone()
                                p_qty = prev_r['new_qty'] if prev_r else 0
                                p_avg = prev_r['new_avg_price'] if prev_r else 0
                                new_tot_qty = p_qty + net_qty
                                new_avg = (p_qty * p_avg + net_qty * unit_price_gr) / new_tot_qty
                                conn.execute("""INSERT INTO moving_avg_price
                                    (item_code,item_name,prev_qty,prev_avg_price,
                                     incoming_qty,incoming_price,new_qty,new_avg_price,reference)
                                    VALUES(?,?,?,?,?,?,?,?,?)""",
                                    (item_gr,item_gr,p_qty,p_avg,net_qty,unit_price_gr,new_tot_qty,new_avg,gr_num))
                        conn.commit(); conn.close()
                        msg = "입고완료" if remaining_new <= 0 else f"부분입고 (잔량 {remaining_new}개)"
                        st.success(f"GR {gr_num} 등록! → {msg} | 이동평균단가 자동 갱신"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("입고 이력")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT g.gr_number AS GR번호, p.po_number AS 발주번호,
                   g.item_name AS 품목, g.ordered_qty AS 발주수량,
                   g.received_qty AS 입고수량, g.rejected_qty AS 불량수량,
                   ROUND(g.rejected_qty*100.0/NULLIF(g.received_qty,0),1) AS 불량률,
                   g.warehouse AS 창고, g.receiver AS 담당자, g.created_at AS 입고일시
            FROM goods_receipts g LEFT JOIN purchase_orders p ON g.po_id=p.id
            ORDER BY g.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("입고 이력 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (moving_avg_price) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_moving_avg_price = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM moving_avg_price ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('item_name','')}"
                        _row_opts_moving_avg_price[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_moving_avg_price:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_moving_avg_price = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_moving_avg_price.keys()),
                        key="_rbsel_moving_avg_price", label_visibility="collapsed"
                    )
                    _rb_id_moving_avg_price = _row_opts_moving_avg_price[_rb_sel_moving_avg_price]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_moving_avg_price"):
                        st.session_state[f"_edit_moving_avg_price"] = _rb_id_moving_avg_price
                        st.session_state[f"_del_moving_avg_price"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"]  = _rb_id_moving_avg_price
                        st.session_state[f"_edit_moving_avg_price"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_moving_avg_price"):
                    _del_id_moving_avg_price = st.session_state[f"_del_moving_avg_price"]
                    st.warning(f"⚠️ ID **{_del_id_moving_avg_price}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_moving_avg_price"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM moving_avg_price WHERE id = ?", (_del_id_moving_avg_price,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_moving_avg_price"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_moving_avg_price"):
                        st.session_state[f"_del_moving_avg_price"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_moving_avg_price"):
                    _edit_id_moving_avg_price = st.session_state[f"_edit_moving_avg_price"]
                    try:
                        _cx_e = get_db()
                        _edit_row_moving_avg_price = dict(_cx_e.execute(
                            "SELECT * FROM moving_avg_price WHERE id=?", (_edit_id_moving_avg_price,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_moving_avg_price = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_moving_avg_price}", expanded=True):
                        if not _edit_row_moving_avg_price:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_moving_avg_price = [c for c in _edit_row_moving_avg_price if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_moving_avg_price)))
                            _ecols = st.columns(_ncols)
                            _new_vals_moving_avg_price = {}
                            for _i, _fc in enumerate(_edit_fields_moving_avg_price):
                                _cv = _edit_row_moving_avg_price[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_moving_avg_price[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                                else:
                                    _new_vals_moving_avg_price[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_moving_avg_price}_{_fc}_moving_avg_price")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_moving_avg_price"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_moving_avg_price])
                                _set_params = list(_new_vals_moving_avg_price.values()) + [_edit_id_moving_avg_price]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE moving_avg_price SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_moving_avg_price"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_moving_avg_price"):
                                st.session_state[f"_edit_moving_avg_price"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (GR) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_goods_receipts = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM goods_receipts ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_goods_receipts[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_goods_receipts:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_goods_receipts = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_goods_receipts.keys()),
                        key="_rbsel_goods_receipts", label_visibility="collapsed"
                    )
                    _rb_id_goods_receipts = _row_opts_goods_receipts[_rb_sel_goods_receipts]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_goods_receipts"):
                        st.session_state[f"_edit_goods_receipts"] = _rb_id_goods_receipts
                        st.session_state[f"_del_goods_receipts"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_goods_receipts"):
                        st.session_state[f"_del_goods_receipts"]  = _rb_id_goods_receipts
                        st.session_state[f"_edit_goods_receipts"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_goods_receipts"):
                    _del_id_goods_receipts = st.session_state[f"_del_goods_receipts"]
                    st.warning(f"⚠️ ID **{_del_id_goods_receipts}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_goods_receipts"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM goods_receipts WHERE id = ?", (_del_id_goods_receipts,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_goods_receipts"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_goods_receipts"):
                        st.session_state[f"_del_goods_receipts"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_goods_receipts"):
                    _edit_id_goods_receipts = st.session_state[f"_edit_goods_receipts"]
                    try:
                        _cx_e = get_db()
                        _edit_row_goods_receipts = dict(_cx_e.execute(
                            "SELECT * FROM goods_receipts WHERE id=?", (_edit_id_goods_receipts,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_goods_receipts = {}
                    with st.expander(f"✏️ GR 수정 — ID {_edit_id_goods_receipts}", expanded=True):
                        if not _edit_row_goods_receipts:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_goods_receipts = [c for c in _edit_row_goods_receipts if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_goods_receipts)))
                            _ecols = st.columns(_ncols)
                            _new_vals_goods_receipts = {}
                            for _i, _fc in enumerate(_edit_fields_goods_receipts):
                                _cv = _edit_row_goods_receipts[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_goods_receipts[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_goods_receipts}_{_fc}_goods_receipts")
                                else:
                                    _new_vals_goods_receipts[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_goods_receipts}_{_fc}_goods_receipts")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_goods_receipts"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_goods_receipts])
                                _set_params = list(_new_vals_goods_receipts.values()) + [_edit_id_goods_receipts]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE goods_receipts SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_goods_receipts"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_goods_receipts"):
                                st.session_state[f"_edit_goods_receipts"] = None; st.rerun()

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("총 입고건수", len(df))
            col_m2.metric("총 입고수량", int(df['입고수량'].sum()))
            col_m3.metric("총 불량수량", int(df['불량수량'].sum()))


# ── 13. 반품(RTV) ──────────────────────────────────────
with tabs[12]:
    st.subheader("↩️ 공급사 반품 (Return to Vendor)")
    st.caption("불량·오납 입고품을 공급사에 반품하고 크레딧 노트를 수령합니다")
    col_form, col_list = st.columns([1, 2])
    with col_form:
        conn = get_db()
        grs_rtv = [dict(r) for r in conn.execute("""
            SELECT g.id, g.gr_number, p.po_number, g.item_name,
                   g.received_qty, g.rejected_qty, p.unit_price, p.supplier_id
            FROM goods_receipts g LEFT JOIN purchase_orders p ON g.po_id=p.id
            WHERE g.rejected_qty > 0 ORDER BY g.id DESC LIMIT 50""").fetchall()]
        conn.close()
        with st.form("rtv_form", clear_on_submit=True):
            if grs_rtv:
                gr_rtv_opts = {f"{g['gr_number']} - {g['item_name']} (불량:{g['rejected_qty']})": g for g in grs_rtv}
                sel_gr_rtv = st.selectbox("입고(GR) 선택 *", list(gr_rtv_opts.keys()))
                gr_data = gr_rtv_opts[sel_gr_rtv]
                col_a, col_b = st.columns(2)
                ret_qty = col_a.number_input("반품수량 *", min_value=1, max_value=int(gr_data['rejected_qty']), value=int(gr_data['rejected_qty']))
                ret_unit_price = col_b.number_input("반품단가", min_value=0.0, value=float(gr_data['unit_price'] or 0), format="%.2f")
                credit_amt = ret_qty * ret_unit_price
                st.info(f"💳 크레딧 노트 예상: ₩{credit_amt:,.0f}")
                col_c, col_d = st.columns(2)
                defect_type = col_c.selectbox("불량유형", ["품질불량","수량오납","규격불일치","파손","기타"])
                return_type = col_d.selectbox("반품유형", ["반품","교환","크레딧노트"])
                reason_rtv = st.text_area("반품사유 *", height=60)
            else:
                st.info("반품 가능한 불량 입고건 없음")
                sel_gr_rtv = None
                gr_data = None
                ret_qty = 1; ret_unit_price = 0; credit_amt = 0
                defect_type = "기타"; return_type = "반품"
                reason_rtv = ""
            if st.form_submit_button("✅ 반품 등록", use_container_width=True):
                if not grs_rtv:
                    st.error("반품 가능 입고건 없음")
                elif not reason_rtv:
                    st.error("반품사유 필수")
                else:
                    try:
                        rtv_num = gen_number("RTV")
                        conn = get_db()
                        conn.execute("""INSERT INTO return_to_vendor
                            (rtv_number,gr_id,po_id,supplier_id,item_name,return_qty,
                             reason,defect_type,return_type,credit_note_amount,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (rtv_num, gr_data['id'], None, gr_data['supplier_id'],
                             gr_data['item_name'], ret_qty, reason_rtv,
                             defect_type, return_type, credit_amt, '반품요청'))
                        # 재고에서 차감
                        conn.execute("""UPDATE inventory SET stock_qty=MAX(0,stock_qty-?), system_qty=MAX(0,system_qty-?)
                            WHERE item_code=?""", (ret_qty, ret_qty, gr_data['item_name']))
                        conn.commit(); conn.close()
                        st.success(f"RTV {rtv_num} 등록! 크레딧 ₩{credit_amt:,.0f}"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("반품 이력")
        conn = get_db()
        df_rtv = pd.read_sql_query("""
            SELECT r.rtv_number AS RTV번호, s.name AS 공급사,
                   r.item_name AS 품목, r.return_qty AS 반품수량,
                   r.defect_type AS 불량유형, r.return_type AS 반품유형,
                   r.credit_note_amount AS 크레딧금액,
                   r.status AS 상태, r.created_at AS 등록일
            FROM return_to_vendor r LEFT JOIN suppliers s ON r.supplier_id=s.id
            ORDER BY r.id DESC""", conn)
        conn.close()
        if df_rtv.empty:
            st.info("반품 이력 없음")
        else:
            st.dataframe(df_rtv, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (반품(RTV)) ──────────────────────────
            if not df_rtv.empty if hasattr(df_rtv, 'empty') else df_rtv is not None:
                _row_opts_return_to_vendor = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM return_to_vendor ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_return_to_vendor[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_return_to_vendor:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_return_to_vendor = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_return_to_vendor.keys()),
                        key="_rbsel_return_to_vendor", label_visibility="collapsed"
                    )
                    _rb_id_return_to_vendor = _row_opts_return_to_vendor[_rb_sel_return_to_vendor]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_return_to_vendor"):
                        st.session_state[f"_edit_return_to_vendor"] = _rb_id_return_to_vendor
                        st.session_state[f"_del_return_to_vendor"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_return_to_vendor"):
                        st.session_state[f"_del_return_to_vendor"]  = _rb_id_return_to_vendor
                        st.session_state[f"_edit_return_to_vendor"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_return_to_vendor"):
                    _del_id_return_to_vendor = st.session_state[f"_del_return_to_vendor"]
                    st.warning(f"⚠️ ID **{_del_id_return_to_vendor}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_return_to_vendor"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM return_to_vendor WHERE id = ?", (_del_id_return_to_vendor,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_return_to_vendor"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_return_to_vendor"):
                        st.session_state[f"_del_return_to_vendor"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_return_to_vendor"):
                    _edit_id_return_to_vendor = st.session_state[f"_edit_return_to_vendor"]
                    try:
                        _cx_e = get_db()
                        _edit_row_return_to_vendor = dict(_cx_e.execute(
                            "SELECT * FROM return_to_vendor WHERE id=?", (_edit_id_return_to_vendor,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_return_to_vendor = {}
                    with st.expander(f"✏️ 반품(RTV) 수정 — ID {_edit_id_return_to_vendor}", expanded=True):
                        if not _edit_row_return_to_vendor:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_return_to_vendor = [c for c in _edit_row_return_to_vendor if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_return_to_vendor)))
                            _ecols = st.columns(_ncols)
                            _new_vals_return_to_vendor = {}
                            for _i, _fc in enumerate(_edit_fields_return_to_vendor):
                                _cv = _edit_row_return_to_vendor[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_return_to_vendor[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_return_to_vendor}_{_fc}_return_to_vendor")
                                else:
                                    _new_vals_return_to_vendor[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_return_to_vendor}_{_fc}_return_to_vendor")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_return_to_vendor"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_return_to_vendor])
                                _set_params = list(_new_vals_return_to_vendor.values()) + [_edit_id_return_to_vendor]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE return_to_vendor SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_return_to_vendor"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_return_to_vendor"):
                                st.session_state[f"_edit_return_to_vendor"] = None; st.rerun()

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("총 반품건", len(df_rtv))
            col_m2.metric("총 반품수량", int(df_rtv['반품수량'].sum()))
            col_m3.metric("크레딧 합계", f"₩{df_rtv['크레딧금액'].sum():,.0f}")
        st.divider()
        st.subheader("⚡ 반품 상태 변경")
        conn = get_db()
        rtvs_pend = [dict(r) for r in conn.execute(
            "SELECT id, rtv_number, item_name, status FROM return_to_vendor WHERE status != '처리완료'").fetchall()]
        conn.close()
        if rtvs_pend:
            rtv_map = {f"{r['rtv_number']} - {r['item_name']} ({r['status']})": r['id'] for r in rtvs_pend}
            sel_rtv = st.selectbox("반품 선택", list(rtv_map.keys()))
            col_r1, col_r2 = st.columns(2)
            new_rtv_st = col_r1.selectbox("변경 상태", ["반품요청","수거중","수거완료","크레딧발행","처리완료"])
            approved_by_rtv = col_r2.text_input("처리자")
            if st.button("🔄 상태 변경", use_container_width=True, key="rtv_status"):
                conn = get_db()
                conn.execute("UPDATE return_to_vendor SET status=?,approved_by=? WHERE id=?",
                             (new_rtv_st, approved_by_rtv, rtv_map[sel_rtv]))
                conn.commit(); conn.close()
                st.success("완료!"); st.rerun()


# ── 14. 이동평균단가 ──────────────────────────────────────
with tabs[13]:
    st.subheader("📈 이동평균단가 (Moving Average Price)")
    st.caption("입고 시마다 자동 계산된 재고 평균단가 이력 — 재고자산 가치 평가 기준")
    conn = get_db()
    df_map = pd.read_sql_query("""
        SELECT item_code AS 자재코드, item_name AS 자재명,
               prev_qty AS 이전재고, ROUND(prev_avg_price,2) AS 이전평균단가,
               incoming_qty AS 입고수량, ROUND(incoming_price,2) AS 입고단가,
               new_qty AS 신규재고, ROUND(new_avg_price,2) AS 신규평균단가,
               reference AS 참조번호, calculated_at AS 계산일시
        FROM moving_avg_price ORDER BY id DESC""", conn)
    conn.close()
    if df_map.empty:
        st.info("이동평균단가 이력 없음 — 입고(GR) 등록 시 자동 생성됩니다")
    else:
        col_f1, col_f2 = st.columns(2)
        search_map = col_f1.text_input("🔍 자재 검색")
        if search_map:
            df_map = df_map[df_map['자재명'].str.contains(search_map, na=False) | df_map['자재코드'].str.contains(search_map, na=False)]

        # 자재별 현재 평균단가 요약
        st.subheader("📊 자재별 현재 이동평균단가")
        conn = get_db()
        df_current = pd.read_sql_query("""
            SELECT item_code AS 자재코드, item_name AS 자재명,
                   new_qty AS 현재고수량, ROUND(new_avg_price,2) AS 현재평균단가,
                   ROUND(new_qty*new_avg_price,0) AS 재고자산가치,
                   calculated_at AS 최종갱신
            FROM moving_avg_price
            WHERE id IN (SELECT MAX(id) FROM moving_avg_price GROUP BY item_code)
            ORDER BY new_qty*new_avg_price DESC""", conn)
        conn.close()
        st.dataframe(df_current, use_container_width=True, hide_index=True)
        if not df_current.empty:
            total_val = df_current['재고자산가치'].sum()
            col_v1, col_v2, col_v3 = st.columns(3)
            col_v1.metric("관리 자재수", len(df_current))
            col_v2.metric("총 재고자산가치", f"₩{total_val:,.0f}")
            col_v3.metric("평균 단가 자재", f"{len(df_current[df_current['현재평균단가']>0])}개")

        st.divider()
        st.subheader("📋 단가 변동 이력")

        # 자재별 이력 조회
        items_map = df_map['자재코드'].unique().tolist()
        if items_map:
            sel_item_map = st.selectbox("자재 선택", items_map)
            df_item_hist = df_map[df_map['자재코드'] == sel_item_map]
            st.dataframe(df_item_hist, use_container_width=True, hide_index=True)

            if len(df_item_hist) >= 2:
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_item_hist['계산일시'].tolist()[::-1],
                    y=df_item_hist['신규평균단가'].tolist()[::-1],
                    mode='lines+markers', name='이동평균단가',
                    line=dict(color='#3b82f6', width=2)
                ))
                fig.update_layout(title=f"{sel_item_map} 이동평균단가 추이",
                                  xaxis_title="날짜", yaxis_title="단가",
                                  height=300, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig, use_container_width=True)


# ── 15. 송장검증 ──────────────────────────────────────
with tabs[14]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("송장검증 (3-Way Match)")
        st.caption("PO금액 ↔ GR금액 ↔ 공급사 인보이스 금액 대사")
        conn = get_db()
        pos_iv = [dict(r) for r in conn.execute("""
            SELECT p.id, p.po_number, p.item_name, p.quantity, p.unit_price,
                   COALESCE(r.received_qty,0) AS rcv
            FROM purchase_orders p LEFT JOIN po_receipt_summary r ON p.id=r.po_id
            WHERE p.status IN ('입고완료','납품중')""").fetchall()]
        conn.close()
        with st.form("iv_form", clear_on_submit=True):
            if pos_iv:
                po_iv_map = {f"{p['po_number']} - {p['item_name']}": p for p in pos_iv}
                sel_po_iv = st.selectbox("PO 선택 *", list(po_iv_map.keys()))
                p_data = po_iv_map[sel_po_iv]
                po_amt = p_data['quantity'] * p_data['unit_price']
                gr_amt = p_data['rcv'] * p_data['unit_price']
                col_a, col_b = st.columns(2)
                col_a.metric("PO 금액", f"₩{po_amt:,.0f}")
                col_b.metric("GR 금액", f"₩{gr_amt:,.0f}")
                iv_supplier = st.text_input("공급사 인보이스 번호")
                col_c, col_d = st.columns(2)
                iv_supply  = col_c.number_input("공급가액", min_value=0.0, value=float(gr_amt), format="%.0f")
                iv_tax     = col_d.number_input("부가세", min_value=0.0, value=float(gr_amt*0.1), format="%.0f")
                iv_total   = iv_supply + iv_tax
                st.info(f"인보이스 총액: ₩{iv_total:,.0f}")
                variance = abs(gr_amt - iv_supply)
                var_pct = variance / gr_amt * 100 if gr_amt > 0 else 0
                if var_pct <= 0:
                    match_result = "완전일치"
                elif var_pct <= 5:
                    match_result = "허용범위 내"
                else:
                    match_result = "불일치"
                col_e, col_f = st.columns(2)
                col_e.metric("차이금액", f"₩{variance:,.0f}")
                col_f.metric("차이율", f"{var_pct:.1f}%",
                             delta_color="normal" if var_pct<=5 else "inverse")
                iv_status = col_e.selectbox("검증결과", ["검토중","승인","보류","반려"])
                note_iv = st.text_area("비고", height=50)
            else:
                st.info("송장검증 가능한 PO 없음")
                p_data = None; po_amt = 0; gr_amt = 0
                iv_supplier = ""; iv_supply = 0; iv_tax = 0; iv_total = 0
                match_result = ""; variance = 0; var_pct = 0
                iv_status = "검토중"; note_iv = ""
                sel_po_iv = None
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not pos_iv:
                    st.error("대상 없음")
                else:
                    try:
                        iv_num = gen_number("IV")
                        conn = get_db()
                        conn.execute("""INSERT INTO invoice_verifications
                            (iv_number,po_id,gr_id,supplier_invoice_no,
                             po_amount,gr_amount,invoice_amount,variance_amount,
                             match_result,status,note)
                            VALUES(?,?,NULL,?,?,?,?,?,?,?,?)""",
                            (iv_num, p_data['id'], iv_supplier,
                             po_amt, gr_amt, iv_total, variance,
                             match_result, iv_status, note_iv))
                        conn.commit(); conn.close()
                        st.success(f"IV {iv_num} 등록! 결과: {match_result}"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("송장검증 목록")
        conn = get_db()
        df_iv = pd.read_sql_query("""
            SELECT i.iv_number AS IV번호, p.po_number AS PO번호,
                   p.item_name AS 품목,
                   ROUND(i.po_amount,0) AS PO금액,
                   ROUND(i.gr_amount,0) AS GR금액,
                   ROUND(i.invoice_amount,0) AS 인보이스금액,
                   ROUND(i.variance_amount,0) AS 차이금액,
                   i.match_result AS 대사결과, i.status AS 상태,
                   i.created_at AS 등록일
            FROM invoice_verifications i LEFT JOIN purchase_orders p ON i.po_id=p.id
            ORDER BY i.id DESC""", conn)
        conn.close()
        if df_iv.empty:
            st.info("송장검증 이력 없음")
        else:
            def iv_color(row):
                if row['대사결과'] == '불일치': return ['background-color:#fee2e2']*len(row)
                if row['대사결과'] == '허용범위 내': return ['background-color:#fef3c7']*len(row)
                if row['대사결과'] == '완전일치': return ['background-color:#d1fae5']*len(row)
                return ['']*len(row)
            st.dataframe(df_iv.style.apply(iv_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (invoice_verifications) ──────────────────────────
            if not df_iv.empty if hasattr(df_iv, 'empty') else df_iv is not None:
                _row_opts_invoice_verifications = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM invoice_verifications ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('supplier','')}"
                        _row_opts_invoice_verifications[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_invoice_verifications:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_invoice_verifications = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_invoice_verifications.keys()),
                        key="_rbsel_invoice_verifications", label_visibility="collapsed"
                    )
                    _rb_id_invoice_verifications = _row_opts_invoice_verifications[_rb_sel_invoice_verifications]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_invoice_verifications"):
                        st.session_state[f"_edit_invoice_verifications"] = _rb_id_invoice_verifications
                        st.session_state[f"_del_invoice_verifications"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_invoice_verifications"):
                        st.session_state[f"_del_invoice_verifications"]  = _rb_id_invoice_verifications
                        st.session_state[f"_edit_invoice_verifications"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_invoice_verifications"):
                    _del_id_invoice_verifications = st.session_state[f"_del_invoice_verifications"]
                    st.warning(f"⚠️ ID **{_del_id_invoice_verifications}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_invoice_verifications"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM invoice_verifications WHERE id = ?", (_del_id_invoice_verifications,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_invoice_verifications"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_invoice_verifications"):
                        st.session_state[f"_del_invoice_verifications"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_invoice_verifications"):
                    _edit_id_invoice_verifications = st.session_state[f"_edit_invoice_verifications"]
                    try:
                        _cx_e = get_db()
                        _edit_row_invoice_verifications = dict(_cx_e.execute(
                            "SELECT * FROM invoice_verifications WHERE id=?", (_edit_id_invoice_verifications,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_invoice_verifications = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_invoice_verifications}", expanded=True):
                        if not _edit_row_invoice_verifications:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_invoice_verifications = [c for c in _edit_row_invoice_verifications if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_invoice_verifications)))
                            _ecols = st.columns(_ncols)
                            _new_vals_invoice_verifications = {}
                            for _i, _fc in enumerate(_edit_fields_invoice_verifications):
                                _cv = _edit_row_invoice_verifications[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_invoice_verifications[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_invoice_verifications}_{_fc}_invoice_verifications")
                                else:
                                    _new_vals_invoice_verifications[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_invoice_verifications}_{_fc}_invoice_verifications")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_invoice_verifications"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_invoice_verifications])
                                _set_params = list(_new_vals_invoice_verifications.values()) + [_edit_id_invoice_verifications]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE invoice_verifications SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_invoice_verifications"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_invoice_verifications"):
                                st.session_state[f"_edit_invoice_verifications"] = None; st.rerun()

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("총 검증건", len(df_iv))
            col_m2.metric("완전일치", len(df_iv[df_iv['대사결과']=='완전일치']))
            col_m3.metric("불일치", len(df_iv[df_iv['대사결과']=='불일치']), delta_color="inverse")


# ── 16. 세금계산서 ──────────────────────────────────────
with tabs[15]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("🧾 매입 세금계산서 등록")
        st.caption("송장검증 완료 후 공급사로부터 수취한 세금계산서")
        conn = get_db()
        ivs = [dict(r) for r in conn.execute("""
            SELECT i.id, i.iv_number, p.po_number, p.item_name, i.invoice_amount,
                   s.name AS supplier_name, s.id AS supplier_id
            FROM invoice_verifications i
            LEFT JOIN purchase_orders p ON i.po_id=p.id
            LEFT JOIN suppliers s ON p.supplier_id=s.id
            WHERE i.status='승인'""").fetchall()]
        conn.close()
        iv_map = {f"{iv['iv_number']} - {iv['item_name']} ({iv['supplier_name']})": iv for iv in ivs}
        with st.form("tax_inv_form", clear_on_submit=True):
            sel_iv = st.selectbox("송장검증 선택 *", list(iv_map.keys()) if iv_map else ["승인된 IV 없음"])
            iv_data = iv_map.get(sel_iv)
            col_a, col_b = st.columns(2)
            supplier_name_ti = col_a.text_input("공급사", value=iv_data['supplier_name'] if iv_data else "")
            tax_inv_no = col_b.text_input("세금계산서 번호")
            supply_amt = st.number_input("공급가액 *", min_value=0.0,
                value=float(iv_data['invoice_amount']*10/11) if iv_data else 0.0, format="%.0f")
            tax_amt = supply_amt * 0.1
            total_amt = supply_amt + tax_amt
            col_c, col_d = st.columns(2)
            col_c.metric("부가세 (10%)", f"₩{tax_amt:,.0f}")
            col_d.metric("합계금액", f"₩{total_amt:,.0f}")
            col_e, col_f = st.columns(2)
            issue_date = col_e.date_input("발행일")
            payment_terms_ti = col_f.selectbox("결제조건", ["현금","30일","60일","90일"])
            days_map = {"현금": 0, "30일": 30, "60일": 60, "90일": 90}
            due_date = (datetime.strptime(str(issue_date), "%Y-%m-%d") + timedelta(days=days_map[payment_terms_ti])).strftime("%Y-%m-%d")
            st.info(f"💳 지급 예정일: {due_date}")
            payment_method = st.selectbox("지급방법", ["계좌이체","어음","카드","현금"])
            note_ti = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if supply_amt == 0:
                    st.error("공급가액 필수")
                else:
                    try:
                        ti_num = gen_number("TI")
                        conn = get_db()
                        conn.execute("""INSERT INTO purchase_tax_invoices
                            (ti_number,iv_id,po_id,supplier_id,supplier_name,tax_invoice_no,
                             supply_amount,tax_amount,total_amount,issue_date,
                             payment_terms,due_date,payment_method,payment_status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'미지급',?)""",
                            (ti_num,
                             iv_data['id'] if iv_data else None,
                             iv_data['id'] if iv_data else None,
                             iv_data['supplier_id'] if iv_data else None,
                             supplier_name_ti, tax_inv_no,
                             supply_amt, tax_amt, total_amt, str(issue_date),
                             payment_terms_ti, due_date, payment_method, note_ti))
                        ti_id = conn.execute("SELECT id FROM purchase_tax_invoices WHERE ti_number=?", (ti_num,)).fetchone()['id']
                        conn.execute("""INSERT INTO payment_schedule
                            (tax_inv_id,ti_number,supplier_name,payment_amount,due_date,payment_method,status)
                            VALUES(?,?,?,?,?,?,'미지급')""",
                            (ti_id, ti_num, supplier_name_ti, total_amt, due_date, payment_method))
                        conn.commit(); conn.close()
                        st.success(f"TI {ti_num} 등록! 지급예정일 {due_date}"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("세금계산서 목록")
        conn = get_db()
        df_ti = pd.read_sql_query("""
            SELECT ti_number AS TI번호, supplier_name AS 공급사,
                   tax_invoice_no AS 계산서번호,
                   ROUND(supply_amount,0) AS 공급가액,
                   ROUND(tax_amount,0) AS 부가세,
                   ROUND(total_amount,0) AS 합계,
                   issue_date AS 발행일, due_date AS 지급예정일,
                   payment_method AS 지급방법, payment_status AS 지급상태
            FROM purchase_tax_invoices ORDER BY id DESC""", conn)
        conn.close()
        if df_ti.empty:
            st.info("세금계산서 없음")
        else:
            today_ti = datetime.now().strftime("%Y-%m-%d")
            def ti_color(row):
                if row['지급상태'] == '지급완료': return ['background-color:#d1fae5']*len(row)
                if row['지급예정일'] < today_ti: return ['background-color:#fee2e2']*len(row)
                if row['지급예정일'] <= (datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d"):
                    return ['background-color:#fef3c7']*len(row)
                return ['']*len(row)
            st.dataframe(df_ti.style.apply(ti_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (세금계산서) ──────────────────────────
            if not df_ti.empty if hasattr(df_ti, 'empty') else df_ti is not None:
                _row_opts_purchase_tax_invoices = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 공급사명 FROM purchase_tax_invoices ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('공급사명','')}"
                        _row_opts_purchase_tax_invoices[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_purchase_tax_invoices:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_purchase_tax_invoices = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_purchase_tax_invoices.keys()),
                        key="_rbsel_purchase_tax_invoices", label_visibility="collapsed"
                    )
                    _rb_id_purchase_tax_invoices = _row_opts_purchase_tax_invoices[_rb_sel_purchase_tax_invoices]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_purchase_tax_invoices"):
                        st.session_state[f"_edit_purchase_tax_invoices"] = _rb_id_purchase_tax_invoices
                        st.session_state[f"_del_purchase_tax_invoices"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_purchase_tax_invoices"):
                        st.session_state[f"_del_purchase_tax_invoices"]  = _rb_id_purchase_tax_invoices
                        st.session_state[f"_edit_purchase_tax_invoices"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_purchase_tax_invoices"):
                    _del_id_purchase_tax_invoices = st.session_state[f"_del_purchase_tax_invoices"]
                    st.warning(f"⚠️ ID **{_del_id_purchase_tax_invoices}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_purchase_tax_invoices"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM purchase_tax_invoices WHERE id = ?", (_del_id_purchase_tax_invoices,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_purchase_tax_invoices"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_purchase_tax_invoices"):
                        st.session_state[f"_del_purchase_tax_invoices"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_purchase_tax_invoices"):
                    _edit_id_purchase_tax_invoices = st.session_state[f"_edit_purchase_tax_invoices"]
                    try:
                        _cx_e = get_db()
                        _edit_row_purchase_tax_invoices = dict(_cx_e.execute(
                            "SELECT * FROM purchase_tax_invoices WHERE id=?", (_edit_id_purchase_tax_invoices,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_purchase_tax_invoices = {}
                    with st.expander(f"✏️ 세금계산서 수정 — ID {_edit_id_purchase_tax_invoices}", expanded=True):
                        if not _edit_row_purchase_tax_invoices:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_purchase_tax_invoices = [c for c in _edit_row_purchase_tax_invoices if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_purchase_tax_invoices)))
                            _ecols = st.columns(_ncols)
                            _new_vals_purchase_tax_invoices = {}
                            for _i, _fc in enumerate(_edit_fields_purchase_tax_invoices):
                                _cv = _edit_row_purchase_tax_invoices[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_purchase_tax_invoices[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_purchase_tax_invoices}_{_fc}_purchase_tax_invoices")
                                else:
                                    _new_vals_purchase_tax_invoices[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_purchase_tax_invoices}_{_fc}_purchase_tax_invoices")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_purchase_tax_invoices"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_purchase_tax_invoices])
                                _set_params = list(_new_vals_purchase_tax_invoices.values()) + [_edit_id_purchase_tax_invoices]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE purchase_tax_invoices SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_purchase_tax_invoices"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_purchase_tax_invoices"):
                                st.session_state[f"_edit_purchase_tax_invoices"] = None; st.rerun()

            unpaid = df_ti[df_ti['지급상태']=='미지급']
            overdue = unpaid[unpaid['지급예정일'] < today_ti]
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("미지급 합계", f"₩{unpaid['합계'].sum():,.0f}")
            col_m2.metric("연체 건수", len(overdue), delta_color="inverse")
            col_m3.metric("지급완료", len(df_ti[df_ti['지급상태']=='지급완료']))


# ── 17. 지급관리 ──────────────────────────────────────
with tabs[16]:
    st.subheader("💰 지급 스케줄 관리")
    st.caption("세금계산서 기반 지급 예정 관리 — 연체 알림, 지급 완료 처리")
    conn = get_db()
    df_pay = pd.read_sql_query("""
        SELECT ps.id, ps.ti_number AS TI번호, ps.supplier_name AS 공급사,
               ROUND(ps.payment_amount,0) AS 지급금액,
               ps.due_date AS 지급예정일, ps.payment_method AS 지급방법,
               ps.status AS 상태, ps.paid_at AS 지급일시
        FROM payment_schedule ps ORDER BY ps.due_date ASC""", conn)
    conn.close()
    today_pay = datetime.now().strftime("%Y-%m-%d")
    soon_pay = (datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d")
    overdue_pay = df_pay[(df_pay['상태']=='미지급') & (df_pay['지급예정일'] < today_pay)]
    soon_due_pay = df_pay[(df_pay['상태']=='미지급') & (df_pay['지급예정일'] >= today_pay) & (df_pay['지급예정일'] <= soon_pay)]
    if not overdue_pay.empty:
        st.error(f"🔴 연체 {len(overdue_pay)}건 | 합계 ₩{overdue_pay['지급금액'].sum():,.0f}")
    if not soon_due_pay.empty:
        st.warning(f"🟡 7일 내 지급 예정 {len(soon_due_pay)}건 | 합계 ₩{soon_due_pay['지급금액'].sum():,.0f}")

    if df_pay.empty:
        st.info("지급 스케줄 없음")
    else:
        tab_p1, tab_p2, tab_p3 = st.tabs(["전체", "미지급", "완료"])
        def pay_color(row):
            if row['상태'] == '지급완료': return ['background-color:#d1fae5']*len(row)
            if row['지급예정일'] < today_pay: return ['background-color:#fee2e2']*len(row)
            if row['지급예정일'] <= soon_pay: return ['background-color:#fef3c7']*len(row)
            return ['']*len(row)
        with tab_p1:
            st.dataframe(df_pay.drop(columns=['id']).style.apply(pay_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (payment_schedule) ──────────────────────────
            if not df_pay.empty if hasattr(df_pay, 'empty') else df_pay is not None:
                _row_opts_payment_schedule = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM payment_schedule ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('supplier','')}"
                        _row_opts_payment_schedule[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_payment_schedule:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_payment_schedule = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_payment_schedule.keys()),
                        key="_rbsel_payment_schedule", label_visibility="collapsed"
                    )
                    _rb_id_payment_schedule = _row_opts_payment_schedule[_rb_sel_payment_schedule]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_payment_schedule"):
                        st.session_state[f"_edit_payment_schedule"] = _rb_id_payment_schedule
                        st.session_state[f"_del_payment_schedule"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_payment_schedule"):
                        st.session_state[f"_del_payment_schedule"]  = _rb_id_payment_schedule
                        st.session_state[f"_edit_payment_schedule"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_payment_schedule"):
                    _del_id_payment_schedule = st.session_state[f"_del_payment_schedule"]
                    st.warning(f"⚠️ ID **{_del_id_payment_schedule}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_payment_schedule"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM payment_schedule WHERE id = ?", (_del_id_payment_schedule,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_payment_schedule"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_payment_schedule"):
                        st.session_state[f"_del_payment_schedule"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_payment_schedule"):
                    _edit_id_payment_schedule = st.session_state[f"_edit_payment_schedule"]
                    try:
                        _cx_e = get_db()
                        _edit_row_payment_schedule = dict(_cx_e.execute(
                            "SELECT * FROM payment_schedule WHERE id=?", (_edit_id_payment_schedule,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_payment_schedule = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_payment_schedule}", expanded=True):
                        if not _edit_row_payment_schedule:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_payment_schedule = [c for c in _edit_row_payment_schedule if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_payment_schedule)))
                            _ecols = st.columns(_ncols)
                            _new_vals_payment_schedule = {}
                            for _i, _fc in enumerate(_edit_fields_payment_schedule):
                                _cv = _edit_row_payment_schedule[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_payment_schedule[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_payment_schedule}_{_fc}_payment_schedule")
                                else:
                                    _new_vals_payment_schedule[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_payment_schedule}_{_fc}_payment_schedule")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_payment_schedule"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_payment_schedule])
                                _set_params = list(_new_vals_payment_schedule.values()) + [_edit_id_payment_schedule]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE payment_schedule SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_payment_schedule"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_payment_schedule"):
                                st.session_state[f"_edit_payment_schedule"] = None; st.rerun()
        with tab_p2:
            df_unpaid = df_pay[df_pay['상태']=='미지급']
            st.dataframe(df_unpaid.drop(columns=['id']).style.apply(pay_color, axis=1),
                         use_container_width=True, hide_index=True)
        with tab_p3:
            df_paid = df_pay[df_pay['상태']=='지급완료']
            st.dataframe(df_paid.drop(columns=['id']), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("✅ 지급 완료 처리")
    conn = get_db()
    unpaid_list = [dict(r) for r in conn.execute("""
        SELECT id, ti_number, supplier_name, payment_amount, due_date
        FROM payment_schedule WHERE status='미지급'
        ORDER BY due_date ASC""").fetchall()]
    conn.close()
    if not unpaid_list:
        st.success("미지급 건 없음")
    else:
        pay_opts = {f"{p['ti_number']} - {p['supplier_name']} ₩{p['payment_amount']:,.0f} ({p['due_date']})": p
                   for p in unpaid_list}
        sel_pay = st.selectbox("지급할 건 선택", list(pay_opts.keys()))
        pay_obj = pay_opts[sel_pay]
        col_p1, col_p2 = st.columns(2)
        actual_pay_amt = col_p1.number_input("실지급액", min_value=0.0,
                                              value=float(pay_obj['payment_amount']), format="%.0f")
        pay_note = col_p2.text_input("비고")
        if st.button("💳 지급 완료 처리", use_container_width=True, key="pay_complete"):
            conn = get_db()
            conn.execute("""UPDATE payment_schedule SET status='지급완료',
                paid_at=datetime('now','localtime') WHERE id=?""", (pay_obj['id'],))
            conn.execute("""UPDATE purchase_tax_invoices SET payment_status='지급완료',
                paid_at=datetime('now','localtime') WHERE ti_number=?""", (pay_obj['ti_number'],))
            conn.commit(); conn.close()
            st.success(f"지급 완료! ₩{actual_pay_amt:,.0f}"); st.rerun()

    st.divider()
    st.subheader("📊 공급사별 미지급 현황")
    conn = get_db()
    df_sup_pay = pd.read_sql_query("""
        SELECT supplier_name AS 공급사, COUNT(*) AS 건수,
               ROUND(SUM(payment_amount),0) AS 미지급합계,
               MIN(due_date) AS 최근만기일
        FROM payment_schedule WHERE status='미지급'
        GROUP BY supplier_name ORDER BY SUM(payment_amount) DESC""", conn)
    conn.close()
    if not df_sup_pay.empty:
        st.dataframe(df_sup_pay, use_container_width=True, hide_index=True)


# ── 18. 공급사 평가 ──────────────────────────────────────
with tabs[17]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("공급사 평가 등록")
        st.caption("납기·품질·가격·서비스 각 25점 만점 (100점 총점)")
        conn = get_db()
        sups_ev = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers WHERE status='활성'").fetchall()]
        conn.close()
        with st.form("eval_form", clear_on_submit=True):
            sup_ev_opts = {s['name']: s['id'] for s in sups_ev}
            sel_sup_ev = st.selectbox("공급사 *", list(sup_ev_opts.keys()) if sup_ev_opts else ["없음"])
            eval_period = st.text_input("평가기간 (예: 2024-Q1)")
            st.markdown("**평가 항목 (각 25점)**")
            col_a, col_b = st.columns(2)
            delivery_score = col_a.slider("납기준수", 0, 25, 20)
            quality_score  = col_b.slider("품질수준", 0, 25, 20)
            col_c, col_d = st.columns(2)
            price_score    = col_c.slider("가격경쟁력", 0, 25, 20)
            service_score  = col_d.slider("서비스", 0, 25, 20)
            total_score = delivery_score + quality_score + price_score + service_score
            grade = "A" if total_score >= 90 else ("B" if total_score >= 75 else ("C" if total_score >= 60 else "D"))
            col_g1, col_g2 = st.columns(2)
            col_g1.metric("총점", f"{total_score}점")
            col_g2.metric("등급", grade)
            comment_ev = st.text_area("평가 코멘트", height=70)
            evaluator = st.text_input("평가자")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not sup_ev_opts:
                    st.error("공급사 없음")
                else:
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO supplier_evaluations
                            (supplier_id,evaluation_period,delivery_score,quality_score,
                             price_score,service_score,total_score,grade,evaluator,comment)
                            VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (sup_ev_opts[sel_sup_ev], eval_period,
                             delivery_score, quality_score, price_score, service_score,
                             total_score, grade, evaluator, comment_ev))
                        conn.commit(); conn.close()
                        st.success(f"평가 등록! {total_score}점 ({grade}등급)"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("공급사 평가 현황")
        conn = get_db()
        df_ev = pd.read_sql_query("""
            SELECT s.name AS 공급사, e.evaluation_period AS 평가기간,
                   e.delivery_score AS 납기, e.quality_score AS 품질,
                   e.price_score AS 가격, e.service_score AS 서비스,
                   e.total_score AS 총점, e.grade AS 등급,
                   e.evaluator AS 평가자, e.created_at AS 평가일
            FROM supplier_evaluations e LEFT JOIN suppliers s ON e.supplier_id=s.id
            ORDER BY e.id DESC""", conn)
        conn.close()
        if df_ev.empty:
            st.info("평가 없음")
        else:
            def ev_color(row):
                g = row.get('등급','')
                if g == 'A': return ['background-color:#d1fae5']*len(row)
                if g == 'B': return ['background-color:#e0f2fe']*len(row)
                if g == 'C': return ['background-color:#fef3c7']*len(row)
                return ['background-color:#fee2e2']*len(row)
            st.dataframe(df_ev.style.apply(ev_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (공급사평가) ──────────────────────────
            if not df_ev.empty if hasattr(df_ev, 'empty') else df_ev is not None:
                _row_opts_supplier_evaluations = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 공급사명 FROM supplier_evaluations ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('공급사명','')}"
                        _row_opts_supplier_evaluations[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_supplier_evaluations:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_supplier_evaluations = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_supplier_evaluations.keys()),
                        key="_rbsel_supplier_evaluations", label_visibility="collapsed"
                    )
                    _rb_id_supplier_evaluations = _row_opts_supplier_evaluations[_rb_sel_supplier_evaluations]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_supplier_evaluations"):
                        st.session_state[f"_edit_supplier_evaluations"] = _rb_id_supplier_evaluations
                        st.session_state[f"_del_supplier_evaluations"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_supplier_evaluations"):
                        st.session_state[f"_del_supplier_evaluations"]  = _rb_id_supplier_evaluations
                        st.session_state[f"_edit_supplier_evaluations"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_supplier_evaluations"):
                    _del_id_supplier_evaluations = st.session_state[f"_del_supplier_evaluations"]
                    st.warning(f"⚠️ ID **{_del_id_supplier_evaluations}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_supplier_evaluations"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM supplier_evaluations WHERE id = ?", (_del_id_supplier_evaluations,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_supplier_evaluations"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_supplier_evaluations"):
                        st.session_state[f"_del_supplier_evaluations"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_supplier_evaluations"):
                    _edit_id_supplier_evaluations = st.session_state[f"_edit_supplier_evaluations"]
                    try:
                        _cx_e = get_db()
                        _edit_row_supplier_evaluations = dict(_cx_e.execute(
                            "SELECT * FROM supplier_evaluations WHERE id=?", (_edit_id_supplier_evaluations,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_supplier_evaluations = {}
                    with st.expander(f"✏️ 공급사평가 수정 — ID {_edit_id_supplier_evaluations}", expanded=True):
                        if not _edit_row_supplier_evaluations:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_supplier_evaluations = [c for c in _edit_row_supplier_evaluations if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_supplier_evaluations)))
                            _ecols = st.columns(_ncols)
                            _new_vals_supplier_evaluations = {}
                            for _i, _fc in enumerate(_edit_fields_supplier_evaluations):
                                _cv = _edit_row_supplier_evaluations[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_supplier_evaluations[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_supplier_evaluations}_{_fc}_supplier_evaluations")
                                else:
                                    _new_vals_supplier_evaluations[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_supplier_evaluations}_{_fc}_supplier_evaluations")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_supplier_evaluations"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_supplier_evaluations])
                                _set_params = list(_new_vals_supplier_evaluations.values()) + [_edit_id_supplier_evaluations]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE supplier_evaluations SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_supplier_evaluations"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_supplier_evaluations"):
                                st.session_state[f"_edit_supplier_evaluations"] = None; st.rerun()

        st.divider()
        st.subheader("📊 공급사별 평균 총점")
        conn = get_db()
        df_ev_avg = pd.read_sql_query("""
            SELECT s.name AS 공급사,
                   ROUND(AVG(e.delivery_score),1) AS 평균납기,
                   ROUND(AVG(e.quality_score),1) AS 평균품질,
                   ROUND(AVG(e.price_score),1) AS 평균가격,
                   ROUND(AVG(e.service_score),1) AS 평균서비스,
                   ROUND(AVG(e.total_score),1) AS 평균총점,
                   COUNT(*) AS 평가횟수
            FROM supplier_evaluations e LEFT JOIN suppliers s ON e.supplier_id=s.id
            GROUP BY e.supplier_id ORDER BY AVG(e.total_score) DESC""", conn)
        conn.close()
        if not df_ev_avg.empty:
            st.dataframe(df_ev_avg, use_container_width=True, hide_index=True)


# ── 19. 구매 KPI ──────────────────────────────────────
with tabs[18]:
    st.subheader("📊 구매 KPI 대시보드")
    conn = get_db()
    total_po_amt = conn.execute("SELECT COALESCE(SUM(quantity*unit_price),0) FROM purchase_orders WHERE status!='취소'").fetchone()[0]
    po_count = conn.execute("SELECT COUNT(*) FROM purchase_orders WHERE status!='취소'").fetchone()[0]
    gr_count = conn.execute("SELECT COUNT(*) FROM goods_receipts").fetchone()[0]
    iv_approved = conn.execute("SELECT COUNT(*) FROM invoice_verifications WHERE status='승인'").fetchone()[0]
    sup_avg_score = conn.execute("SELECT ROUND(AVG(total_score),1) FROM supplier_evaluations").fetchone()[0]
    overdue_pay_cnt = conn.execute(
        f"SELECT COUNT(*) FROM payment_schedule WHERE status='미지급' AND due_date < date('now')").fetchone()[0]
    rtv_count = conn.execute("SELECT COUNT(*) FROM return_to_vendor").fetchone()[0]

    # 납기준수율
    on_time = conn.execute("""
        SELECT COUNT(*) FROM goods_receipts g JOIN purchase_orders p ON g.po_id=p.id
        WHERE p.delivery_date >= date(g.created_at)""").fetchone()[0]
    total_gr_with_date = conn.execute("""
        SELECT COUNT(*) FROM goods_receipts g JOIN purchase_orders p ON g.po_id=p.id
        WHERE p.delivery_date IS NOT NULL AND p.delivery_date != ''""").fetchone()[0]
    on_time_rate = round(on_time / total_gr_with_date * 100, 1) if total_gr_with_date > 0 else 0

    # 평균 불량률
    avg_defect = conn.execute("""
        SELECT ROUND(SUM(rejected_qty)*100.0/NULLIF(SUM(received_qty),0),1) FROM goods_receipts""").fetchone()[0] or 0

    # 단가절감률 (표준단가 vs 실발주단가)
    savings = conn.execute("""
        SELECT ROUND((1 - AVG(p.unit_price/NULLIF(m.standard_price,0)))*100,1)
        FROM purchase_orders p JOIN materials m ON p.material_id=m.id
        WHERE m.standard_price > 0 AND p.status!='취소'""").fetchone()[0] or 0

    conn.close()

    # 핵심 KPI 카드
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 발주금액", f"₩{total_po_amt:,.0f}")
    col2.metric("발주건수", f"{po_count}건")
    col3.metric("입고건수", f"{gr_count}건")
    col4.metric("납기준수율", f"{on_time_rate}%")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("송장검증 승인", f"{iv_approved}건")
    col6.metric("평균 공급사 평점", f"{sup_avg_score or 0:.1f}점")
    col7.metric("지급 연체", f"{overdue_pay_cnt}건", delta_color="inverse")
    col8.metric("평균 불량률", f"{avg_defect:.1f}%", delta_color="inverse")

    col9, col10 = st.columns(4)[:2]
    col9.metric("단가절감률", f"{savings:.1f}%")
    col10.metric("반품(RTV)", f"{rtv_count}건", delta_color="inverse")

    st.divider()

    conn = get_db()
    try:
        import plotly.graph_objects as go
        import plotly.express as px

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader("공급사별 발주금액")
            df_sup_po = pd.read_sql_query("""
                SELECT s.name AS 공급사, ROUND(SUM(p.quantity*p.unit_price),0) AS 발주금액
                FROM purchase_orders p LEFT JOIN suppliers s ON p.supplier_id=s.id
                WHERE p.status!='취소' GROUP BY s.id ORDER BY 발주금액 DESC LIMIT 10""", conn)
            if not df_sup_po.empty:
                fig = px.bar(df_sup_po, x='공급사', y='발주금액', color='발주금액',
                             color_continuous_scale='Blues')
                fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        with col_chart2:
            st.subheader("품목별 발주금액 TOP 10")
            df_item_po = pd.read_sql_query("""
                SELECT item_name AS 품목, ROUND(SUM(quantity*unit_price),0) AS 발주금액
                FROM purchase_orders WHERE status!='취소'
                GROUP BY item_name ORDER BY 발주금액 DESC LIMIT 10""", conn)
            if not df_item_po.empty:
                fig2 = px.pie(df_item_po, names='품목', values='발주금액', hole=0.4)
                fig2.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig2, use_container_width=True)

        st.subheader("월별 발주금액 추이")
        df_monthly = pd.read_sql_query("""
            SELECT substr(created_at,1,7) AS 월,
                   ROUND(SUM(quantity*unit_price),0) AS 발주금액,
                   COUNT(*) AS 발주건수
            FROM purchase_orders WHERE status!='취소'
            GROUP BY substr(created_at,1,7) ORDER BY 월""", conn)
        if not df_monthly.empty and len(df_monthly) > 1:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(x=df_monthly['월'], y=df_monthly['발주금액'],
                                  name='발주금액', marker_color='#3b82f6'))
            fig3.add_trace(go.Scatter(x=df_monthly['월'], y=df_monthly['발주건수'],
                                      name='건수', yaxis='y2', mode='lines+markers',
                                      line=dict(color='#f97316', width=2)))
            fig3.update_layout(
                yaxis2=dict(overlaying='y', side='right'),
                height=300, margin=dict(l=0,r=0,t=10,b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig3, use_container_width=True)

        col_chart3, col_chart4 = st.columns(2)
        with col_chart3:
            st.subheader("PO 상태 현황")
            df_po_st = pd.read_sql_query("""
                SELECT status AS 상태, COUNT(*) AS 건수 FROM purchase_orders GROUP BY status""", conn)
            if not df_po_st.empty:
                fig4 = px.pie(df_po_st, names='상태', values='건수')
                fig4.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig4, use_container_width=True)

        with col_chart4:
            st.subheader("공급사별 납기준수율")
            df_on_time = pd.read_sql_query("""
                SELECT s.name AS 공급사,
                       ROUND(SUM(CASE WHEN p.delivery_date >= date(g.created_at) THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS 납기준수율,
                       COUNT(*) AS 입고건수
                FROM goods_receipts g
                JOIN purchase_orders p ON g.po_id=p.id
                JOIN suppliers s ON p.supplier_id=s.id
                WHERE p.delivery_date IS NOT NULL AND p.delivery_date != ''
                GROUP BY s.id ORDER BY 납기준수율 DESC""", conn)
            if not df_on_time.empty:
                fig5 = px.bar(df_on_time, x='공급사', y='납기준수율',
                              color='납기준수율', color_continuous_scale='RdYlGn',
                              range_color=[0, 100])
                fig5.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig5, use_container_width=True)

    except ImportError:
        st.info("차트 표시를 위해 plotly 설치 필요: pip install plotly")
    finally:
        conn.close()

# ══════════════════════════════════════════════════════
# BI 분석 탭들
# ══════════════════════════════════════════════════════
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

def _no_plotly():
    st.warning("차트 표시를 위해 plotly 설치 필요: `pip install plotly`")

def _empty_fig(msg="데이터 없음"):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(size=13, color="#9ca3af"))
    fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                      plot_bgcolor="#f9fafb", paper_bgcolor="#f9fafb")
    return fig

# ── BI 공통 기간 필터 ─────────────────────────────────
with st.sidebar:
    st.divider()
    st.markdown("### 📊 분석 기간")
    bi_period = st.selectbox("기간", ["최근 1개월","최근 3개월","최근 6개월","최근 1년","전체"], key="mm_bi_period")
    bi_days = {"최근 1개월":30,"최근 3개월":90,"최근 6개월":180,"최근 1년":365,"전체":9999}[bi_period]
    bi_from = (datetime.now()-timedelta(days=bi_days)).strftime("%Y-%m-%d")


# ── BI-1: 공급사 분석 (대분류0 > 공급사 분석) ────────────
with tabs["bi_sup"]:
    if not HAS_PLOTLY:
        _no_plotly()
    else:
        conn = get_db()
        st.subheader("🏭 공급사 분석 대시보드")

        # KPI 카드
        sup_total = conn.execute("SELECT COUNT(*) FROM suppliers WHERE status='활성'").fetchone()[0]
        sup_eval_avg = conn.execute("SELECT ROUND(AVG(total_score),1) FROM supplier_evaluations").fetchone()[0] or 0
        rtv_total = conn.execute(f"SELECT COUNT(*) FROM return_to_vendor WHERE created_at>='{bi_from}'").fetchone()[0]
        on_time_rate = conn.execute(f"""
            SELECT ROUND(COUNT(CASE WHEN p.delivery_date>=date(g.created_at) THEN 1 END)*100.0/NULLIF(COUNT(*),0),1)
            FROM goods_receipts g JOIN purchase_orders p ON g.po_id=p.id
            WHERE p.delivery_date IS NOT NULL AND g.created_at>='{bi_from}'""").fetchone()[0] or 0

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("활성 공급사", f"{sup_total}개")
        c2.metric("평균 평점", f"{sup_eval_avg}점")
        c3.metric("납기준수율", f"{on_time_rate}%")
        c4.metric("반품건수", f"{rtv_total}건")
        st.divider()

        col_l, col_r = st.columns(2)
        with col_l:
            # 공급사별 발주금액
            df_sup_po = pd.read_sql_query(f"""
                SELECT s.name AS 공급사, ROUND(SUM(p.quantity*p.unit_price),0) AS 발주금액,
                       COUNT(p.id) AS 발주건수
                FROM purchase_orders p JOIN suppliers s ON p.supplier_id=s.id
                WHERE p.status!='취소' AND p.created_at>='{bi_from}'
                GROUP BY s.id ORDER BY 발주금액 DESC LIMIT 10""", conn)
            if not df_sup_po.empty:
                fig = px.bar(df_sup_po, y='공급사', x='발주금액', orientation='h',
                             color='발주금액', color_continuous_scale='Blues',
                             title="공급사별 발주금액 TOP10")
                fig.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.plotly_chart(_empty_fig(), use_container_width=True)

        with col_r:
            # 공급사별 납기준수율
            df_ontime = pd.read_sql_query(f"""
                SELECT s.name AS 공급사,
                       ROUND(SUM(CASE WHEN p.delivery_date>=date(g.created_at) THEN 1 ELSE 0 END)*100.0/NULLIF(COUNT(*),0),1) AS 납기준수율,
                       ROUND(SUM(g.rejected_qty)*100.0/NULLIF(SUM(g.received_qty),0),1) AS 불량률
                FROM goods_receipts g
                JOIN purchase_orders p ON g.po_id=p.id
                JOIN suppliers s ON p.supplier_id=s.id
                WHERE p.delivery_date IS NOT NULL AND g.created_at>='{bi_from}'
                GROUP BY s.id ORDER BY 납기준수율 DESC""", conn)
            if not df_ontime.empty:
                fig2 = px.scatter(df_ontime, x='납기준수율', y='불량률',
                                  text='공급사', size_max=20,
                                  title="납기준수율 vs 불량률 (좌상단이 최적)",
                                  color='납기준수율', color_continuous_scale='RdYlGn')
                fig2.add_vline(x=95, line_dash="dash", line_color="green")
                fig2.add_hline(y=5, line_dash="dash", line_color="red")
                fig2.update_traces(textposition='top center')
                fig2.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

        # 공급사 평가 레이더
        df_eval = pd.read_sql_query("""
            SELECT s.name AS 공급사,
                   ROUND(AVG(e.delivery_score),1) AS 납기,
                   ROUND(AVG(e.quality_score),1) AS 품질,
                   ROUND(AVG(e.price_score),1) AS 가격,
                   ROUND(AVG(e.service_score),1) AS 서비스,
                   ROUND(AVG(e.total_score),1) AS 총점
            FROM supplier_evaluations e JOIN suppliers s ON e.supplier_id=s.id
            GROUP BY e.supplier_id ORDER BY 총점 DESC LIMIT 6""", conn)

        if not df_eval.empty:
            col_r2, col_r3 = st.columns(2)
            with col_r2:
                cats = ['납기','품질','가격','서비스']
                fig3 = go.Figure()
                for _, row in df_eval.iterrows():
                    fig3.add_trace(go.Scatterpolar(
                        r=[row['납기'],row['품질'],row['가격'],row['서비스'],row['납기']],
                        theta=cats+[cats[0]], fill='toself', name=row['공급사']))
                fig3.update_layout(polar=dict(radialaxis=dict(range=[0,25])),
                                   title="공급사 역량 레이더 (TOP6)",
                                   height=340, margin=dict(l=40,r=40,t=60,b=0))
                st.plotly_chart(fig3, use_container_width=True)
            with col_r3:
                fig4 = px.bar(df_eval, x='공급사', y='총점',
                              color='총점', color_continuous_scale='RdYlGn',
                              range_color=[0,100], title="공급사별 평균 총점")
                fig4.add_hline(y=75, line_dash="dash", line_color="orange", annotation_text="합격선")
                fig4.update_layout(height=340, margin=dict(l=0,r=0,t=40,b=0), showlegend=False)
                st.plotly_chart(fig4, use_container_width=True)

        conn.close()


# ── BI-2: 구매 프로세스 분석 (대분류1) ───────────────────
with tabs["bi_po"]:
    if not HAS_PLOTLY:
        _no_plotly()
    else:
        conn = get_db()
        st.subheader("📝 구매 프로세스 분석 대시보드")

        po_amt  = conn.execute(f"SELECT COALESCE(SUM(quantity*unit_price),0) FROM purchase_orders WHERE status!='취소' AND created_at>='{bi_from}'").fetchone()[0]
        po_cnt  = conn.execute(f"SELECT COUNT(*) FROM purchase_orders WHERE status!='취소' AND created_at>='{bi_from}'").fetchone()[0]
        pr_cnt  = conn.execute(f"SELECT COUNT(*) FROM purchase_requests WHERE created_at>='{bi_from}'").fetchone()[0]
        late_po = conn.execute(f"SELECT COUNT(*) FROM purchase_orders WHERE delivery_date<date('now') AND status NOT IN ('입고완료','취소')").fetchone()[0]
        savings = conn.execute(f"""
            SELECT ROUND((1-AVG(p.unit_price/NULLIF(m.standard_price,0)))*100,1)
            FROM purchase_orders p JOIN materials m ON p.material_id=m.id
            WHERE m.standard_price>0 AND p.status!='취소' AND p.created_at>='{bi_from}'""").fetchone()[0] or 0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("총 발주금액", f"₩{po_amt:,.0f}")
        c2.metric("발주건수", f"{po_cnt}건")
        c3.metric("구매요청", f"{pr_cnt}건")
        c4.metric("납기지연 PO", f"{late_po}건", delta_color="inverse")
        c5.metric("단가절감률", f"{savings:.1f}%")
        st.divider()

        col_l, col_r = st.columns(2)
        with col_l:
            # 월별 발주 추이
            df_trend = pd.read_sql_query(f"""
                SELECT substr(created_at,1,7) AS 월,
                       ROUND(SUM(quantity*unit_price),0) AS 발주금액,
                       COUNT(*) AS 건수
                FROM purchase_orders WHERE status!='취소' AND created_at>='{bi_from}'
                GROUP BY substr(created_at,1,7) ORDER BY 월""", conn)
            if not df_trend.empty:
                fig = make_subplots(specs=[[{"secondary_y":True}]])
                fig.add_trace(go.Bar(x=df_trend['월'], y=df_trend['발주금액'],
                                     name='발주금액', marker_color='#3b82f6'), secondary_y=False)
                fig.add_trace(go.Scatter(x=df_trend['월'], y=df_trend['건수'],
                                         name='건수', mode='lines+markers',
                                         line=dict(color='#f97316',width=2)), secondary_y=True)
                fig.update_layout(title="월별 발주금액 · 건수", height=300,
                                  margin=dict(l=0,r=0,t=40,b=0),
                                  legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.plotly_chart(_empty_fig("발주 데이터 없음"), use_container_width=True)

        with col_r:
            # PO 상태 분포
            df_po_st = pd.read_sql_query("""
                SELECT status AS 상태, COUNT(*) AS 건수
                FROM purchase_orders GROUP BY status""", conn)
            if not df_po_st.empty:
                fig2 = px.pie(df_po_st, names='상태', values='건수',
                              hole=0.4, title="PO 상태 현황")
                fig2.update_layout(height=300, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig2, use_container_width=True)

        # PR→PO 전환율
        pr_approved = conn.execute(f"SELECT COUNT(*) FROM purchase_requests WHERE status='승인' AND created_at>='{bi_from}'").fetchone()[0]
        pr_to_po = conn.execute(f"SELECT COUNT(DISTINCT pr_id) FROM purchase_orders WHERE pr_id IS NOT NULL AND created_at>='{bi_from}'").fetchone()[0]
        conv_rate = round(pr_to_po / pr_approved * 100, 1) if pr_approved > 0 else 0

        col_l2, col_r2 = st.columns(2)
        with col_l2:
            st.metric("PR → PO 전환율", f"{conv_rate}%",
                      help="승인된 PR 대비 PO로 전환된 비율")
            # 품목별 발주금액 treemap
            df_item = pd.read_sql_query(f"""
                SELECT item_name AS 품목, ROUND(SUM(quantity*unit_price),0) AS 발주금액, COUNT(*) AS 건수
                FROM purchase_orders WHERE status!='취소' AND created_at>='{bi_from}'
                GROUP BY item_name ORDER BY 발주금액 DESC LIMIT 12""", conn)
            if not df_item.empty:
                fig3 = px.treemap(df_item, path=['품목'], values='발주금액',
                                  color='건수', color_continuous_scale='Blues',
                                  title="품목별 발주금액 트리맵")
                fig3.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig3, use_container_width=True)

        with col_r2:
            # 계약 만료 현황
            today_str = datetime.now().strftime("%Y-%m-%d")
            d30 = (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d")
            df_contract = pd.read_sql_query(f"""
                SELECT s.name AS 공급사, c.item_name AS 품목,
                       c.end_date AS 종료일,
                       CAST(julianday(c.end_date)-julianday('now') AS INTEGER) AS 잔여일
                FROM supplier_contracts c JOIN suppliers s ON c.supplier_id=s.id
                WHERE c.status='유효' AND c.end_date<='{d30}'
                ORDER BY c.end_date""", conn)
            if not df_contract.empty:
                st.warning(f"⚠️ 30일 내 만료 계약 {len(df_contract)}건")
                st.dataframe(df_contract, use_container_width=True, hide_index=True)
            else:
                st.success("✅ 30일 내 만료 계약 없음")

        conn.close()


# ── BI-3: 입출고 분석 (대분류2) ──────────────────────────
with tabs["bi_gr"]:
    if not HAS_PLOTLY:
        _no_plotly()
    else:
        conn = get_db()
        st.subheader("📦 입출고 분석 대시보드")

        gr_cnt   = conn.execute(f"SELECT COUNT(*) FROM goods_receipts WHERE created_at>='{bi_from}'").fetchone()[0]
        defect   = conn.execute(f"SELECT ROUND(SUM(rejected_qty)*100.0/NULLIF(SUM(received_qty),0),1) FROM goods_receipts WHERE created_at>='{bi_from}'").fetchone()[0] or 0
        rtv_cnt  = conn.execute(f"SELECT COUNT(*) FROM return_to_vendor WHERE created_at>='{bi_from}'").fetchone()[0]
        rtv_credit = conn.execute(f"SELECT COALESCE(SUM(credit_note_amount),0) FROM return_to_vendor WHERE created_at>='{bi_from}'").fetchone()[0]

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("입고건수", f"{gr_cnt}건")
        c2.metric("평균 불량률", f"{defect:.1f}%", delta_color="inverse")
        c3.metric("반품건수", f"{rtv_cnt}건", delta_color="inverse")
        c4.metric("크레딧 노트 합계", f"₩{rtv_credit:,.0f}")
        st.divider()

        col_l, col_r = st.columns(2)
        with col_l:
            # 월별 입고 추이
            df_gr = pd.read_sql_query(f"""
                SELECT substr(created_at,1,7) AS 월,
                       SUM(received_qty) AS 입고수량,
                       SUM(rejected_qty) AS 불량수량,
                       ROUND(SUM(rejected_qty)*100.0/NULLIF(SUM(received_qty),0),1) AS 불량률
                FROM goods_receipts WHERE created_at>='{bi_from}'
                GROUP BY substr(created_at,1,7) ORDER BY 월""", conn)
            if not df_gr.empty:
                fig = make_subplots(specs=[[{"secondary_y":True}]])
                fig.add_trace(go.Bar(x=df_gr['월'], y=df_gr['입고수량'],
                                     name='입고수량', marker_color='#10b981'), secondary_y=False)
                fig.add_trace(go.Scatter(x=df_gr['월'], y=df_gr['불량률'],
                                         name='불량률(%)', mode='lines+markers',
                                         line=dict(color='#ef4444',width=2)), secondary_y=True)
                fig.update_layout(title="월별 입고수량 · 불량률", height=300,
                                  margin=dict(l=0,r=0,t=40,b=0),
                                  legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            # 공급사별 불량률
            df_defect = pd.read_sql_query(f"""
                SELECT s.name AS 공급사,
                       ROUND(SUM(g.rejected_qty)*100.0/NULLIF(SUM(g.received_qty),0),1) AS 불량률,
                       SUM(g.received_qty) AS 입고수량
                FROM goods_receipts g
                JOIN purchase_orders p ON g.po_id=p.id
                JOIN suppliers s ON p.supplier_id=s.id
                WHERE g.created_at>='{bi_from}'
                GROUP BY s.id HAVING 입고수량>0
                ORDER BY 불량률 DESC LIMIT 10""", conn)
            if not df_defect.empty:
                fig2 = px.bar(df_defect, x='공급사', y='불량률',
                              color='불량률', color_continuous_scale='RdYlGn_r',
                              title="공급사별 불량률 (%)")
                fig2.add_hline(y=5, line_dash="dash", line_color="red", annotation_text="기준 5%")
                fig2.update_layout(height=300, margin=dict(l=0,r=0,t=40,b=0), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

        # 반품 분석
        df_rtv = pd.read_sql_query(f"""
            SELECT defect_type AS 불량유형, COUNT(*) AS 건수,
                   ROUND(SUM(credit_note_amount),0) AS 크레딧합계
            FROM return_to_vendor WHERE created_at>='{bi_from}'
            GROUP BY defect_type ORDER BY 건수 DESC""", conn)
        if not df_rtv.empty:
            col_l2, col_r2 = st.columns(2)
            with col_l2:
                fig3 = px.pie(df_rtv, names='불량유형', values='건수',
                              title="반품 사유별 비중", hole=0.4)
                fig3.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig3, use_container_width=True)
            with col_r2:
                st.dataframe(df_rtv, use_container_width=True, hide_index=True)

        conn.close()


# ── BI-4: 정산 분석 (대분류3) ────────────────────────────
with tabs["bi_pay"]:
    if not HAS_PLOTLY:
        _no_plotly()
    else:
        conn = get_db()
        st.subheader("💰 정산 분석 대시보드")

        iv_match  = conn.execute(f"SELECT COUNT(*) FROM invoice_verifications WHERE match_result='완전일치' AND created_at>='{bi_from}'").fetchone()[0]
        iv_total  = conn.execute(f"SELECT COUNT(*) FROM invoice_verifications WHERE created_at>='{bi_from}'").fetchone()[0]
        match_rate = round(iv_match/iv_total*100,1) if iv_total > 0 else 0
        unpaid    = conn.execute("SELECT COALESCE(SUM(payment_amount),0) FROM payment_schedule WHERE status='미지급'").fetchone()[0]
        overdue   = conn.execute(f"SELECT COUNT(*) FROM payment_schedule WHERE status='미지급' AND due_date<date('now')").fetchone()[0]
        paid_amt  = conn.execute(f"SELECT COALESCE(SUM(payment_amount),0) FROM payment_schedule WHERE status='지급완료' AND paid_at>='{bi_from}'").fetchone()[0]

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("송장검증 일치율", f"{match_rate:.1f}%")
        c2.metric("미지급 잔액", f"₩{unpaid:,.0f}", delta_color="inverse")
        c3.metric("연체 건수", f"{overdue}건", delta_color="inverse")
        c4.metric("기간 내 지급완료", f"₩{paid_amt:,.0f}")
        st.divider()

        col_l, col_r = st.columns(2)
        with col_l:
            # 월별 지급 현황
            df_pay = pd.read_sql_query("""
                SELECT substr(due_date,1,7) AS 월,
                       ROUND(SUM(CASE WHEN status='지급완료' THEN payment_amount ELSE 0 END),0) AS 지급완료,
                       ROUND(SUM(CASE WHEN status='미지급' THEN payment_amount ELSE 0 END),0) AS 미지급
                FROM payment_schedule
                GROUP BY substr(due_date,1,7) ORDER BY 월""", conn)
            if not df_pay.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df_pay['월'], y=df_pay['지급완료'],
                                     name='지급완료', marker_color='#10b981'))
                fig.add_trace(go.Bar(x=df_pay['월'], y=df_pay['미지급'],
                                     name='미지급', marker_color='#ef4444'))
                fig.update_layout(barmode='stack', title="월별 지급 현황",
                                  height=300, margin=dict(l=0,r=0,t=40,b=0),
                                  legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            # 송장검증 대사결과 분포
            df_iv = pd.read_sql_query(f"""
                SELECT match_result AS 결과, COUNT(*) AS 건수
                FROM invoice_verifications WHERE created_at>='{bi_from}'
                GROUP BY match_result""", conn)
            if not df_iv.empty:
                color_map = {'완전일치':'#10b981','허용범위 내':'#3b82f6',
                             '불일치':'#ef4444','검토중':'#9ca3af'}
                fig2 = px.pie(df_iv, names='결과', values='건수',
                              color='결과', color_discrete_map=color_map,
                              title="송장검증 대사결과 분포", hole=0.4)
                fig2.update_layout(height=300, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.plotly_chart(_empty_fig("검증 데이터 없음"), use_container_width=True)

        # 공급사별 미지급 상위
        df_sup_unpaid = pd.read_sql_query("""
            SELECT supplier_name AS 공급사,
                   COUNT(CASE WHEN status='미지급' THEN 1 END) AS 미지급건,
                   ROUND(SUM(CASE WHEN status='미지급' THEN payment_amount ELSE 0 END),0) AS 미지급금액,
                   MIN(CASE WHEN status='미지급' THEN due_date END) AS 최근만기
            FROM payment_schedule GROUP BY supplier_name
            HAVING 미지급금액>0 ORDER BY 미지급금액 DESC""", conn)
        if not df_sup_unpaid.empty:
            st.subheader("공급사별 미지급 현황")
            st.dataframe(df_sup_unpaid, use_container_width=True, hide_index=True)

        conn.close()

# ══ 재발주점(ROP) · 자동발주 ══════════════════════════════════════════
with tabs["rop"]:
    def _ac_mm(t,c,ct="TEXT"):
        try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
        except: pass
    _ac_mm("materials","reorder_point","REAL DEFAULT 0")
    _ac_mm("materials","reorder_qty","REAL DEFAULT 0")
    _ac_mm("materials","lead_time_days","INTEGER DEFAULT 7")
    _ac_mm("materials","auto_order","INTEGER DEFAULT 0")

    st.subheader("🔄 재발주점(ROP) · 자동발주 설정")
    st.caption("재고가 재발주점 이하로 떨어지면 자동으로 PR 생성")

    col_set, col_mon = st.columns([1, 2])
    with col_set:
        st.subheader("재발주점 설정")
        conn=get_db()
        mats=[r for r in conn.execute("SELECT id,material_code,material_name,min_stock,reorder_point,reorder_qty,lead_time_days,auto_order FROM materials ORDER BY material_name").fetchall()]
        conn.close()
        if not mats: st.info("자재 없음")
        else:
            mat_map={f"{r['material_code']} {r['material_name']}":r for r in mats}
            sel_m=st.selectbox("자재 선택",list(mat_map.keys()))
            m=mat_map[sel_m]
            with st.form("rop_f"):
                a,b=st.columns(2); rop=a.number_input("재발주점(ROP)",min_value=0.0,value=float(m['reorder_point'] or 0),format="%.1f"); rqty=b.number_input("발주수량",min_value=0.0,value=float(m['reorder_qty'] or 0),format="%.1f")
                lt=st.number_input("리드타임(일)",min_value=1,value=int(m['lead_time_days'] or 7))
                auto=st.checkbox("자동발주 활성화",value=bool(m['auto_order']))
                if st.form_submit_button("✅ 저장",use_container_width=True):
                    conn=get_db(); conn.execute("UPDATE materials SET reorder_point=?,reorder_qty=?,lead_time_days=?,auto_order=? WHERE id=?",(rop,rqty,lt,1 if auto else 0,m['id']))
                    conn.commit(); conn.close(); st.success("저장!"); st.rerun()

        st.divider()
        if st.button("🤖 자동발주 실행 (재고 점검)",use_container_width=True,type="primary"):
            conn=get_db()
            mats_auto=[r for r in conn.execute("""
                SELECT m.id,m.material_name,m.reorder_point,m.reorder_qty,m.lead_time_days,
                       COALESCE(i.stock_qty,0) AS stock
                FROM materials m
                LEFT JOIN inventory i ON m.material_name=i.item_name
                WHERE m.auto_order=1 AND m.reorder_point>0""").fetchall()]
            created=0
            for r in mats_auto:
                if r['stock'] <= r['reorder_point']:
                    try:
                        prn=gen_number("PR")
                        conn.execute("""INSERT INTO purchase_requests(pr_number,material_name,quantity,required_date,status,note)
                            VALUES(?,?,?,date('now',?),?,?)""",
                            (prn,r['material_name'],r['reorder_qty'],f"+{r['lead_time_days']} days","자동생성",f"자동발주: 재고{r['stock']} ≤ ROP{r['reorder_point']}"))
                        created+=1
                    except: pass
            conn.commit(); conn.close()
            if created: st.success(f"✅ PR {created}건 자동 생성!")
            else: st.info("자동발주 대상 없음")

    with col_mon:
        st.subheader("📊 재발주점 모니터링")
        conn=get_db(); df_rop=pd.read_sql_query("""
            SELECT m.material_code AS 자재코드, m.material_name AS 자재명,
                   COALESCE(i.stock_qty,0) AS 현재고,
                   m.reorder_point AS ROP, m.min_stock AS 안전재고,
                   m.reorder_qty AS 발주수량, m.lead_time_days AS 리드타임,
                   CASE m.auto_order WHEN 1 THEN '✅자동' ELSE '수동' END AS 자동발주,
                   CASE WHEN COALESCE(i.stock_qty,0) <= m.reorder_point AND m.reorder_point>0 THEN '🔴 발주필요'
                        WHEN COALESCE(i.stock_qty,0) <= m.min_stock THEN '🟠 안전재고미달'
                        ELSE '🟢 정상' END AS 상태
            FROM materials m
            LEFT JOIN inventory i ON m.material_name=i.item_name
            WHERE m.reorder_point>0
            ORDER BY COALESCE(i.stock_qty,0)-m.reorder_point""", conn); conn.close()
        if df_rop.empty: st.info("ROP 설정된 자재 없음")
        else:
            alert=df_rop[df_rop['상태'].str.contains('발주')]
            if not alert.empty: st.error(f"⚠️ 즉시 발주 필요: {len(alert)}종")
            st.dataframe(df_rop, use_container_width=True, hide_index=True)
            try:
                import plotly.express as px
                fig=px.bar(df_rop,x='자재명',y=['현재고','ROP','안전재고'],barmode='group',
                           title="자재별 재고 vs ROP",color_discrete_map={'현재고':'#3b82f6','ROP':'#f97316','안전재고':'#ef4444'})
                fig.update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig,use_container_width=True)
            except: pass


# ══ VMI (Vendor Managed Inventory) ══════════════════════════════════════════
with tabs["vmi"]:
    try:
        conn=get_db()
        conn.execute('''CREATE TABLE IF NOT EXISTS vmi_agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vmi_number TEXT UNIQUE,
            supplier_id INTEGER, supplier_name TEXT,
            material_name TEXT,
            min_qty REAL DEFAULT 0, max_qty REAL DEFAULT 0,
            replenish_trigger REAL DEFAULT 0,
            review_cycle TEXT DEFAULT '주간',
            status TEXT DEFAULT '활성',
            note TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS vmi_replenishments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vmi_id INTEGER, supplier_name TEXT,
            material_name TEXT, current_stock REAL,
            replenish_qty REAL, status TEXT DEFAULT '요청',
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
        conn.commit(); conn.close()
    except: pass

    st.subheader("🤝 VMI — 공급사 관리 재고")
    st.caption("공급사가 직접 재고를 모니터링하고 보충하는 협력 재고 관리 방식")

    col_form, col_mon = st.columns([1, 2])
    with col_form:
        st.subheader("VMI 협약 등록")
        conn=get_db()
        sups_v=[r for r in conn.execute("SELECT id,name AS supplier_name FROM suppliers WHERE status='활성'").fetchall()]
        conn.close()
        with st.form("vmi_f", clear_on_submit=True):
            sup_v=st.selectbox("공급사",([r['supplier_name'] for r in sups_v] if sups_v else ["직접입력"]))
            mat_v=st.text_input("관리 품목 *")
            a,b=st.columns(2); mn_v=a.number_input("최소재고",min_value=0.0,format="%.1f"); mx_v=b.number_input("최대재고",min_value=0.0,format="%.1f")
            trig_v=st.number_input("보충 트리거 재고",min_value=0.0,value=mn_v,format="%.1f",help="이 재고 이하가 되면 자동 보충요청")
            cyc_v=st.selectbox("검토주기",["일간","주간","격주","월간"])
            st_v=st.selectbox("상태",["활성","일시중지","종료"]); note_v=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not mat_v: st.error("품목 필수")
                else:
                    try:
                        conn=get_db()
                        sup_id=next((r['id'] for r in sups_v if r['supplier_name']==sup_v),None)
                        conn.execute("INSERT INTO vmi_agreements(vmi_number,supplier_id,supplier_name,material_name,min_qty,max_qty,replenish_trigger,review_cycle,status,note) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (gen_number("VMI"),sup_id,sup_v,mat_v,mn_v,mx_v,trig_v,cyc_v,st_v,note_v))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")

        st.divider()
        if st.button("🔄 VMI 재고 점검 & 보충요청",use_container_width=True,type="primary"):
            conn=get_db()
            vmis=[r for r in conn.execute("SELECT v.*,COALESCE(i.stock_qty,0) AS cur_stock FROM vmi_agreements v LEFT JOIN inventory i ON v.material_name=i.item_name WHERE v.status='활성'").fetchall()]
            cnt=0
            for v in vmis:
                if v['cur_stock']<=v['replenish_trigger']:
                    need=v['max_qty']-v['cur_stock']
                    conn.execute("INSERT INTO vmi_replenishments(vmi_id,supplier_name,material_name,current_stock,replenish_qty,status) VALUES(?,?,?,?,?,?)",
                        (v['id'],v['supplier_name'],v['material_name'],v['cur_stock'],need,"요청"))
                    cnt+=1
            conn.commit(); conn.close()
            if cnt: st.success(f"✅ {cnt}건 보충요청 생성")
            else: st.info("보충 필요 없음")

    with col_mon:
        conn=get_db(); df_vmi=pd.read_sql_query("""
            SELECT v.vmi_number AS VMI번호, v.supplier_name AS 공급사,
                   v.material_name AS 품목,
                   COALESCE(i.stock_qty,0) AS 현재고,
                   v.min_qty AS 최소재고, v.max_qty AS 최대재고,
                   v.replenish_trigger AS 보충트리거,
                   v.review_cycle AS 검토주기, v.status AS 상태,
                   CASE WHEN COALESCE(i.stock_qty,0)<=v.replenish_trigger THEN '🔴 보충필요'
                        WHEN COALESCE(i.stock_qty,0)<=v.min_qty THEN '🟠 최소재고'
                        WHEN COALESCE(i.stock_qty,0)>=v.max_qty THEN '🔵 최대초과'
                        ELSE '🟢 정상' END AS 재고상태
            FROM vmi_agreements v
            LEFT JOIN inventory i ON v.material_name=i.item_name
            WHERE v.status='활성' ORDER BY 재고상태""", conn)
        df_rep=pd.read_sql_query("""
            SELECT supplier_name AS 공급사, material_name AS 품목,
                   current_stock AS 현재고, replenish_qty AS 보충수량,
                   status AS 상태, created_at AS 요청일시
            FROM vmi_replenishments ORDER BY id DESC LIMIT 20""", conn)
        conn.close()

        if not df_vmi.empty:
            needs=df_vmi[df_vmi['재고상태'].str.contains('보충')]
            if not needs.empty: st.error(f"⚠️ VMI 보충 필요: {len(needs)}건")
            st.dataframe(df_vmi,use_container_width=True,hide_index=True)

            # ── 행 수정/삭제 버튼 (vmi_replenishments) ──────────────────────────
            if not df_vmi.empty if hasattr(df_vmi, 'empty') else df_vmi is not None:
                _row_opts_vmi_replenishments = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM vmi_replenishments ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('supplier_name','')}"
                        _row_opts_vmi_replenishments[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_vmi_replenishments:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_vmi_replenishments = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_vmi_replenishments.keys()),
                        key="_rbsel_vmi_replenishments", label_visibility="collapsed"
                    )
                    _rb_id_vmi_replenishments = _row_opts_vmi_replenishments[_rb_sel_vmi_replenishments]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_vmi_replenishments"):
                        st.session_state[f"_edit_vmi_replenishments"] = _rb_id_vmi_replenishments
                        st.session_state[f"_del_vmi_replenishments"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_vmi_replenishments"):
                        st.session_state[f"_del_vmi_replenishments"]  = _rb_id_vmi_replenishments
                        st.session_state[f"_edit_vmi_replenishments"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_vmi_replenishments"):
                    _del_id_vmi_replenishments = st.session_state[f"_del_vmi_replenishments"]
                    st.warning(f"⚠️ ID **{_del_id_vmi_replenishments}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_vmi_replenishments"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM vmi_replenishments WHERE id = ?", (_del_id_vmi_replenishments,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_vmi_replenishments"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_vmi_replenishments"):
                        st.session_state[f"_del_vmi_replenishments"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_vmi_replenishments"):
                    _edit_id_vmi_replenishments = st.session_state[f"_edit_vmi_replenishments"]
                    try:
                        _cx_e = get_db()
                        _edit_row_vmi_replenishments = dict(_cx_e.execute(
                            "SELECT * FROM vmi_replenishments WHERE id=?", (_edit_id_vmi_replenishments,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_vmi_replenishments = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_vmi_replenishments}", expanded=True):
                        if not _edit_row_vmi_replenishments:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_vmi_replenishments = [c for c in _edit_row_vmi_replenishments if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_vmi_replenishments)))
                            _ecols = st.columns(_ncols)
                            _new_vals_vmi_replenishments = {}
                            for _i, _fc in enumerate(_edit_fields_vmi_replenishments):
                                _cv = _edit_row_vmi_replenishments[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_vmi_replenishments[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_vmi_replenishments}_{_fc}_vmi_replenishments")
                                else:
                                    _new_vals_vmi_replenishments[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_vmi_replenishments}_{_fc}_vmi_replenishments")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_vmi_replenishments"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_vmi_replenishments])
                                _set_params = list(_new_vals_vmi_replenishments.values()) + [_edit_id_vmi_replenishments]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE vmi_replenishments SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_vmi_replenishments"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_vmi_replenishments"):
                                st.session_state[f"_edit_vmi_replenishments"] = None; st.rerun()


            # ── 행 수정/삭제 버튼 (vmi_agreements) ──────────────────────────
            if not df_vmi.empty if hasattr(df_vmi, 'empty') else df_vmi is not None:
                _row_opts_vmi_agreements = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, * FROM vmi_agreements ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('supplier_name','')}"
                        _row_opts_vmi_agreements[_k] = _r['id']
                except Exception:
                    pass
            
                if _row_opts_vmi_agreements:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_vmi_agreements = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_vmi_agreements.keys()),
                        key="_rbsel_vmi_agreements", label_visibility="collapsed"
                    )
                    _rb_id_vmi_agreements = _row_opts_vmi_agreements[_rb_sel_vmi_agreements]
            
                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_vmi_agreements"):
                        st.session_state[f"_edit_vmi_agreements"] = _rb_id_vmi_agreements
                        st.session_state[f"_del_vmi_agreements"]  = None
            
                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_vmi_agreements"):
                        st.session_state[f"_del_vmi_agreements"]  = _rb_id_vmi_agreements
                        st.session_state[f"_edit_vmi_agreements"] = None
            
                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_vmi_agreements"):
                    _del_id_vmi_agreements = st.session_state[f"_del_vmi_agreements"]
                    st.warning(f"⚠️ ID **{_del_id_vmi_agreements}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_vmi_agreements"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM vmi_agreements WHERE id = ?", (_del_id_vmi_agreements,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_vmi_agreements"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_vmi_agreements"):
                        st.session_state[f"_del_vmi_agreements"] = None; st.rerun()
            
                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_vmi_agreements"):
                    _edit_id_vmi_agreements = st.session_state[f"_edit_vmi_agreements"]
                    try:
                        _cx_e = get_db()
                        _edit_row_vmi_agreements = dict(_cx_e.execute(
                            "SELECT * FROM vmi_agreements WHERE id=?", (_edit_id_vmi_agreements,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_vmi_agreements = {}
                    with st.expander(f"✏️ 정보 수정 — ID {_edit_id_vmi_agreements}", expanded=True):
                        if not _edit_row_vmi_agreements:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at','ordered_at'}
                            _edit_fields_vmi_agreements = [c for c in _edit_row_vmi_agreements if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_vmi_agreements)))
                            _ecols = st.columns(_ncols)
                            _new_vals_vmi_agreements = {}
                            for _i, _fc in enumerate(_edit_fields_vmi_agreements):
                                _cv = _edit_row_vmi_agreements[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_vmi_agreements[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_vmi_agreements}_{_fc}_vmi_agreements")
                                else:
                                    _new_vals_vmi_agreements[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_vmi_agreements}_{_fc}_vmi_agreements")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_vmi_agreements"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_vmi_agreements])
                                _set_params = list(_new_vals_vmi_agreements.values()) + [_edit_id_vmi_agreements]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE vmi_agreements SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_vmi_agreements"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_vmi_agreements"):
                                st.session_state[f"_edit_vmi_agreements"] = None; st.rerun()

        st.divider()
        st.subheader("보충요청 이력")
        if not df_rep.empty: st.dataframe(df_rep,use_container_width=True,hide_index=True)
        else: st.info("보충요청 없음")
