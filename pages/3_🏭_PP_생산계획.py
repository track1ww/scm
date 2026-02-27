import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number

st.title("🏭 PP – Production Planning (생산계획/MRP)")

tab1, tab2, tab3 = st.tabs(["📐 BOM (자재명세서)", "📅 생산계획", "⚙️ MRP 소요량계산"])

# ── BOM ──────────────────────────────────────────
with tab1:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("BOM 등록")
        with st.form("bom_form", clear_on_submit=True):
            product    = st.text_input("완제품명 *")
            comp_name  = st.text_input("구성 자재명 *")
            comp_code  = st.text_input("자재코드")
            col_a, col_b = st.columns(2)
            qty        = col_a.number_input("소요수량", min_value=0.01, value=1.0, format="%.2f")
            unit       = col_b.selectbox("단위", ["EA","KG","L","M","BOX"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not product or not comp_name:
                    st.error("완제품명, 자재명 필수")
                else:
                    conn = get_db()
                    conn.execute("""INSERT INTO bom
                        (product_name,component_name,component_code,quantity,unit)
                        VALUES(?,?,?,?,?)""",
                        (product, comp_name, comp_code, qty, unit))
                    conn.commit(); conn.close()
                    st.success("BOM 등록 완료!"); st.rerun()
    with col_list:
        st.subheader("BOM 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT product_name AS 완제품, component_code AS 자재코드,
                   component_name AS 구성자재, quantity AS 소요수량, unit AS 단위
            FROM bom ORDER BY product_name, id""", conn)
        conn.close()
        if df.empty:
            st.info("BOM 없음")
        else:
            prod_filter = st.selectbox("완제품 선택", ["전체"] + df['완제품'].unique().tolist())
            if prod_filter != "전체":
                df = df[df['완제품'] == prod_filter]
            st.dataframe(df, use_container_width=True, hide_index=True)

# ── 생산계획 ──────────────────────────────────────────
with tab2:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("생산계획 등록")
        with st.form("pp_form", clear_on_submit=True):
            product   = st.text_input("생산품목 *")
            col_a, col_b = st.columns(2)
            plan_qty  = col_a.number_input("계획수량", min_value=1, value=1)
            work_ctr  = col_b.text_input("작업장")
            col_c, col_d = st.columns(2)
            start_dt  = col_c.date_input("시작일")
            end_dt    = col_d.date_input("완료예정일")
            status    = st.selectbox("상태", ["계획","확정","진행중","완료","취소"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not product:
                    st.error("생산품목 필수")
                else:
                    pnum = gen_number("PP")
                    conn = get_db()
                    conn.execute("""INSERT INTO production_plans
                        (plan_number,product_name,planned_qty,start_date,end_date,work_center,status)
                        VALUES(?,?,?,?,?,?,?)""",
                        (pnum, product, plan_qty, str(start_dt), str(end_dt), work_ctr, status))
                    conn.commit(); conn.close()
                    st.success(f"생산계획 {pnum} 등록!"); st.rerun()
    with col_list:
        st.subheader("생산계획 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT plan_number AS 계획번호, product_name AS 품목,
                   planned_qty AS 계획수량, work_center AS 작업장,
                   start_date AS 시작일, end_date AS 완료예정,
                   status AS 상태
            FROM production_plans ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("생산계획 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            status_cnt = df['상태'].value_counts().reset_index()
            status_cnt.columns = ['상태','건수']
            st.bar_chart(status_cnt.set_index('상태'))

# ── MRP ──────────────────────────────────────────
with tab3:
    st.subheader("⚙️ MRP 소요량 계산")
    st.info("생산계획 기반으로 BOM을 전개하여 자재 소요량을 자동 계산합니다.")

    conn = get_db()
    plans = conn.execute("SELECT plan_number, product_name, planned_qty FROM production_plans WHERE status IN ('확정','진행중')").fetchall()
    boms  = conn.execute("SELECT product_name, component_name, component_code, quantity, unit FROM bom").fetchall()
    inv   = conn.execute("SELECT item_name, stock_qty FROM inventory").fetchall()
    conn.close()

    if not plans:
        st.warning("확정/진행중 생산계획이 없습니다.")
    else:
        inv_map = {i['item_name']: i['stock_qty'] for i in inv}
        bom_map = {}
        for b in boms:
            bom_map.setdefault(b['product_name'], []).append(b)

        rows = []
        for p in plans:
            prod = p['product_name']
            qty  = p['planned_qty']
            comps = bom_map.get(prod, [])
            if not comps:
                rows.append({"계획번호": p['plan_number'], "완제품": prod,
                              "구성자재": "BOM 없음", "소요량": "-",
                              "현재고": "-", "발주필요량": "-"})
            for c in comps:
                required = c['quantity'] * qty
                stock    = inv_map.get(c['component_name'], 0)
                need     = max(0, required - stock)
                rows.append({
                    "계획번호": p['plan_number'], "완제품": prod,
                    "구성자재": c['component_name'],
                    "자재코드": c['component_code'] or "-",
                    "소요량": f"{required:.1f} {c['unit']}",
                    "현재고": stock,
                    "발주필요량": f"🔴 {need:.1f}" if need > 0 else "✅ 충족"
                })

        df_mrp = pd.DataFrame(rows)
        st.dataframe(df_mrp, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📋 MRP 발주요청 등록")
    col_form2, col_list2 = st.columns([1, 2])
    with col_form2:
        with st.form("mrp_form", clear_on_submit=True):
            mat_name = st.text_input("자재명 *")
            req_qty  = st.number_input("필요수량", min_value=1, value=1)
            req_date = st.date_input("필요일")
            source   = st.selectbox("요청출처", ["MRP자동","수동입력","생산계획연동"])
            status   = st.selectbox("상태", ["요청","발주완료","입고완료","취소"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not mat_name:
                    st.error("자재명 필수")
                else:
                    mnum = gen_number("MRP")
                    conn = get_db()
                    conn.execute("""INSERT INTO mrp_requests
                        (mrp_number,material_name,required_qty,required_date,source,status)
                        VALUES(?,?,?,?,?,?)""",
                        (mnum, mat_name, req_qty, str(req_date), source, status))
                    conn.commit(); conn.close()
                    st.success(f"MRP 요청 {mnum} 등록!"); st.rerun()
    with col_list2:
        conn = get_db()
        df_m = pd.read_sql_query("""
            SELECT mrp_number AS MRP번호, material_name AS 자재명,
                   required_qty AS 필요수량, required_date AS 필요일,
                   source AS 출처, status AS 상태
            FROM mrp_requests ORDER BY id DESC""", conn)
        conn.close()
        if not df_m.empty:

            st.dataframe(df_m, use_container_width=True, hide_index=True)

        else:

            st.info("MRP 요청 없음")
