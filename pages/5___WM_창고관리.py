import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number
from utils.design import inject_css, apply_plotly_theme
from datetime import datetime, timedelta, date

def _ac(t,c,ct="TEXT"):
    try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
    except: pass

_ac("inventory","lot_number"); _ac("inventory","expiry_date")
_ac("inventory","serial_number"); _ac("stock_movements","lot_number")
_ac("stock_movements","reference_number"); _ac("stock_movements","movement_number")
_ac("goods_receipts","fifo_layer","INTEGER DEFAULT 1")
_ac("materials","max_stock","REAL DEFAULT 0"); _ac("materials","new_avg","REAL DEFAULT 0")

st.title("📦 WM/EWM – Warehouse Management (창고관리)")
inject_css()
apply_plotly_theme()

main_tabs = st.tabs(["🏗️ 기준정보", "📦 입출고", "📊 재고 관리", "🔍 실사·폐기", "📈 분석·예측"])
tabs = {}
with main_tabs[0]:
    s = st.tabs(["🏗️ 창고/Bin 등록", "🏷️ LOT·시리얼 관리", "📍 Putaway 위치최적화"])
    tabs.update({"wh": s[0], "lot": s[1], "putaway": s[2]})
with main_tabs[1]:
    s = st.tabs(["📥 입고(ASN/검수)", "📤 출고지시(FIFO)", "🌊 피킹 웨이브", "🔄 재고 이동"])
    tabs.update({"gr": s[0], "issue": s[1], "wave": s[2], "move": s[3]})
with main_tabs[2]:
    s = st.tabs(["📊 재고 현황", "🔔 안전재고 알림"])
    tabs.update({"stock": s[0], "safety": s[1]})
with main_tabs[3]:
    s = st.tabs(["🔍 재고 실사", "🗑️ 폐기·반송"])
    tabs.update({"count": s[0], "dispose": s[1]})
with main_tabs[4]:
    s = st.tabs(["📊 재고 분석", "🔮 수요·폐기 예측"])
    tabs.update({"bi": s[0], "pred": s[1]})

with st.sidebar:
    st.divider(); st.markdown("### 📊 분석 기간")
    bp = st.selectbox("기간",["최근 1개월","최근 3개월","최근 6개월","최근 1년","전체"],key="wm_bp")
    bi_from = (datetime.now()-timedelta(days={"최근 1개월":30,"최근 3개월":90,"최근 6개월":180,"최근 1년":365,"전체":9999}[bp])).strftime("%Y-%m-%d")

try:
    import plotly.express as px; import plotly.graph_objects as go
    import numpy as np; from plotly.subplots import make_subplots; HAS_PL=True
except: HAS_PL=False

