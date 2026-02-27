import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number

st.title("📦 WM/EWM – Warehouse Management (창고관리)")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏗️ 창고/Bin 등록", "📥 입고(ASN/검수)", "📊 재고 현황", "🔄 재고 이동", "🔍 재고 실사"])

# ── 창고 & 빈 등록 ──────────────────────────────────────────
with tab1:
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
                        ON CONFLICT(warehouse_code) DO UPDATE SET
                        warehouse_name=excluded.warehouse_name,
                        location=excluded.location,
                        warehouse_type=excluded.warehouse_type,
                        capacity=excluded.capacity""",
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
                        ON CONFLICT(bin_code) DO NOTHING""",
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
with tab2:
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
                    conn.commit(); conn.close()
                    st.success("검수 등록 완료!"); st.rerun()
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
with tab3:
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
                        ON CONFLICT(item_code) DO UPDATE SET
                        item_name=excluded.item_name, category=excluded.category,
                        warehouse_id=excluded.warehouse_id, warehouse=excluded.warehouse,
                        bin_code=excluded.bin_code, stock_qty=excluded.stock_qty,
                        system_qty=excluded.system_qty, unit_price=excluded.unit_price,
                        min_stock=excluded.min_stock,
                        updated_at=datetime('now','localtime')""",
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
with tab4:
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

        else:

            st.info("이동 이력 없음")

# ── 재고 실사 ──────────────────────────────────────────
with tab5:
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

        else:

            st.info("폐기 없음")
