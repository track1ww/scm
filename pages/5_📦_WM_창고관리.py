import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number

st.title("📦 WM/EWM – Warehouse Management (창고관리)")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏗️ 창고/Bin 등록", "📥 입고(ASN/검수)", "📊 재고 현황", "🔄 재고 이동", "🔍 재고 실사",
    "📊 재고 분석", "🔮 수요·폐기 예측"])

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

# ══════════════════════════════════════════════════════
# 탭 6 — 재고 분석
# ══════════════════════════════════════════════════════
with tab6:
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
        move_cnt    = conn.execute("SELECT COUNT(*) FROM stock_movements WHERE created_at>=date('now','-30 days')").fetchone()[0]

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
            WHERE g.created_at>=date('now','-90 days')
            GROUP BY g.item_name HAVING 현재고>0
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
with tab7:
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
                    SELECT substr(created_at,1,7) AS 월,
                           SUM(received_qty-rejected_qty) AS 수요량
                    FROM goods_receipts WHERE item_name=?
                    GROUP BY substr(created_at,1,7) ORDER BY 월""",
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
                   CAST(julianday('now')-julianday(MAX(sm.created_at)) AS INTEGER) AS 미이동일수
            FROM inventory i
            LEFT JOIN stock_movements sm ON i.item_code=sm.item_code
            WHERE i.stock_qty>0
            GROUP BY i.item_code, i.warehouse
            ORDER BY 미이동일수 DESC NULLS LAST""", conn)

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