# ── 창고 & 빈 등록 ──────────────────────────────────────────
with tabs["wh"]:
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("창고 등록")
        with st.form("wh_form", clear_on_submit=True):
            wh_code = st.text_input("창고코드 *")
            wh_name = st.text_input("창고명 *")
            location= st.text_input("위치")
            wh_type = st.selectbox("창고유형", ["일반창고","냉장창고","냉동창고","위험물창고","야외창고"])
            capacity= st.number_input("용량(㎡)", min_value=0.0, format="%.1f")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not wh_code or not wh_name:
                    st.error("창고코드, 창고명 필수")
                else:
                    conn = get_db()
                    conn.execute("""INSERT INTO warehouses
                        (warehouse_code,warehouse_name,location,warehouse_type,capacity)
                        VALUES(?,?,?,?,?)
                        ON DUPLICATE KEY UPDATE
                        warehouse_name=VALUES(warehouse_name),
                        location=VALUES(location),
                        warehouse_type=VALUES(warehouse_type),
                        capacity=VALUES(capacity)""",
                        (wh_code, wh_name, location, wh_type, capacity))
                    conn.commit(); conn.close()
                    st.success("창고 등록 완료!"); st.rerun()
        conn = get_db()
        df_wh = pd.read_sql_query("""
            SELECT warehouse_code AS 코드, warehouse_name AS 창고명,
                   location AS 위치, warehouse_type AS 유형, capacity AS 용량
            FROM warehouses ORDER BY id""", conn)
        conn.close()
        if not df_wh.empty:

            st.dataframe(df_wh, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (창고) ──────────────────────────
            if not df_wh.empty if hasattr(df_wh, 'empty') else df_wh is not None:
                _row_opts_warehouses = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 창고명 FROM warehouses ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('창고명','')}"
                        _row_opts_warehouses[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_warehouses:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_warehouses = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_warehouses.keys()),
                        key="_rbsel_warehouses", label_visibility="collapsed"
                    )
                    _rb_id_warehouses = _row_opts_warehouses[_rb_sel_warehouses]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_warehouses"):
                        st.session_state[f"_edit_warehouses"] = _rb_id_warehouses
                        st.session_state[f"_del_warehouses"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_warehouses"):
                        st.session_state[f"_del_warehouses"]  = _rb_id_warehouses
                        st.session_state[f"_edit_warehouses"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_warehouses"):
                    _del_id_warehouses = st.session_state[f"_del_warehouses"]
                    st.warning(f"⚠️ ID **{_del_id_warehouses}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_warehouses"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM warehouses WHERE id = ?", (_del_id_warehouses,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_warehouses"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_warehouses"):
                        st.session_state[f"_del_warehouses"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_warehouses"):
                    _edit_id_warehouses = st.session_state[f"_edit_warehouses"]
                    try:
                        _cx_e = get_db()
                        _edit_row_warehouses = dict(_cx_e.execute(
                            "SELECT * FROM warehouses WHERE id=?", (_edit_id_warehouses,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_warehouses = {}
                    with st.expander(f"✏️ 창고 수정 — ID {_edit_id_warehouses}", expanded=True):
                        if not _edit_row_warehouses:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_warehouses = [c for c in _edit_row_warehouses if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_warehouses)))
                            _ecols = st.columns(_ncols)
                            _new_vals_warehouses = {}
                            for _i, _fc in enumerate(_edit_fields_warehouses):
                                _cv = _edit_row_warehouses[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_warehouses[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_fc}_warehouses")
                                else:
                                    _new_vals_warehouses[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_fc}_warehouses")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_warehouses"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_warehouses])
                                _set_params = list(_new_vals_warehouses.values()) + [_edit_id_warehouses]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE warehouses SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_warehouses"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_warehouses"):
                                st.session_state[f"_edit_warehouses"] = None; st.rerun()


        else:

            st.info("창고 없음")

    with col_r:
        st.subheader("Bin(저장위치) 등록")
        conn = get_db()
        whs = conn.execute("SELECT id, warehouse_code, warehouse_name FROM warehouses").fetchall()
        conn.close()
        wh_opts = {f"{w['warehouse_code']} - {w['warehouse_name']}": w['id'] for w in whs}

        with st.form("bin_form", clear_on_submit=True):
            wh_sel  = st.selectbox("창고", list(wh_opts.keys()) if wh_opts else ["창고 없음"])
            bin_code= st.text_input("Bin 코드 *")
            zone    = st.text_input("구역(Zone)")
            bin_type= st.selectbox("Bin 유형", ["일반","냉장","냉동","위험물","대형"])
            max_wt  = st.number_input("최대하중(kg)", min_value=0.0, format="%.1f")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not bin_code:
                    st.error("Bin 코드 필수")
                else:
                    conn = get_db()
                    conn.execute("""INSERT INTO storage_bins
                        (bin_code,warehouse_id,zone,bin_type,max_weight)
                        VALUES(?,?,?,?,?)
                        ON DUPLICATE KEY UPDATE warehouse_id=VALUES(warehouse_id)""",
                        (bin_code, wh_opts.get(wh_sel), zone, bin_type, max_wt))
                    conn.commit(); conn.close()
                    st.success("Bin 등록 완료!"); st.rerun()

        conn = get_db()
        df_bin = pd.read_sql_query("""
            SELECT b.bin_code AS Bin코드, w.warehouse_name AS 창고,
                   b.zone AS 구역, b.bin_type AS 유형, b.max_weight AS 최대하중,
                   CASE b.is_occupied WHEN 1 THEN '사용중' ELSE '빈자리' END AS 상태
            FROM storage_bins b LEFT JOIN warehouses w ON b.warehouse_id=w.id
            ORDER BY b.bin_code""", conn)
        conn.close()
        if not df_bin.empty:

            st.dataframe(df_bin, use_container_width=True, hide_index=True)

        else:

            st.info("Bin 없음")

# ── 입고 (ASN + 검수) ──────────────────────────────────────────
with tabs["gr"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("ASN 입고예정 등록")
        conn = get_db()
        pos = conn.execute("SELECT id, po_number, item_name FROM purchase_orders").fetchall()
        conn.close()
        po_opts = {f"{p['po_number']} - {p['item_name']}": p['id'] for p in pos}

        with st.form("asn_form", clear_on_submit=True):
            po_sel    = st.selectbox("발주서", list(po_opts.keys()) if po_opts else ["없음"])
            item_name = st.text_input("품목명 *")
            col_a, col_b = st.columns(2)
            exp_qty   = col_a.number_input("예정수량", min_value=1, value=1)
            exp_date  = col_b.date_input("입고예정일")
            warehouse = st.text_input("입고창고")
            if st.form_submit_button("✅ ASN 등록", use_container_width=True):
                if not item_name:
                    st.error("품목명 필수")
                else:
                    asn_num = gen_number("ASN")
                    conn = get_db()
                    conn.execute("""INSERT INTO asn
                        (asn_number,po_id,item_name,expected_qty,expected_date,warehouse)
                        VALUES(?,?,?,?,?,?)""",
                        (asn_num, po_opts.get(po_sel), item_name, exp_qty, str(exp_date), warehouse))
                    conn.commit(); conn.close()
                    st.success(f"ASN {asn_num} 등록!"); st.rerun()

    with col_list:
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT asn_number AS ASN번호, item_name AS 품목,
                   expected_qty AS 예정수량, expected_date AS 입고예정일,
                   warehouse AS 창고, status AS 상태
            FROM asn ORDER BY id DESC""", conn)
        conn.close()
        if not df.empty:

            st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (ASN입고) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_asn = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM asn ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_asn[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_asn:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_asn = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_asn.keys()),
                        key="_rbsel_asn", label_visibility="collapsed"
                    )
                    _rb_id_asn = _row_opts_asn[_rb_sel_asn]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_asn"):
                        st.session_state[f"_edit_asn"] = _rb_id_asn
                        st.session_state[f"_del_asn"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_asn"):
                        st.session_state[f"_del_asn"]  = _rb_id_asn
                        st.session_state[f"_edit_asn"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_asn"):
                    _del_id_asn = st.session_state[f"_del_asn"]
                    st.warning(f"⚠️ ID **{_del_id_asn}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_asn"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM asn WHERE id = ?", (_del_id_asn,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_asn"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_asn"):
                        st.session_state[f"_del_asn"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_asn"):
                    _edit_id_asn = st.session_state[f"_edit_asn"]
                    try:
                        _cx_e = get_db()
                        _edit_row_asn = dict(_cx_e.execute(
                            "SELECT * FROM asn WHERE id=?", (_edit_id_asn,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_asn = {}
                    with st.expander(f"✏️ ASN입고 수정 — ID {_edit_id_asn}", expanded=True):
                        if not _edit_row_asn:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_asn = [c for c in _edit_row_asn if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_asn)))
                            _ecols = st.columns(_ncols)
                            _new_vals_asn = {}
                            for _i, _fc in enumerate(_edit_fields_asn):
                                _cv = _edit_row_asn[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_asn[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_fc}_asn")
                                else:
                                    _new_vals_asn[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_fc}_asn")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_asn"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_asn])
                                _set_params = list(_new_vals_asn.values()) + [_edit_id_asn]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE asn SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_asn"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_asn"):
                                st.session_state[f"_edit_asn"] = None; st.rerun()


        else:

            st.info("ASN 없음")

    st.divider()
    st.subheader("🔎 입고 검수")
    col_f2, col_l2 = st.columns([1, 2])
    with col_f2:
        conn = get_db()
        asns = conn.execute("SELECT id, asn_number, item_name FROM asn").fetchall()
        conn.close()
        asn_opts = {f"{a['asn_number']} - {a['item_name']}": a['id'] for a in asns}

        with st.form("inspect_form", clear_on_submit=True):
            asn_sel   = st.selectbox("ASN 선택", list(asn_opts.keys()) if asn_opts else ["없음"])
            item_name = st.text_input("품목명 *")
            col_a, col_b, col_c = st.columns(3)
            exp_qty   = col_a.number_input("예정수량", min_value=0, value=0)
            recv_qty  = col_b.number_input("수령수량", min_value=0, value=0)
            defect    = col_c.number_input("불량수량", min_value=0, value=0)
            inspector = st.text_input("검수자")
            result    = st.selectbox("결과", ["정상","부분불량","전량불량","수량부족"])
            note      = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 검수 등록", use_container_width=True):
                if not item_name:
                    st.error("품목명 필수")
                else:
                    conn = get_db()
                    conn.execute("""INSERT INTO inbound_inspection
                        (asn_id,item_name,expected_qty,received_qty,defect_qty,inspector,result,note)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (asn_opts.get(asn_sel), item_name, exp_qty, recv_qty, defect, inspector, result, note))
                    # ── QM 수입검사 자동 트리거 ──────────────────
                    try:
                        from utils.db import gen_number as _gn
                        conn.execute("""INSERT INTO quality_inspections
                            (inspection_number,inspection_type,item_name,lot_number,
                             lot_size,sample_qty,pass_qty,fail_qty,inspector,result,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (_gn("QI"),"수입검사",item_name,"",exp_qty,recv_qty,
                             recv_qty-defect,defect,inspector,
                             "합격" if result=="정상" else ("조건부합격" if result=="부분불량" else "불합격"),
                             f"WM입고검수 자동연동 / {note}"))
                    except: pass
                    conn.commit(); conn.close()
                    st.success("검수 등록 완료! (QM 수입검사 자동 생성)"); st.rerun()
    with col_l2:
        conn = get_db()
        df2 = pd.read_sql_query("""
            SELECT item_name AS 품목, expected_qty AS 예정,
                   received_qty AS 수령, defect_qty AS 불량,
                   inspector AS 검수자, result AS 결과, inspected_at AS 일시
            FROM inbound_inspection ORDER BY id DESC""", conn)
        conn.close()
        if not df2.empty:

            st.dataframe(df2, use_container_width=True, hide_index=True)

        else:

            st.info("검수 데이터 없음")

# ── 재고 현황 ──────────────────────────────────────────
with tabs["stock"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("재고 등록/수정")
        conn = get_db()
        whs3 = conn.execute("SELECT id, warehouse_code, warehouse_name FROM warehouses").fetchall()
        conn.close()
        wh3_opts = {f"{w['warehouse_code']} - {w['warehouse_name']}": (w['id'], w['warehouse_name']) for w in whs3}

        with st.form("inv_form", clear_on_submit=True):
            item_code = st.text_input("품목코드 *")
            item_name = st.text_input("품목명 *")
            wh_sel3   = st.selectbox("창고", list(wh3_opts.keys()) if wh3_opts else ["없음"])
            bin_input = st.text_input("Bin 위치")
            col_a, col_b = st.columns(2)
            category  = col_a.text_input("카테고리")
            stock_qty = col_b.number_input("실재고", min_value=0, value=0)
            col_c, col_d = st.columns(2)
            sys_qty   = col_c.number_input("시스템재고", min_value=0, value=0)
            unit_price= col_d.number_input("단가", min_value=0.0, format="%.2f")
            min_stock = st.number_input("최소재고 기준", min_value=0, value=0)
            if st.form_submit_button("✅ 저장", use_container_width=True):
                if not item_code or not item_name:
                    st.error("품목코드, 품목명 필수")
                else:
                    wh_id, wh_name = wh3_opts.get(wh_sel3, (None, ""))
                    conn = get_db()
                    conn.execute("""INSERT INTO inventory
                        (item_code,item_name,category,warehouse_id,warehouse,bin_code,
                         stock_qty,system_qty,unit_price,min_stock)
                        VALUES(?,?,?,?,?,?,?,?,?,?)
                        ON DUPLICATE KEY UPDATE
                        item_name=VALUES(item_name), category=VALUES(category),
                        warehouse_id=VALUES(warehouse_id), warehouse=VALUES(warehouse),
                        bin_code=VALUES(bin_code), stock_qty=VALUES(stock_qty),
                        system_qty=VALUES(system_qty), unit_price=VALUES(unit_price),
                        min_stock=VALUES(min_stock),
                        updated_at=NOW()""",
                        (item_code, item_name, category, wh_id, wh_name, bin_input,
                         stock_qty, sys_qty, unit_price, min_stock))
                    conn.commit(); conn.close()
                    st.success("저장 완료!"); st.rerun()

    with col_list:
        st.subheader("재고 현황표")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT item_code AS 품목코드, item_name AS 품목명,
                   warehouse AS 창고, bin_code AS Bin,
                   stock_qty AS 실재고, system_qty AS 시스템재고,
                   (stock_qty - system_qty) AS 차이,
                   unit_price AS 단가,
                   ROUND(stock_qty * unit_price, 0) AS 재고금액,
                   min_stock AS 최소재고, updated_at AS 갱신일
            FROM inventory ORDER BY item_name""", conn)
        conn.close()
        if df.empty:
            st.info("재고 없음")
        else:
            search = st.text_input("🔍 품목 검색")
            if search:
                df = df[df['품목명'].str.contains(search, na=False)]
            def hl_low(row):
                if row['최소재고'] > 0 and row['실재고'] <= row['최소재고']:
                    return ['background-color:#fee2e2'] * len(row)
                return [''] * len(row)
            st.dataframe(df.style.apply(hl_low, axis=1), use_container_width=True, hide_index=True)
            st.metric("총 재고금액", f"₩{df['재고금액'].sum():,.0f}")

# ── 재고 이동 ──────────────────────────────────────────
with tabs["move"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("재고 이동 등록")
        with st.form("move_form", clear_on_submit=True):
            mv_type   = st.selectbox("이동유형", ["창고간이동","Bin이동","입고","출고","반품입고","폐기출고"])
            item_name = st.text_input("품목명 *")
            qty       = st.number_input("수량", min_value=1, value=1)
            from_loc  = st.text_input("출발위치")
            to_loc    = st.text_input("도착위치")
            reference = st.text_input("참조번호(PO/SO 등)")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_name:
                    st.error("품목명 필수")
                else:
                    mnum = gen_number("MV")
                    conn = get_db()
                    conn.execute("""INSERT INTO stock_movements
                        (movement_number,movement_type,item_name,quantity,from_location,to_location,reference)
                        VALUES(?,?,?,?,?,?,?)""",
                        (mnum, mv_type, item_name, qty, from_loc, to_loc, reference))
                    conn.commit(); conn.close()
                    st.success(f"이동 {mnum} 등록!"); st.rerun()
    with col_list:
        st.subheader("재고 이동 이력")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT movement_number AS 이동번호, movement_type AS 유형,
                   item_name AS 품목, quantity AS 수량,
                   from_location AS 출발, to_location AS 도착,
                   reference AS 참조, created_at AS 일시
            FROM stock_movements ORDER BY id DESC LIMIT 50""", conn)
        conn.close()
        if not df.empty:

            st.dataframe(df, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (재고이동) ──────────────────────────
            if not df.empty if hasattr(df, 'empty') else df is not None:
                _row_opts_stock_movements = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM stock_movements ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_stock_movements[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_stock_movements:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_stock_movements = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_stock_movements.keys()),
                        key="_rbsel_stock_movements", label_visibility="collapsed"
                    )
                    _rb_id_stock_movements = _row_opts_stock_movements[_rb_sel_stock_movements]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_stock_movements"):
                        st.session_state[f"_edit_stock_movements"] = _rb_id_stock_movements
                        st.session_state[f"_del_stock_movements"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_stock_movements"):
                        st.session_state[f"_del_stock_movements"]  = _rb_id_stock_movements
                        st.session_state[f"_edit_stock_movements"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_stock_movements"):
                    _del_id_stock_movements = st.session_state[f"_del_stock_movements"]
                    st.warning(f"⚠️ ID **{_del_id_stock_movements}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_stock_movements"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM stock_movements WHERE id = ?", (_del_id_stock_movements,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_stock_movements"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_stock_movements"):
                        st.session_state[f"_del_stock_movements"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_stock_movements"):
                    _edit_id_stock_movements = st.session_state[f"_edit_stock_movements"]
                    try:
                        _cx_e = get_db()
                        _edit_row_stock_movements = dict(_cx_e.execute(
                            "SELECT * FROM stock_movements WHERE id=?", (_edit_id_stock_movements,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_stock_movements = {}
                    with st.expander(f"✏️ 재고이동 수정 — ID {_edit_id_stock_movements}", expanded=True):
                        if not _edit_row_stock_movements:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_stock_movements = [c for c in _edit_row_stock_movements if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_stock_movements)))
                            _ecols = st.columns(_ncols)
                            _new_vals_stock_movements = {}
                            for _i, _fc in enumerate(_edit_fields_stock_movements):
                                _cv = _edit_row_stock_movements[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_stock_movements[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_fc}_stock_movements")
                                else:
                                    _new_vals_stock_movements[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_fc}_stock_movements")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_stock_movements"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_stock_movements])
                                _set_params = list(_new_vals_stock_movements.values()) + [_edit_id_stock_movements]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE stock_movements SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_stock_movements"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_stock_movements"):
                                st.session_state[f"_edit_stock_movements"] = None; st.rerun()


        else:

            st.info("이동 이력 없음")

# ── 재고 실사 ──────────────────────────────────────────
with tabs["count"]:
    st.subheader("🔍 재고 실사 보고서")
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT item_code AS 품목코드, item_name AS 품목명,
               warehouse AS 창고, bin_code AS Bin,
               stock_qty AS 실재고, system_qty AS 시스템재고,
               (stock_qty - system_qty) AS 차이수량,
               ROUND((stock_qty - system_qty) * unit_price, 0) AS 차이금액
        FROM inventory
        WHERE stock_qty != system_qty
        ORDER BY ABS(stock_qty - system_qty) DESC""", conn)
    conn.close()
    if df.empty:
        st.success("✅ 실재고와 시스템재고가 일치합니다!")
    else:
        st.warning(f"⚠️ 불일치 품목: {len(df)}건")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("총 재고 차이금액", f"₩{df['차이금액'].sum():,.0f}")

    st.divider()

with tabs["dispose"]:
    st.subheader("🗑️ 폐기/반송 처리")
    col_form2, col_list2 = st.columns([1, 2])
    with col_form2:
        with st.form("disposal_form", clear_on_submit=True):
            item_name = st.text_input("품목명 *")
            qty2      = st.number_input("수량", min_value=1, value=1)
            d_type    = st.selectbox("처리유형", ["폐기","반송","소각","기부"])
            reason    = st.text_area("사유", height=60)
            approved  = st.text_input("승인자")
            status2   = st.selectbox("상태", ["승인대기","승인완료","처리완료","반려"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_name:
                    st.error("품목명 필수")
                else:
                    dnum = gen_number("DSP")
                    conn = get_db()
                    conn.execute("""INSERT INTO disposal
                        (disposal_number,item_name,quantity,reason,disposal_type,approved_by,status)
                        VALUES(?,?,?,?,?,?,?)""",
                        (dnum, item_name, qty2, reason, d_type, approved, status2))
                    conn.commit(); conn.close()
                    st.success(f"폐기 {dnum} 등록!"); st.rerun()
    with col_list2:
        conn = get_db()
        df2 = pd.read_sql_query("""
            SELECT disposal_number AS 처리번호, item_name AS 품목,
                   quantity AS 수량, disposal_type AS 유형,
                   approved_by AS 승인자, status AS 상태, created_at AS 등록일
            FROM disposal ORDER BY id DESC""", conn)
        conn.close()
        if not df2.empty:

            st.dataframe(df2, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (폐기) ──────────────────────────
            if not df2.empty if hasattr(df2, 'empty') else df2 is not None:
                _row_opts_disposal = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM disposal ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_disposal[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_disposal:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_disposal = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_disposal.keys()),
                        key="_rbsel_disposal", label_visibility="collapsed"
                    )
                    _rb_id_disposal = _row_opts_disposal[_rb_sel_disposal]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_disposal"):
                        st.session_state[f"_edit_disposal"] = _rb_id_disposal
                        st.session_state[f"_del_disposal"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_disposal"):
                        st.session_state[f"_del_disposal"]  = _rb_id_disposal
                        st.session_state[f"_edit_disposal"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_disposal"):
                    _del_id_disposal = st.session_state[f"_del_disposal"]
                    st.warning(f"⚠️ ID **{_del_id_disposal}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_disposal"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM disposal WHERE id = ?", (_del_id_disposal,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_disposal"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_disposal"):
                        st.session_state[f"_del_disposal"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_disposal"):
                    _edit_id_disposal = st.session_state[f"_edit_disposal"]
                    try:
                        _cx_e = get_db()
                        _edit_row_disposal = dict(_cx_e.execute(
                            "SELECT * FROM disposal WHERE id=?", (_edit_id_disposal,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_disposal = {}
                    with st.expander(f"✏️ 폐기 수정 — ID {_edit_id_disposal}", expanded=True):
                        if not _edit_row_disposal:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_disposal = [c for c in _edit_row_disposal if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_disposal)))
                            _ecols = st.columns(_ncols)
                            _new_vals_disposal = {}
                            for _i, _fc in enumerate(_edit_fields_disposal):
                                _cv = _edit_row_disposal[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_disposal[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_fc}_disposal")
                                else:
                                    _new_vals_disposal[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_fc}_disposal")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_disposal"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_disposal])
                                _set_params = list(_new_vals_disposal.values()) + [_edit_id_disposal]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE disposal SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_disposal"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_disposal"):
                                st.session_state[f"_edit_disposal"] = None; st.rerun()


        else:

            st.info("폐기 없음")

# ══════════════════════════════════════════════════════
# LOT·시리얼 관리
# ══════════════════════════════════════════════════════
with tabs["lot"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("LOT / 시리얼 등록")
        conn = get_db()
        items_lot = [r[0] for r in conn.execute("SELECT DISTINCT item_name FROM inventory").fetchall()]
        conn.close()
        with st.form("lot_f", clear_on_submit=True):
            li = st.selectbox("품목", items_lot if items_lot else ["직접입력"])
            a,b = st.columns(2); lot_n = a.text_input("LOT 번호"); ser_n = b.text_input("시리얼 번호")
            c,d = st.columns(2); mfg_d = c.date_input("제조일"); exp_d = d.date_input("유통기한", value=date.today()+timedelta(days=365))
            e,f = st.columns(2); lot_qty = e.number_input("수량", min_value=1, value=1); wh_lot = f.text_input("창고/Bin")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                try:
                    conn = get_db()
                    conn.execute("""UPDATE inventory SET lot_number=?, expiry_date=?, serial_number=?
                        WHERE item_name=?""", (lot_n, str(exp_d), ser_n, li))
                    conn.execute("""INSERT INTO stock_movements(movement_number,item_code,item_name,movement_type,quantity,warehouse,lot_number)
                        VALUES(?,?,?,?,?,?,?)""", (gen_number("LOT"), li, li, "LOT등록", lot_qty, wh_lot, lot_n))
                    conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("LOT / 유통기한 현황")
        conn = get_db()
        df_lot = pd.read_sql_query("""
            SELECT item_name AS 품목, lot_number AS LOT번호, serial_number AS 시리얼,
                   stock_qty AS 재고, expiry_date AS 유통기한,
                   CAST(DATEDIFF(expiry_date, CURDATE()) AS SIGNED) AS 잔여일,
                   warehouse AS 창고
            FROM inventory WHERE lot_number IS NOT NULL AND CHAR_LENGTH(lot_number)>0
            ORDER BY expiry_date""", conn)
        conn.close()
        if df_lot.empty: st.info("LOT 등록 없음")
        else:
            today_s = datetime.now().strftime("%Y-%m-%d")
            d30 = (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d")
            exp_soon = df_lot[df_lot['유통기한'] <= d30]
            if not exp_soon.empty: st.error(f"⚠️ 30일 내 유통기한 만료: {len(exp_soon)}개")
            def lot_color(r):
                if str(r['유통기한']) < today_s: return ['background-color:#fee2e2']*len(r)
                if str(r['유통기한']) <= d30: return ['background-color:#fef9c3']*len(r)
                return ['']*len(r)
            st.dataframe(df_lot.style.apply(lot_color, axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (LOT) ──────────────────────────
            if not df_lot.empty if hasattr(df_lot, 'empty') else df_lot is not None:
                _row_opts_inventory = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM inventory ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
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
                    with st.expander(f"✏️ LOT 수정 — ID {_edit_id_inventory}", expanded=True):
                        if not _edit_row_inventory:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_inventory = [c for c in _edit_row_inventory if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_inventory)))
                            _ecols = st.columns(_ncols)
                            _new_vals_inventory = {}
                            for _i, _fc in enumerate(_edit_fields_inventory):
                                _cv = _edit_row_inventory[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_inventory[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_fc}_inventory")
                                else:
                                    _new_vals_inventory[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_fc}_inventory")
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


# ══════════════════════════════════════════════════════
# 출고지시 (FIFO/FEFO)
# ══════════════════════════════════════════════════════
with tabs["issue"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("📤 출고지시 등록")
        st.caption("FEFO(유통기한 빠른 것 먼저) / FIFO(입고 순서) 자동 적용")
        conn = get_db()
        items_issue = [r[0] for r in conn.execute("SELECT DISTINCT item_name FROM inventory WHERE stock_qty>0").fetchall()]
        conn.close()
        with st.form("issue_f", clear_on_submit=True):
            iss_item = st.selectbox("출고 품목 *", items_issue if items_issue else ["없음"])
            a,b = st.columns(2); iss_qty = a.number_input("출고수량", min_value=1, value=1)
            iss_method = b.selectbox("피킹방식", ["FEFO(유통기한)", "FIFO(입고순)", "수동"])
            iss_to = st.text_input("출고처 (SO번호 또는 생산오더)")
            iss_note = st.text_area("비고", height=40)
            if st.form_submit_button("✅ 출고지시", use_container_width=True):
                if not items_issue: st.error("재고 없음")
                else:
                    try:
                        conn = get_db()
                        # 재고 차감
                        avail = conn.execute("SELECT COALESCE(stock_qty,0) FROM inventory WHERE item_name=?", (iss_item,)).fetchone()
                        if not avail or avail[0] < iss_qty:
                            st.error(f"재고 부족 (가용:{avail[0] if avail else 0})")
                        else:
                            conn.execute("UPDATE inventory SET stock_qty=stock_qty-? WHERE item_name=?", (iss_qty, iss_item))
                            conn.execute("""INSERT INTO stock_movements(movement_number,item_code,item_name,movement_type,quantity,reference_number)
                                VALUES(?,?,?,?,?,?)""", (gen_number("ISS"), iss_item, iss_item, f"출고({iss_method})", iss_qty, iss_to))
                            # ── SD 배송 상태 자동 연동 ──────────────────
                            if iss_to:
                                try:
                                    conn.execute("""UPDATE sales_orders SET status='배송중'
                                        WHERE order_number=? AND status IN ('출하준비','생산/조달중','주문접수')""", (iss_to,))
                                except: pass
                            conn.commit(); conn.close()
                            st.success(f"출고지시 완료 — {iss_method} 적용" + (" (SD 상태→배송중)" if iss_to else "")); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("출고 이력")
        conn = get_db()
        df_iss = pd.read_sql_query("""
            SELECT movement_number AS 출고번호, item_name AS 품목,
                   quantity AS 수량, reference_number AS 참조,
                   created_at AS 출고일
            FROM stock_movements WHERE movement_type LIKE '출고%%'
            ORDER BY id DESC LIMIT 50""", conn)
        conn.close()
        if df_iss.empty: st.info("출고 이력 없음")
        else: st.dataframe(df_iss, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("📋 FEFO 피킹 우선순위")
        conn = get_db()
        df_fefo = pd.read_sql_query("""
            SELECT item_name AS 품목, lot_number AS LOT, stock_qty AS 재고,
                   expiry_date AS 유통기한,
                   CAST(DATEDIFF(expiry_date, CURDATE()) AS SIGNED) AS 잔여일,
                   warehouse AS 창고
            FROM inventory WHERE stock_qty>0 AND expiry_date IS NOT NULL
            ORDER BY expiry_date, item_name""", conn)
        conn.close()
        if df_fefo.empty: st.info("유통기한 등록 재고 없음")
        else: st.dataframe(df_fefo, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════
# 안전재고 알림
# ══════════════════════════════════════════════════════
with tabs["safety"]:
    st.subheader("🔔 안전재고 모니터링")
    conn = get_db()
    df_safety = pd.read_sql_query("""
        SELECT m.material_code AS 자재코드, m.material_name AS 품목,
               COALESCE(i.stock_qty, 0) AS 현재고,
               m.min_stock AS 안전재고,
               m.max_stock AS 최대재고,
               COALESCE(i.stock_qty,0) - m.min_stock AS 여유재고,
               CASE
                   WHEN COALESCE(i.stock_qty,0) = 0 THEN '🔴 재고없음'
                   WHEN COALESCE(i.stock_qty,0) < m.min_stock THEN '🟠 안전재고미달'
                   WHEN COALESCE(i.stock_qty,0) < m.min_stock * 1.2 THEN '🟡 경고'
                   ELSE '🟢 정상'
               END AS 상태
        FROM materials m
        LEFT JOIN inventory i ON m.material_code = i.item_code
        WHERE m.min_stock > 0
        ORDER BY 여유재고""", conn)
    conn.close()
    if df_safety.empty:
        st.info("안전재고 기준이 설정된 품목 없음 (자재마스터에서 min_stock 설정)")
    else:
        danger = df_safety[df_safety['상태'].isin(['🔴 재고없음', '🟠 안전재고미달'])]
        warn = df_safety[df_safety['상태'] == '🟡 경고']
        c1,c2,c3 = st.columns(3)
        c1.metric("재고없음·미달", f"{len(danger)}품목", delta_color="inverse")
        c2.metric("경고", f"{len(warn)}품목", delta_color="inverse")
        c3.metric("정상", f"{len(df_safety)-len(danger)-len(warn)}품목")
        if not danger.empty:
            st.error("⚠️ 즉시 발주 필요 품목")
            st.dataframe(danger, use_container_width=True, hide_index=True)
        if not warn.empty:
            st.warning("주의 품목")
            st.dataframe(warn, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("전체 안전재고 현황")
        st.dataframe(df_safety, use_container_width=True, hide_index=True)


with tabs["bi"]:
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        HAS_PL = True
    except ImportError:
        HAS_PL = False

    if not HAS_PL:
        st.warning("plotly 설치 필요: `pip install plotly`")
    else:
        from datetime import datetime, timedelta
        conn = get_db()
        st.subheader("📊 재고 분석 대시보드")

        # KPI
        total_items = conn.execute("SELECT COUNT(DISTINCT item_code) FROM inventory WHERE stock_qty>0").fetchone()[0]
        zero_items  = conn.execute("""SELECT COUNT(*) FROM materials m
                                      LEFT JOIN inventory i ON m.material_code=i.item_code
                                      WHERE COALESCE(i.stock_qty,0)=0""").fetchone()[0]
        total_val   = conn.execute("""SELECT COALESCE(SUM(i.stock_qty*COALESCE(m.new_avg,mat.standard_price,0)),0)
                                      FROM inventory i
                                      LEFT JOIN materials mat ON i.item_code=mat.material_code
                                      LEFT JOIN (SELECT item_code, new_avg_price AS new_avg FROM moving_avg_price
                                                 WHERE id IN (SELECT MAX(id) FROM moving_avg_price GROUP BY item_code)) m
                                             ON i.item_code=m.item_code""").fetchone()[0]
        move_cnt    = conn.execute("SELECT COUNT(*) FROM stock_movements WHERE created_at>=DATE_SUB(CURDATE(), INTERVAL 30 DAY)").fetchone()[0]

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("보유 품목수", f"{total_items}개")
        c2.metric("재고 0 품목", f"{zero_items}개", delta_color="inverse")
        c3.metric("총 재고자산가치", f"₩{total_val:,.0f}")
        c4.metric("30일 재고이동", f"{move_cnt}건")
        st.divider()

        # 재고 현황 + 창고별
        col_l, col_r = st.columns(2)
        with col_l:
            df_top = pd.read_sql_query("""
                SELECT i.item_name AS 품목, i.stock_qty AS 재고수량,
                       ROUND(i.stock_qty*COALESCE(m.new_avg,mat.standard_price,0),0) AS 재고금액
                FROM inventory i
                LEFT JOIN materials mat ON i.item_code=mat.material_code
                LEFT JOIN (SELECT item_code, new_avg_price AS new_avg FROM moving_avg_price
                           WHERE id IN (SELECT MAX(id) FROM moving_avg_price GROUP BY item_code)) m
                       ON i.item_code=m.item_code
                WHERE i.stock_qty>0 ORDER BY 재고금액 DESC LIMIT 10""", conn)
            if not df_top.empty:
                fig = px.bar(df_top, y='품목', x='재고금액', orientation='h',
                             color='재고금액', color_continuous_scale='Teal',
                             title="재고금액 TOP10")
                fig.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            df_wh = pd.read_sql_query("""
                SELECT warehouse AS 창고, ROUND(SUM(stock_qty),0) AS 수량
                FROM inventory WHERE stock_qty>0 GROUP BY warehouse""", conn)
            if not df_wh.empty:
                fig2 = px.pie(df_wh, names='창고', values='수량',
                              title="창고별 재고수량 분포", hole=0.4)
                fig2.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig2, use_container_width=True)

        # ABC 분석
        st.subheader("🏷️ ABC 재고 분류")
        st.caption("재고금액 기준 — A: 상위 70% / B: 70~90% / C: 나머지")
        df_abc = pd.read_sql_query("""
            SELECT i.item_code AS 자재코드, i.item_name AS 품목,
                   i.stock_qty AS 수량,
                   ROUND(i.stock_qty*COALESCE(m.new_avg,mat.standard_price,0),0) AS 재고금액
            FROM inventory i
            LEFT JOIN materials mat ON i.item_code=mat.material_code
            LEFT JOIN (SELECT item_code, new_avg_price AS new_avg FROM moving_avg_price
                       WHERE id IN (SELECT MAX(id) FROM moving_avg_price GROUP BY item_code)) m
                   ON i.item_code=m.item_code
            WHERE i.stock_qty>0 ORDER BY 재고금액 DESC""", conn)

        if not df_abc.empty:
            tv = df_abc['재고금액'].sum()
            df_abc['누적비중'] = df_abc['재고금액'].cumsum()/tv*100
            df_abc['ABC'] = df_abc['누적비중'].apply(
                lambda x: 'A' if x<=70 else ('B' if x<=90 else 'C'))
            clr = {'A':'#ef4444','B':'#f97316','C':'#6b7280'}

            col_a, col_b = st.columns([3,1])
            with col_a:
                fig3 = px.bar(df_abc, x='품목', y='재고금액',
                              color='ABC', color_discrete_map=clr, title="ABC 분류")
                fig3.update_layout(height=320, margin=dict(l=0,r=0,t=40,b=0),
                                   xaxis_tickangle=-30)
                st.plotly_chart(fig3, use_container_width=True)
            with col_b:
                ab_sum = df_abc.groupby('ABC').agg(
                    품목수=('품목','count'),
                    금액=('재고금액','sum')).reset_index()
                ab_sum['비중%'] = (ab_sum['금액']/tv*100).round(1)
                st.dataframe(ab_sum, use_container_width=True, hide_index=True)

        # 재고 회전율
        st.subheader("🔄 재고 회전율")
        df_turn = pd.read_sql_query("""
            SELECT g.item_name AS 품목,
                   SUM(g.received_qty-g.rejected_qty) AS 입고수량,
                   COALESCE(i.stock_qty,0) AS 현재고,
                   ROUND(SUM(g.received_qty-g.rejected_qty)*1.0/NULLIF(COALESCE(i.stock_qty,0),0),2) AS 회전율
            FROM goods_receipts g
            LEFT JOIN inventory i ON g.item_name=i.item_code
            WHERE g.created_at>=DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            GROUP BY g.item_name, i.stock_qty HAVING COALESCE(i.stock_qty,0)>0
            ORDER BY 회전율 DESC LIMIT 15""", conn)
        if not df_turn.empty:
            fig4 = px.bar(df_turn, x='품목', y='회전율',
                          color='회전율', color_continuous_scale='RdYlGn',
                          title="품목별 재고 회전율 (최근 90일)")
            fig4.add_hline(y=df_turn['회전율'].mean(), line_dash="dash",
                           line_color="blue", annotation_text="평균")
            fig4.update_layout(height=300, margin=dict(l=0,r=0,t=40,b=0),
                               xaxis_tickangle=-30, showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

        conn.close()


# ══════════════════════════════════════════════════════
# 탭 7 — 수요·폐기 예측
# ══════════════════════════════════════════════════════
with tabs["pred"]:
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        import numpy as np
        from datetime import datetime, timedelta
        HAS_PL2 = True
    except ImportError:
        HAS_PL2 = False

    if not HAS_PL2:
        st.warning("plotly / numpy 설치 필요")
    else:
        st.subheader("🔮 수요 예측 · 폐기 위험 분석")
        st.caption("입고 이력 기반 이동평균 수요 예측 — 유통기한 있는 품목의 폐기 위험도 산출")

        conn = get_db()

        # 수요 예측 섹션
        st.markdown("#### 📈 품목별 수요 예측 (이동평균)")

        items_pred = [r[0] for r in conn.execute("""
            SELECT DISTINCT item_name FROM goods_receipts
            GROUP BY item_name HAVING COUNT(*)>=3
            ORDER BY COUNT(*) DESC LIMIT 30""").fetchall()]

        if not items_pred:
            st.info("예측에 필요한 입고 이력이 부족합니다 (품목당 최소 3건 필요)")
        else:
            col_p1, col_p2 = st.columns([1,3])
            with col_p1:
                sel_pred = st.selectbox("품목 선택", items_pred, key="wm_pred_item")
                ma_window = st.slider("이동평균 기간(월)", 2, 6, 3, key="wm_ma")
                pred_months = st.slider("예측 개월수", 1, 6, 3, key="wm_pred_m")

            with col_p2:
                # 월별 수요(입고) 집계
                df_demand = pd.read_sql_query("""
                    SELECT DATE_FORMAT(created_at,'%%Y-%%m') AS 월,
                           SUM(received_qty-rejected_qty) AS 수요량
                    FROM goods_receipts WHERE item_name=?
                    GROUP BY DATE_FORMAT(created_at,'%%Y-%%m') ORDER BY 월""",
                    conn, params=[sel_pred])

                if len(df_demand) < 2:
                    st.info("데이터가 2개월 이상 필요합니다")
                else:
                    # 이동평균 계산
                    df_demand['이동평균'] = df_demand['수요량'].rolling(
                        window=ma_window, min_periods=1).mean().round(1)

                    # 추세 기반 예측 (단순 선형)
                    y = df_demand['수요량'].values
                    x = np.arange(len(y))
                    if len(x) >= 2:
                        coeffs = np.polyfit(x, y, 1)
                        slope, intercept = coeffs[0], coeffs[1]
                    else:
                        slope, intercept = 0, y[-1]

                    last_date = df_demand['월'].iloc[-1]
                    last_dt = datetime.strptime(last_date, "%Y-%m")
                    future_months = []
                    future_pred   = []
                    for i in range(1, pred_months+1):
                        fd = last_dt + timedelta(days=31*i)
                        future_months.append(fd.strftime("%Y-%m"))
                        pred_val = max(0, slope*(len(y)+i-1)+intercept)
                        future_pred.append(round(pred_val, 1))

                    # 안전재고 = 평균 수요 × 1.5
                    avg_demand = df_demand['수요량'].mean()
                    safety_stock = round(avg_demand * 1.5, 0)

                    # 현재 재고
                    curr_stock = conn.execute(
                        "SELECT COALESCE(stock_qty,0) FROM inventory WHERE item_code=?",
                        (sel_pred,)).fetchone()
                    curr_stock = curr_stock[0] if curr_stock else 0

                    # 재고 소진 예상 시점
                    cumulative = 0
                    stockout_month = None
                    for i, fp in enumerate(future_pred):
                        cumulative += fp
                        if cumulative >= curr_stock:
                            stockout_month = future_months[i]
                            break

                    # KPI
                    k1,k2,k3,k4 = st.columns(4)
                    k1.metric("평균 월 수요", f"{avg_demand:.0f}개")
                    k2.metric("권장 안전재고", f"{safety_stock:.0f}개")
                    k3.metric("현재고", f"{curr_stock}개")
                    k4.metric("재고소진 예상",
                              stockout_month if stockout_month else "6개월 이상",
                              delta_color="inverse" if stockout_month else "normal")

                    # 차트
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=df_demand['월'], y=df_demand['수요량'],
                                         name='실적 수요량', marker_color='#93c5fd'))
                    fig.add_trace(go.Scatter(x=df_demand['월'], y=df_demand['이동평균'],
                                             name=f'{ma_window}개월 이동평균',
                                             line=dict(color='#2563eb',width=2), mode='lines'))
                    fig.add_trace(go.Scatter(x=future_months, y=future_pred,
                                             name='예측', mode='lines+markers',
                                             line=dict(color='#f97316',width=2,dash='dash'),
                                             marker=dict(size=8)))
                    fig.add_hline(y=safety_stock, line_dash="dot", line_color="red",
                                  annotation_text=f"안전재고 {safety_stock:.0f}")
                    fig.update_layout(title=f"{sel_pred} 수요 예측",
                                      height=320, margin=dict(l=0,r=0,t=40,b=0),
                                      legend=dict(orientation="h",y=1.1))
                    st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # 폐기 위험 분석
        st.markdown("#### ⚠️ 폐기 위험 분석 (유통기한 / 장기 미출고)")
        st.caption("유통기한 컬럼이 없는 품목은 마지막 이동 후 경과일로 위험도를 산출합니다")

        df_risk = pd.read_sql_query("""
            SELECT i.item_code AS 자재코드, i.item_name AS 품목,
                   i.warehouse AS 창고, i.stock_qty AS 재고수량,
                   MAX(sm.created_at) AS 마지막이동일,
                   CAST(DATEDIFF(CURDATE(), MAX(sm.created_at)) AS SIGNED) AS 미이동일수
            FROM inventory i
            LEFT JOIN stock_movements sm ON i.item_name=sm.item_name
            WHERE i.stock_qty>0
            GROUP BY i.item_code, i.item_name, i.warehouse, i.stock_qty
            ORDER BY 미이동일수 DESC""", conn)

        if df_risk.empty:
            st.info("재고 데이터 없음")
        else:
            # 위험등급 분류
            def risk_grade(days):
                if days is None or days == '':
                    return '정보없음'
                try:
                    d = int(days)
                    if d >= 180: return '🔴 폐기위험'
                    if d >= 90:  return '🟠 주의'
                    if d >= 30:  return '🟡 관찰'
                    return '🟢 정상'
                except:
                    return '정보없음'

            df_risk['위험등급'] = df_risk['미이동일수'].apply(risk_grade)

            # 위험등급별 색상
            color_map = {'🔴 폐기위험':'#ef4444','🟠 주의':'#f97316',
                         '🟡 관찰':'#eab308','🟢 정상':'#22c55e','정보없음':'#9ca3af'}

            col_r1, col_r2 = st.columns([2,1])
            with col_r1:
                risk_high = df_risk[df_risk['위험등급'].isin(['🔴 폐기위험','🟠 주의'])]
                if not risk_high.empty:
                    st.error(f"⚠️ 폐기위험·주의 품목: {len(risk_high)}개")
                    st.dataframe(risk_high[['자재코드','품목','창고','재고수량',
                                            '마지막이동일','미이동일수','위험등급']],
                                 use_container_width=True, hide_index=True)
                else:
                    st.success("✅ 폐기 위험 품목 없음")

            with col_r2:
                risk_sum = df_risk.groupby('위험등급').size().reset_index(name='품목수')
                fig5 = px.pie(risk_sum, names='위험등급', values='품목수',
                              color='위험등급', color_discrete_map=color_map,
                              title="폐기 위험등급 분포")
                fig5.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig5, use_container_width=True)

            # 미이동일수 분포 히스토그램
            df_valid = df_risk[df_risk['미이동일수'].notna()]
            if not df_valid.empty:
                fig6 = px.histogram(df_valid, x='미이동일수', nbins=20,
                                    color='위험등급', color_discrete_map=color_map,
                                    title="재고 미이동일수 분포",
                                    labels={'미이동일수':'미이동일수 (일)'})
                fig6.add_vline(x=90, line_dash="dash", line_color="orange", annotation_text="90일")
                fig6.add_vline(x=180, line_dash="dash", line_color="red", annotation_text="180일")
                fig6.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig6, use_container_width=True)

        conn.close()

# ══ Putaway 위치 최적화 ══════════════════════════════════════════
with tabs["putaway"]:
    # MySQL: putaway_rules, putaway_tasks 테이블은 db.py init_db()에서 이미 생성됨

    col_l, col_r = st.columns([1,2])
    with col_l:
        st.subheader("📍 Putaway 규칙 등록")
        st.caption("품목/카테고리별 최적 보관 위치 규칙 설정")
        with st.form("pa_rule_f", clear_on_submit=True):
            item_pa=st.text_input("품목명 (공백=카테고리 전체 적용)")
            cat_pa=st.selectbox("카테고리",["원자재","반제품","완제품","소모품","냉장품","위험물","대형품"])
            a,b=st.columns(2); zone_pa=a.text_input("보관 구역(Zone)"); bin_pa=b.text_input("Bin 위치")
            rt=st.selectbox("규칙 유형",["ABC 분류","무게기준","온도요건","회전율기준","FIFO"])
            pri=st.slider("우선순위",1,5,1); note_pa=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 규칙 등록",use_container_width=True):
                try:
                    conn=get_db()
                    conn.execute("INSERT INTO putaway_rules(item_name,item_category,preferred_zone,preferred_bin,priority,rule_type,note) VALUES(?,?,?,?,?,?,?)",
                        (item_pa,cat_pa,zone_pa,bin_pa,pri,rt,note_pa))
                    conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")

        st.divider()
        st.subheader("📋 Putaway 작업 생성")
        conn=get_db()
        pending_asn=[r for r in conn.execute("SELECT item_name,received_qty FROM inbound_inspection WHERE result IN ('정상','부분불량') ORDER BY id DESC LIMIT 20").fetchall()]
        conn.close()
        if pending_asn:
            asn_map={f"{r['item_name']} ({r['received_qty']}개)":r for r in pending_asn}
            sel_asn=st.selectbox("입고 품목",list(asn_map.keys()))
            asn_d=asn_map[sel_asn]
            # 규칙 자동 추천
            conn=get_db()
            rule=conn.execute("SELECT preferred_zone,preferred_bin FROM putaway_rules WHERE item_name=? OR item_name='' ORDER BY priority LIMIT 1",(asn_d['item_name'],)).fetchone()
            conn.close()
            a2,b2=st.columns(2)
            to_zone=a2.text_input("배치 구역",value=rule['preferred_zone'] if rule else "")
            to_bin=b2.text_input("Bin",value=rule['preferred_bin'] if rule else "")
            worker=st.text_input("담당자")
            if st.button("📋 작업 생성",use_container_width=True):
                try:
                    conn=get_db()
                    conn.execute("INSERT INTO putaway_tasks(task_number,item_name,quantity,to_zone,to_bin,assigned_to) VALUES(?,?,?,?,?,?)",
                        (gen_number("PUT"),asn_d['item_name'],asn_d['received_qty'],to_zone,to_bin,worker))
                    conn.commit(); conn.close(); st.success("작업 생성!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")

    with col_r:
        st.subheader("Putaway 작업 현황")
        conn=get_db(); df_put=pd.read_sql_query("""
            SELECT task_number AS 작업번호, item_name AS 품목, quantity AS 수량,
                   from_location AS 출발, to_zone AS 구역, to_bin AS Bin,
                   assigned_to AS 담당자, status AS 상태, created_at AS 생성일시
            FROM putaway_tasks ORDER BY id DESC LIMIT 50""", conn); conn.close()
        if df_put.empty: st.info("없음")
        else:
            # 상태 변경
            open_put=[r for r in get_db().execute("SELECT id,task_number,item_name FROM putaway_tasks WHERE status='대기'").fetchall()]
            get_db().close()
            if open_put:
                put_map={f"{r['task_number']}-{r['item_name']}":r['id'] for r in open_put}
                c1,c2=st.columns(2); sel_put=c1.selectbox("완료처리",list(put_map.keys())); new_put_st=c2.selectbox("상태",["진행중","완료"])
                if st.button("🔄 상태 변경",use_container_width=True):
                    conn=get_db(); conn.execute("UPDATE putaway_tasks SET status=? WHERE id=?",(new_put_st,put_map[sel_put]))
                    conn.commit(); conn.close(); st.rerun()
            st.dataframe(df_put, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (Putaway규칙) ──────────────────────────
            if not df_put.empty if hasattr(df_put, 'empty') else df_put is not None:
                _row_opts_putaway_rules = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 카테고리 FROM putaway_rules ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('카테고리','')}"
                        _row_opts_putaway_rules[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_putaway_rules:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_putaway_rules = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_putaway_rules.keys()),
                        key="_rbsel_putaway_rules", label_visibility="collapsed"
                    )
                    _rb_id_putaway_rules = _row_opts_putaway_rules[_rb_sel_putaway_rules]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_putaway_rules"):
                        st.session_state[f"_edit_putaway_rules"] = _rb_id_putaway_rules
                        st.session_state[f"_del_putaway_rules"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_putaway_rules"):
                        st.session_state[f"_del_putaway_rules"]  = _rb_id_putaway_rules
                        st.session_state[f"_edit_putaway_rules"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_putaway_rules"):
                    _del_id_putaway_rules = st.session_state[f"_del_putaway_rules"]
                    st.warning(f"⚠️ ID **{_del_id_putaway_rules}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_putaway_rules"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM putaway_rules WHERE id = ?", (_del_id_putaway_rules,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_putaway_rules"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_putaway_rules"):
                        st.session_state[f"_del_putaway_rules"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_putaway_rules"):
                    _edit_id_putaway_rules = st.session_state[f"_edit_putaway_rules"]
                    try:
                        _cx_e = get_db()
                        _edit_row_putaway_rules = dict(_cx_e.execute(
                            "SELECT * FROM putaway_rules WHERE id=?", (_edit_id_putaway_rules,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_putaway_rules = {}
                    with st.expander(f"✏️ Putaway규칙 수정 — ID {_edit_id_putaway_rules}", expanded=True):
                        if not _edit_row_putaway_rules:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_putaway_rules = [c for c in _edit_row_putaway_rules if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_putaway_rules)))
                            _ecols = st.columns(_ncols)
                            _new_vals_putaway_rules = {}
                            for _i, _fc in enumerate(_edit_fields_putaway_rules):
                                _cv = _edit_row_putaway_rules[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_putaway_rules[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_fc}_putaway_rules")
                                else:
                                    _new_vals_putaway_rules[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_fc}_putaway_rules")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_putaway_rules"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_putaway_rules])
                                _set_params = list(_new_vals_putaway_rules.values()) + [_edit_id_putaway_rules]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE putaway_rules SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_putaway_rules"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_putaway_rules"):
                                st.session_state[f"_edit_putaway_rules"] = None; st.rerun()


        st.divider()
        st.subheader("📋 Putaway 규칙 목록")
        conn=get_db(); df_par=pd.read_sql_query("""
            SELECT item_name AS 품목, item_category AS 카테고리,
                   preferred_zone AS 구역, preferred_bin AS Bin,
                   rule_type AS 규칙유형, priority AS 우선순위
            FROM putaway_rules ORDER BY priority""", conn); conn.close()
        if not df_par.empty: st.dataframe(df_par, use_container_width=True, hide_index=True)


# ══ 피킹 웨이브 관리 ══════════════════════════════════════════
with tabs["wave"]:
    # MySQL: pick_waves, pick_wave_lines 테이블은 db.py init_db()에서 이미 생성됨

    st.subheader("🌊 피킹 웨이브 관리")
    st.caption("복수 출하건을 묶어 최적 동선으로 일괄 피킹")

    col_form, col_list = st.columns([1,2])
    with col_form:
        st.subheader("웨이브 생성")
        conn=get_db()
        pend_deli=[r for r in conn.execute("SELECT id,delivery_number,item_name,delivery_qty FROM deliveries WHERE status IN ('출하준비','피킹대기') ORDER BY delivery_date").fetchall()]
        conn.close()
        if not pend_deli:
            st.info("피킹 대기 출하 없음")
        else:
            deli_opts={f"{r['delivery_number']}-{r['item_name']}({r['delivery_qty']})":r for r in pend_deli}
            sel_delis=st.multiselect("출하건 선택 (복수)",list(deli_opts.keys()))
            a,b=st.columns(2)
            wave_type=a.selectbox("웨이브 유형",["배치피킹","존피킹","싱글피킹","클러스터피킹"])
            picker=b.text_input("피커")
            wave_date=st.date_input("피킹일",value=date.today())
            if st.button("🌊 웨이브 생성",use_container_width=True,type="primary"):
                if not sel_delis: st.error("출하건 선택 필수")
                else:
                    try:
                        conn=get_db()
                        wnum=gen_number("WV")
                        conn.execute("INSERT INTO pick_waves(wave_number,wave_date,wave_type,picker,total_lines,status) VALUES(?,?,?,?,?,?)",
                            (wnum,str(wave_date),wave_type,picker,len(sel_delis),"대기"))
                        wid=conn.execute("SELECT id FROM pick_waves WHERE wave_number=?",(wnum,)).fetchone()[0]
                        for sk in sel_delis:
                            d=deli_opts[sk]
                            # bin 위치 조회
                            bin_loc=conn.execute("SELECT bin_code FROM inventory i JOIN storage_bins sb ON i.bin_id=sb.id WHERE i.item_name=? LIMIT 1",(d['item_name'],)).fetchone()
                            conn.execute("INSERT INTO pick_wave_lines(wave_id,delivery_id,item_name,bin_location,required_qty) VALUES(?,?,?,?,?)",
                                (wid,d['id'],d['item_name'],bin_loc[0] if bin_loc else "미지정",d['delivery_qty']))
                            conn.execute("UPDATE deliveries SET status='피킹중' WHERE id=?",(d['id'],))
                        conn.commit(); conn.close(); st.success(f"웨이브 {wnum} 생성! ({len(sel_delis)}건)"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")

    with col_list:
        st.subheader("웨이브 현황")
        conn=get_db(); df_wv=pd.read_sql_query("""
            SELECT w.wave_number AS 웨이브번호, w.wave_date AS 피킹일,
                   w.wave_type AS 유형, w.picker AS 피커,
                   w.total_lines AS 전체, w.picked_lines AS 완료,
                   ROUND(w.picked_lines*100.0/GREATEST(w.total_lines,1),1) AS 진척률,
                   w.status AS 상태
            FROM pick_waves w ORDER BY w.id DESC LIMIT 30""", conn)
        conn.close()
        if df_wv.empty: st.info("없음")
        else:
            st.dataframe(df_wv, use_container_width=True, hide_index=True)
            st.divider()
            # 웨이브 피킹 처리
            open_waves=[r for r in get_db().execute("SELECT id,wave_number FROM pick_waves WHERE status IN ('대기','피킹중')").fetchall()]
            get_db().close()
            if open_waves:
                wv_map={r['wave_number']:r['id'] for r in open_waves}
                sel_wv=st.selectbox("웨이브 선택",list(wv_map.keys()))
                conn=get_db(); df_wvl=pd.read_sql_query("""
                    SELECT l.id, l.item_name AS 품목, l.bin_location AS Bin위치,
                           l.required_qty AS 필요수량, l.picked_qty AS 피킹수량, l.status AS 상태
                    FROM pick_wave_lines l WHERE l.wave_id=? ORDER BY l.bin_location""",(wv_map[sel_wv],),conn)
                conn.close()
                if not df_wvl.empty:
                    st.dataframe(df_wvl.drop(columns=['id']),use_container_width=True,hide_index=True)
                    if st.button("✅ 전체 피킹 완료",use_container_width=True,type="primary"):
                        try:
                            conn=get_db()
                            conn.execute("UPDATE pick_wave_lines SET picked_qty=required_qty,status='완료' WHERE wave_id=?",(wv_map[sel_wv],))
                            lines=conn.execute("SELECT COUNT(*) FROM pick_wave_lines WHERE wave_id=?",(wv_map[sel_wv],)).fetchone()[0]
                            conn.execute("UPDATE pick_waves SET picked_lines=?,status='완료' WHERE id=?",(lines,wv_map[sel_wv]))
                            conn.commit(); conn.close(); st.success("웨이브 피킹 완료!"); st.rerun()
                        except Exception as e: st.error(f"오류:{e}")
