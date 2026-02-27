import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number, init_mm_extended_db
from datetime import datetime, timedelta

# MM 확장 테이블 초기화
try:
    init_mm_extended_db()
except:
    pass

st.title("🛒 MM – Materials Management (자재관리)")

tabs = st.tabs([
    "🏭 공급사",
    "📦 자재 마스터",
    "💡 구매정보(PIR)",
    "📝 구매요청(PR)",
    "💬 견적(RFQ)",
    "🔀 견적 비교",
    "📄 계약",
    "📋 발주서(PO)",
    "📥 입고(GR)",
    "🧾 송장검증",
    "🧾 세금계산서",
    "💰 지급관리",
    "⭐ 공급사 평가",
    "📊 구매 KPI",
])

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
            email   = st.text_input("이메일")
            address = st.text_area("주소", height=60)
            col_c, col_d = st.columns(2)
            payment = col_c.selectbox("결제조건", ["현금","30일","60일","90일","선불"])
            status  = col_d.selectbox("상태", ["활성","휴면","거래중지"])
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
            SELECT id AS ID, name AS 공급사명, contact AS 담당자,
                   phone AS 전화, email AS 이메일,
                   payment_terms AS 결제조건, status AS 상태,
                   created_at AS 등록일
            FROM suppliers ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("등록된 공급사 없음")
        else:
            search = st.text_input("🔍 검색")
            if search:
                df = df[df['공급사명'].str.contains(search, na=False)]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.metric("총 공급사", len(df))
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
            mat_type = col_a.selectbox("유형", ["원자재","반제품","완제품","소모품","포장재"])
            unit     = col_b.selectbox("단위", ["EA","KG","L","M","BOX","SET","TON"])
            col_c, col_d = st.columns(2)
            category = col_c.text_input("카테고리")
            storage  = col_d.text_input("보관조건")
            std_price= st.number_input("표준단가", min_value=0.0, format="%.2f")
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
                            storage_condition=excluded.storage_condition,standard_price=excluded.standard_price""",
                            (mat_code,mat_name,mat_type,unit,category,storage,std_price))
                        conn.commit(); conn.close()
                        st.success("저장 완료!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
    with col_list:
        st.subheader("자재 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT material_code AS 자재코드, material_name AS 자재명,
                   material_type AS 유형, unit AS 단위,
                   category AS 카테고리, standard_price AS 표준단가
            FROM materials ORDER BY material_code""", conn)
        conn.close()
        if df.empty:
            st.info("자재 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.metric("총 자재수", len(df))

# ── 3. PIR ──────────────────────────────────────
with tabs[2]:
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
                             disc_p,price_unit_p,str(valid_from_p),str(valid_to_p),
                             memo_p,status_p))
                        conn.commit(); conn.close()
                        st.success(f"PIR {pnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("PIR 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT p.pir_number AS PIR번호, s.name AS 공급사,
                   p.item_name AS 품목, p.unit_price AS 단가,
                   p.currency AS 통화, p.discount_rate AS 할인율,
                   ROUND(p.unit_price*(1-p.discount_rate/100),2) AS 실단가,
                   p.min_order_qty AS 최소발주량, p.lead_time_days AS 납기일수,
                   p.valid_from AS 유효시작, p.valid_to AS 유효종료, p.status AS 상태
            FROM purchase_info_records p
            LEFT JOIN suppliers s ON p.supplier_id=s.id
            ORDER BY p.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("PIR 없음")
        else:
            search_p = st.text_input("🔍 품목/공급사 검색")
            if search_p:
                df = df[df['품목'].str.contains(search_p, na=False) |
                        df['공급사'].str.contains(search_p, na=False)]
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("💡 자재별 최저단가 공급사 조회")
        conn = get_db()
        mats_chk = [dict(r) for r in conn.execute("SELECT material_name FROM materials").fetchall()]
        conn.close()
        if mats_chk:
            chk_item = st.selectbox("자재 선택", [m['material_name'] for m in mats_chk])
            conn = get_db()
            pir_res = pd.read_sql_query("""
                SELECT s.name AS 공급사, p.unit_price AS 단가,
                       p.currency AS 통화, p.discount_rate AS 할인율,
                       ROUND(p.unit_price*(1-p.discount_rate/100),2) AS 실단가,
                       p.lead_time_days AS 납기일수,
                       p.min_order_qty AS 최소발주량, p.valid_to AS 유효기간
                FROM purchase_info_records p
                LEFT JOIN suppliers s ON p.supplier_id=s.id
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

# ── 4. 구매요청 PR ──────────────────────────────────────
with tabs[3]:
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
                   item_name AS 품목, quantity AS 수량,
                   required_date AS 필요일, status AS 상태,
                   approved_by AS 승인자, created_at AS 등록일
            FROM purchase_requests ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("구매요청 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("✅ PR 승인/반려")
        conn = get_db()
        prs = [dict(r) for r in conn.execute(
            "SELECT id, pr_number, item_name FROM purchase_requests WHERE status='승인대기'").fetchall()]
        conn.close()
        if not prs:
            st.info("승인 대기 PR 없음")
        else:
            pr_map = {f"{p['pr_number']} - {p['item_name']}": p['id'] for p in prs}
            sel_pr = st.selectbox("PR 선택", list(pr_map.keys()))
            col_a, col_b, col_c = st.columns(3)
            approver = col_a.text_input("승인자명")
            new_st   = col_b.selectbox("처리", ["승인","반려"])
            if col_c.button("처리 확정", use_container_width=True):
                conn = get_db()
                conn.execute("""UPDATE purchase_requests SET status=?, approved_by=?,
                    approved_at=datetime('now','localtime') WHERE id=?""",
                    (new_st, approver, pr_map[sel_pr]))
                conn.commit(); conn.close()
                st.success(f"{new_st} 처리!"); st.rerun()

# ── 5. 견적 RFQ ──────────────────────────────────────
with tabs[4]:
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
            status_q= st.selectbox("상태", ["검토중","승인","반려","만료"])
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
                   q.item_name AS 품목, q.quantity AS 수량,
                   q.unit_price AS 단가, q.currency AS 통화,
                   ROUND(q.quantity*q.unit_price,0) AS 총액,
                   q.valid_until AS 유효기간, q.status AS 상태
            FROM quotations q LEFT JOIN suppliers s ON q.supplier_id=s.id
            ORDER BY q.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("견적서 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
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

# ── 6. 견적 비교 ──────────────────────────────────────
with tabs[5]:
    st.subheader("🔀 복수 공급사 견적 비교표")
    st.caption("동일 품목에 대한 공급사별 단가, 납기, 조건을 한눈에 비교")
    conn = get_db()
    df_all_q = pd.read_sql_query("""
        SELECT q.item_name AS 품목, s.name AS 공급사,
               q.quantity AS 수량, q.unit_price AS 단가,
               q.currency AS 통화,
               ROUND(q.quantity*q.unit_price,0) AS 총액,
               q.valid_until AS 유효기간, q.status AS 상태,
               q.quote_number AS 견적번호
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
                if row['단가'] == min_price:
                    return ['background-color:#d1fae5;font-weight:bold'] * len(row)
                return [''] * len(row)
            st.dataframe(filtered.style.apply(highlight_best, axis=1),
                         use_container_width=True, hide_index=True)

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
                        # 입고 잔량 초기화
                        po_id = conn.execute("SELECT id FROM purchase_orders WHERE po_number=?", (po_num,)).fetchone()['id']
                        try:
                            conn.execute("""INSERT INTO po_receipt_summary
                                (po_id,ordered_qty,received_qty,remaining_qty)
                                VALUES(?,?,0,?)""",
                                (po_id, q_data['quantity'], q_data['quantity']))
                        except: pass
                        conn.commit(); conn.close()
                        st.success(f"PO {po_num} 생성!"); st.rerun()
                    conn.close()

# ── 7. 계약 ──────────────────────────────────────
with tabs[6]:
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
            status_c   = col_d2.selectbox("상태", ["유효","만료","해지"])
            col_e, col_f = st.columns(2)
            start_c = col_e.date_input("계약시작")
            end_c   = col_f.date_input("계약종료")
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
            def exp_color(row):
                if row['상태'] == '만료': return ['background-color:#fee2e2']*len(row)
                if row['종료일'] <= today: return ['background-color:#fef3c7']*len(row)
                return ['']*len(row)
            st.dataframe(df.style.apply(exp_color, axis=1), use_container_width=True, hide_index=True)
            exp_soon = df[(df['상태']=='유효') & (df['종료일'] <= (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d"))]
            if not exp_soon.empty:
                st.warning(f"⚠️ 30일 내 만료 계약: {len(exp_soon)}건")

# ── 8. 발주서 PO ──────────────────────────────────────
with tabs[7]:
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
        pr5  = {"없음": None}
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

            # PIR 단가 자동 참조
            if sup5 and sup_p2 in sup5:
                conn = get_db()
                pir_auto = conn.execute("""
                    SELECT unit_price, currency, lead_time_days FROM purchase_info_records
                    WHERE supplier_id=? AND status='유효'
                    ORDER BY id DESC LIMIT 1""", (sup5[sup_p2],)).fetchone()
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
                             final_name,qty_p2,price_p2,currency_p2,
                             str(delivery),warehouse,status_p2,note_p2))
                        # 부분입고 추적 초기화
                        po_id = conn.execute("SELECT id FROM purchase_orders WHERE po_number=?", (po_num,)).fetchone()['id']
                        try:
                            conn.execute("""INSERT INTO po_receipt_summary
                                (po_id,ordered_qty,received_qty,remaining_qty)
                                VALUES(?,?,0,?)""", (po_id, qty_p2, qty_p2))
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
                   p.delivery_date AS 납기일, p.status AS 상태,
                   p.created_at AS 등록일
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
            def po_color(row):
                if row['잔량'] > 0 and row['상태'] not in ['취소','입고완료']:
                    return ['background-color:#fef3c7']*len(row)
                return ['']*len(row)
            st.dataframe(filtered.style.apply(po_color, axis=1), use_container_width=True, hide_index=True)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("총 발주금액", f"₩{filtered['총액'].sum():,.0f}")
            col_m2.metric("미입고 잔량 PO", len(filtered[filtered['잔량']>0]))
            col_m3.metric("입고완료", len(filtered[filtered['상태']=='입고완료']))

        st.divider()
        st.subheader("🔄 PO 상태 변경 + 변경이력 기록")
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
                conn.execute("UPDATE purchase_orders SET status=? WHERE id=?",
                             (new_po_st, po_obj['id']))
                try:
                    conn.execute("""INSERT INTO po_change_log
                        (po_id,po_number,changed_field,old_value,new_value,changed_by,change_reason)
                        VALUES(?,?,?,?,?,?,?)""",
                        (po_obj['id'],po_obj['po_number'],'status',
                         po_obj['status'],new_po_st,changer,chg_reason))
                except: pass
                conn.commit(); conn.close()
                st.success("변경 완료!"); st.rerun()

        st.divider()
        st.subheader("📋 PO 변경이력")
        conn = get_db()
        df_chg = pd.read_sql_query("""
            SELECT po_number AS PO번호, changed_field AS 변경항목,
                   old_value AS 이전값, new_value AS 변경값,
                   changed_by AS 변경자, change_reason AS 사유,
                   changed_at AS 변경일시
            FROM po_change_log ORDER BY id DESC LIMIT 30""", conn)
        conn.close()
        if df_chg.empty:
            st.info("변경이력 없음")
        else:
            st.dataframe(df_chg, use_container_width=True, hide_index=True)

# ── 9. 입고 GR ──────────────────────────────────────
with tabs[8]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("입고(GR) 등록")
        conn = get_db()
        pos_gr = [dict(r) for r in conn.execute("""
            SELECT p.id, p.po_number, p.item_name, p.quantity,
                   COALESCE(r.remaining_qty, p.quantity) AS remaining
            FROM purchase_orders p
            LEFT JOIN po_receipt_summary r ON p.id=r.po_id
            WHERE p.status IN ('발주완료','납품중')
            AND COALESCE(r.remaining_qty, p.quantity) > 0""").fetchall()]
        conn.close()
        po_gr_opts = {f"{p['po_number']} - {p['item_name']} (잔량:{p['remaining']})":
                      (p['id'], p['item_name'], p['quantity'], p['remaining']) for p in pos_gr}

        with st.form("gr_form", clear_on_submit=True):
            po_sel_gr = st.selectbox("발주서(PO) *", list(po_gr_opts.keys()) if po_gr_opts else ["발주 PO 없음"])
            if po_gr_opts and po_sel_gr in po_gr_opts:
                po_id_val, item_auto, ord_qty, remaining = po_gr_opts[po_sel_gr]
            else:
                po_id_val, item_auto, ord_qty, remaining = None, "", 0, 0

            item_gr = st.text_input("품목명", value=item_auto)
            col_a, col_b, col_c = st.columns(3)
            col_a.number_input("발주수량", value=ord_qty, disabled=True)
            recv_qty = col_b.number_input("입고수량 *", min_value=0, value=int(remaining))
            rej_qty  = col_c.number_input("불량/반품수량", min_value=0, value=0)
            col_d, col_e = st.columns(2)
            warehouse_gr = col_d.text_input("입고창고")
            bin_gr    = col_e.text_input("Bin 위치")
            receiver  = st.text_input("입고담당자")
            note_gr   = st.text_area("비고", height=50)

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
                            (gr_num,po_id_val,item_gr,ord_qty,recv_qty,
                             rej_qty,warehouse_gr,bin_gr,receiver,note_gr))
                        # 부분입고 잔량 업데이트
                        conn.execute("""INSERT INTO po_receipt_summary(po_id,ordered_qty,received_qty,remaining_qty,last_gr_date)
                            VALUES(?,?,?,?,date('now'))
                            ON CONFLICT(po_id) DO UPDATE SET
                            received_qty=received_qty+?,
                            remaining_qty=MAX(0,remaining_qty-?),
                            last_gr_date=date('now'),
                            updated_at=datetime('now','localtime')""",
                            (po_id_val,ord_qty,recv_qty,ord_qty-recv_qty,recv_qty,recv_qty))
                        # 잔량 0이면 PO 완료
                        remaining_new = remaining - recv_qty
                        if remaining_new <= 0:
                            conn.execute("UPDATE purchase_orders SET status='입고완료' WHERE id=?", (po_id_val,))
                        else:
                            conn.execute("UPDATE purchase_orders SET status='납품중' WHERE id=?", (po_id_val,))
                        # 재고 자동 반영
                        net_qty = recv_qty - rej_qty
                        if net_qty > 0:
                            conn.execute("""INSERT INTO inventory(item_code,item_name,warehouse,stock_qty,system_qty)
                                VALUES(?,?,?,?,?)
                                ON CONFLICT(item_code) DO UPDATE SET
                                stock_qty=stock_qty+excluded.stock_qty,
                                system_qty=system_qty+excluded.system_qty,
                                updated_at=datetime('now','localtime')""",
                                (gr_num, item_gr, warehouse_gr, net_qty, net_qty))
                        conn.commit(); conn.close()
                        msg = "입고완료" if remaining_new <= 0 else f"부분입고 (잔량 {remaining_new}개)"
                        st.success(f"GR {gr_num} 등록! → {msg}, 재고 자동 반영"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("입고 이력")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT g.gr_number AS GR번호, p.po_number AS 발주번호,
                   g.item_name AS 품목, g.ordered_qty AS 발주수량,
                   g.received_qty AS 입고수량, g.rejected_qty AS 불량수량,
                   g.warehouse AS 창고, g.receiver AS 담당자,
                   g.created_at AS 입고일시
            FROM goods_receipts g LEFT JOIN purchase_orders p ON g.po_id=p.id
            ORDER BY g.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("입고 이력 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("총 입고건수", len(df))
            col_m2.metric("총 입고수량", int(df['입고수량'].sum()))

# ── 10. 송장검증 ──────────────────────────────────────
with tabs[9]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("송장검증 (3-Way Match)")
        st.caption("PO금액 ↔ GR금액 ↔ 공급사 인보이스 금액 대사")
        conn = get_db()
        pos_iv = [dict(r) for r in conn.execute("""
            SELECT p.id, p.po_number, p.item_name, p.quantity, p.unit_price, s.name
            FROM purchase_orders p LEFT JOIN suppliers s ON p.supplier_id=s.id""").fetchall()]
        grs_iv = [dict(r) for r in conn.execute(
            "SELECT id, gr_number, item_name, received_qty FROM goods_receipts").fetchall()]
        conn.close()
        po_iv_opts = {f"{p['po_number']} - {p['item_name']}": p for p in pos_iv}
        gr_iv_opts = {f"{g['gr_number']} - {g['item_name']}": g for g in grs_iv}

        with st.form("iv_form", clear_on_submit=True):
            po_iv_sel = st.selectbox("발주서(PO) *", list(po_iv_opts.keys()) if po_iv_opts else ["없음"])
            gr_iv_sel = st.selectbox("입고(GR) *", list(gr_iv_opts.keys()) if gr_iv_opts else ["없음"])

            po_amt, sup_name_iv, gr_amt = 0, "", 0
            if po_iv_opts and po_iv_sel in po_iv_opts:
                po_data = po_iv_opts[po_iv_sel]
                po_amt  = po_data['quantity'] * po_data['unit_price']
                sup_name_iv = po_data['name'] or ""
                if gr_iv_opts and gr_iv_sel in gr_iv_opts:
                    gr_data = gr_iv_opts[gr_iv_sel]
                    gr_amt  = gr_data['received_qty'] * po_data['unit_price']

            st.info(f"PO 금액: ₩{po_amt:,.0f} | GR 금액: ₩{gr_amt:,.0f}")
            supplier_iv = st.text_input("공급사명", value=sup_name_iv)
            inv_ref     = st.text_input("공급사 인보이스 번호")
            col_a, col_b = st.columns(2)
            inv_amt = col_a.number_input("인보이스 금액 *", min_value=0.0, format="%.0f")
            tax_iv  = col_b.number_input("세액", min_value=0.0, format="%.0f")

            if inv_amt > 0:
                diff = abs(inv_amt - po_amt)
                tolerance = po_amt * 0.01
                auto_match = "일치" if diff <= tolerance else "불일치"
                color = "success" if auto_match == "일치" else "warning"
                if auto_match == "일치":
                    st.success(f"자동 판단: **{auto_match}** (차이: ₩{diff:,.0f})")
                else:
                    st.warning(f"자동 판단: **{auto_match}** (차이: ₩{diff:,.0f})")

            match_status = st.selectbox("최종 처리", ["검증중","일치-승인","불일치-보류","불일치-반려"])
            note_iv = st.text_area("비고", height=50)

            if st.form_submit_button("✅ 등록", use_container_width=True):
                if inv_amt == 0:
                    st.error("인보이스 금액 필수")
                else:
                    try:
                        iv_num = gen_number("IV")
                        po_id_iv = po_iv_opts[po_iv_sel]['id'] if po_iv_opts else None
                        gr_id_iv = gr_iv_opts[gr_iv_sel]['id'] if gr_iv_opts else None
                        conn = get_db()
                        conn.execute("""INSERT INTO invoice_verifications
                            (iv_number,po_id,gr_id,supplier,invoice_ref,po_amount,
                             gr_amount,invoice_amount,tax_amount,match_status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (iv_num,po_id_iv,gr_id_iv,supplier_iv,inv_ref,
                             po_amt,gr_amt,inv_amt,tax_iv,match_status,note_iv))
                        conn.commit(); conn.close()
                        st.success(f"송장검증 {iv_num} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("송장검증 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT iv_number AS IV번호, supplier AS 공급사,
                   invoice_ref AS 인보이스번호,
                   po_amount AS PO금액, gr_amount AS GR금액,
                   invoice_amount AS 인보이스금액,
                   (invoice_amount-po_amount) AS 차이,
                   match_status AS 결과, created_at AS 등록일
            FROM invoice_verifications ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("검증 내역 없음")
        else:
            def color_match(val):
                if '일치' in str(val) and '불일치' not in str(val): return "color:green;font-weight:bold"
                if '불일치' in str(val): return "color:red;font-weight:bold"
                return ""
            st.dataframe(df.style.map(color_match, subset=['결과']),
                         use_container_width=True, hide_index=True)

# ── 11. 세금계산서 ──────────────────────────────────────
with tabs[10]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("🧾 매입 세금계산서 등록")
        st.caption("송장검증 완료 후 공급사로부터 수취한 세금계산서")
        conn = get_db()
        ivs = [dict(r) for r in conn.execute("""
            SELECT iv.id, iv.iv_number, iv.supplier, iv.invoice_amount, iv.tax_amount,
                   iv.po_id, iv.gr_id
            FROM invoice_verifications iv
            WHERE iv.match_status LIKE '%승인%'""").fetchall()]
        sups_ti = [dict(r) for r in conn.execute("SELECT id, name, payment_terms FROM suppliers").fetchall()]
        conn.close()
        iv_opts  = {"직접입력": None}
        iv_opts.update({f"{i['iv_number']} - {i['supplier']}": i for i in ivs})
        sup_ti_map = {s['name']: s for s in sups_ti}

        with st.form("tax_inv_form", clear_on_submit=True):
            iv_sel = st.selectbox("연결 송장검증(IV)", list(iv_opts.keys()))
            iv_data = iv_opts.get(iv_sel)

            supplier_ti = st.text_input("공급사명 *",
                value=iv_data['supplier'] if iv_data else "")
            col_a, col_b = st.columns(2)
            supply_amt = col_a.number_input("공급가액 *", min_value=0.0, format="%.0f",
                value=float(iv_data['invoice_amount']) if iv_data else 0.0)
            tax_rate_ti = col_b.selectbox("세율(%)", [10, 0])
            tax_amt_ti = supply_amt * tax_rate_ti / 100
            total_ti   = supply_amt + tax_amt_ti
            st.info(f"세액: ₩{tax_amt_ti:,.0f} | 합계: ₩{total_ti:,.0f}")

            col_c, col_d = st.columns(2)
            issue_dt = col_c.date_input("발행일")
            # 결제조건으로 기한 자동계산
            pay_days = 30
            if supplier_ti in sup_ti_map:
                pt = sup_ti_map[supplier_ti]['payment_terms'] or "30일"
                pay_days = int(''.join(filter(str.isdigit, pt)) or 30)
            due_dt = col_d.date_input("결제기한",
                value=datetime.now().date() + timedelta(days=pay_days))
            note_ti = st.text_input("비고")

            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not supplier_ti or supply_amt == 0:
                    st.error("공급사, 금액 필수")
                else:
                    try:
                        tnum = gen_number("TI")
                        conn = get_db()
                        conn.execute("""INSERT INTO purchase_tax_invoices
                            (tax_inv_number,iv_id,po_id,gr_id,supplier,
                             supply_amount,tax_amount,total_amount,
                             issue_date,due_date,payment_status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (tnum,
                             iv_data['id'] if iv_data else None,
                             iv_data['po_id'] if iv_data else None,
                             iv_data['gr_id'] if iv_data else None,
                             supplier_ti, supply_amt, tax_amt_ti, total_ti,
                             str(issue_dt), str(due_dt), '미결', note_ti))
                        # 지급 스케줄 자동 생성
                        snum = gen_number("PAY")
                        ti_id = conn.execute("SELECT id FROM purchase_tax_invoices WHERE tax_inv_number=?", (tnum,)).fetchone()['id']
                        conn.execute("""INSERT INTO payment_schedule
                            (schedule_number,tax_inv_id,supplier,payment_amount,
                             currency,due_date,payment_method,status)
                            VALUES(?,?,?,?,'KRW',?,?,?)""",
                            (snum, ti_id, supplier_ti, total_ti, str(due_dt), '계좌이체', '예정'))
                        conn.commit(); conn.close()
                        st.success(f"세금계산서 {tnum} 등록! 지급 스케줄 자동 생성"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("세금계산서 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT tax_inv_number AS 계산서번호, supplier AS 공급사,
                   supply_amount AS 공급가액, tax_amount AS 세액,
                   total_amount AS 합계, issue_date AS 발행일,
                   due_date AS 결제기한, payment_status AS 결제상태
            FROM purchase_tax_invoices ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("세금계산서 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            unpaid = df[df['결제상태']=='미결']['합계'].sum()
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("미결 합계", f"₩{unpaid:,.0f}", delta_color="inverse")
            col_m2.metric("총 건수", len(df))

# ── 12. 지급 관리 ──────────────────────────────────────
with tabs[11]:
    st.subheader("💰 지급 스케줄 관리")
    conn = get_db()
    df_pay = pd.read_sql_query("""
        SELECT p.schedule_number AS 스케줄번호, p.supplier AS 공급사,
               p.payment_amount AS 지급금액, p.due_date AS 지급기한,
               p.payment_method AS 지급방법, p.status AS 상태,
               p.paid_at AS 지급일시
        FROM payment_schedule p ORDER BY p.due_date, p.id DESC""", conn)
    conn.close()

    if df_pay.empty:
        st.info("지급 스케줄 없음 (세금계산서 등록 시 자동 생성됩니다)")
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        overdue = df_pay[(df_pay['상태']=='예정') & (df_pay['지급기한'] < today_str)]
        due_soon = df_pay[(df_pay['상태']=='예정') &
                          (df_pay['지급기한'] >= today_str) &
                          (df_pay['지급기한'] <= (datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d"))]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 지급예정", f"₩{df_pay[df_pay['상태']=='예정']['지급금액'].sum():,.0f}")
        col2.metric("🔴 연체", f"{len(overdue)}건", delta_color="inverse")
        col3.metric("🟡 7일 내 도래", f"{len(due_soon)}건")
        col4.metric("✅ 지급완료", len(df_pay[df_pay['상태']=='완료']))

        st.divider()
        tab_a, tab_b = st.tabs(["📋 전체 스케줄", "⚠️ 긴급 처리"])
        with tab_a:
            def pay_hl(row):
                if row['상태'] == '완료': return ['background-color:#d1fae5']*len(row)
                if row['지급기한'] < today_str and row['상태']=='예정': return ['background-color:#fee2e2']*len(row)
                if row['지급기한'] <= (datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d") and row['상태']=='예정':
                    return ['background-color:#fef3c7']*len(row)
                return ['']*len(row)
            st.dataframe(df_pay.style.apply(pay_hl, axis=1), use_container_width=True, hide_index=True)

        with tab_b:
            conn = get_db()
            pending = [dict(r) for r in conn.execute("""
                SELECT id, schedule_number, supplier, payment_amount, due_date
                FROM payment_schedule WHERE status='예정'
                ORDER BY due_date""").fetchall()]
            conn.close()
            if not pending:
                st.success("✅ 처리할 지급 없음")
            else:
                pay_map = {f"{p['schedule_number']} - {p['supplier']} ₩{p['payment_amount']:,.0f} ({p['due_date']})": p['id']
                           for p in pending}
                sel_pay = st.selectbox("지급 처리할 항목", list(pay_map.keys()))
                col_a2, col_b2 = st.columns(2)
                pay_method = col_a2.selectbox("지급방법", ["계좌이체","수표","어음","현금"])
                if col_b2.button("💳 지급 완료 처리", use_container_width=True):
                    conn = get_db()
                    pay_id = pay_map[sel_pay]
                    conn.execute("""UPDATE payment_schedule SET status='완료',
                        paid_at=datetime('now','localtime'), payment_method=? WHERE id=?""",
                        (pay_method, pay_id))
                    # 세금계산서 결제상태도 업데이트
                    ti_id = conn.execute("SELECT tax_inv_id FROM payment_schedule WHERE id=?", (pay_id,)).fetchone()
                    if ti_id and ti_id[0]:
                        conn.execute("UPDATE purchase_tax_invoices SET payment_status='완료', paid_at=datetime('now','localtime') WHERE id=?",
                                     (ti_id[0],))
                    conn.commit(); conn.close()
                    st.success("지급 완료 처리!"); st.rerun()

# ── 13. 공급사 평가 ──────────────────────────────────────
with tabs[12]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("공급사 평가 등록")
        st.caption("납기·품질·가격·서비스 각 25점 만점 (100점 총점)")
        conn = get_db()
        sups_ev = [dict(r) for r in conn.execute("SELECT id, name FROM suppliers").fetchall()]
        conn.close()
        sup_ev = {s['name']: s['id'] for s in sups_ev}
        with st.form("eval_form", clear_on_submit=True):
            sup_e    = st.selectbox("공급사 *", list(sup_ev.keys()) if sup_ev else ["없음"])
            col_a, col_b = st.columns(2)
            period   = col_a.text_input("평가기간 (예: 2024-Q1)")
            evaluator= col_b.text_input("평가자")
            st.markdown("**평가 항목 (각 0~25점)**")
            col_1, col_2, col_3, col_4 = st.columns(4)
            d_score = col_1.number_input("납기준수", 0.0, 25.0, 20.0, 0.5)
            q_score = col_2.number_input("품질", 0.0, 25.0, 20.0, 0.5)
            p_score = col_3.number_input("가격", 0.0, 25.0, 20.0, 0.5)
            s_score = col_4.number_input("서비스", 0.0, 25.0, 20.0, 0.5)
            total   = d_score + q_score + p_score + s_score
            grade   = "A (우수)" if total>=90 else "B (양호)" if total>=75 else "C (보통)" if total>=60 else "D (개선필요)"
            st.info(f"총점: **{total}점** | 등급: **{grade}**")
            note_e = st.text_area("종합의견", height=60)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not sup_ev or not period:
                    st.error("공급사, 평가기간 필수")
                else:
                    try:
                        enum = gen_number("EV")
                        conn = get_db()
                        conn.execute("""INSERT INTO supplier_evaluations
                            (eval_number,supplier_id,eval_period,delivery_score,quality_score,
                             price_score,service_score,total_score,grade,evaluator,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (enum,sup_ev.get(sup_e),period,d_score,q_score,
                             p_score,s_score,total,grade,evaluator,note_e))
                        conn.commit(); conn.close()
                        st.success(f"평가 {enum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("공급사 평가 현황")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT e.eval_number AS 평가번호, s.name AS 공급사,
                   e.eval_period AS 기간, e.delivery_score AS 납기,
                   e.quality_score AS 품질, e.price_score AS 가격,
                   e.service_score AS 서비스, e.total_score AS 총점,
                   e.grade AS 등급, e.evaluator AS 평가자
            FROM supplier_evaluations e LEFT JOIN suppliers s ON e.supplier_id=s.id
            ORDER BY e.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("평가 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.subheader("📊 공급사별 평균 총점")
            avg_df = df.groupby('공급사')['총점'].mean().reset_index().sort_values('총점', ascending=False)
            st.bar_chart(avg_df.set_index('공급사'))

# ── 14. 구매 KPI ──────────────────────────────────────
with tabs[13]:
    st.subheader("📊 구매 KPI 대시보드")
    conn = get_db()
    df_po  = pd.read_sql_query("""
        SELECT p.po_number, s.name AS supplier, p.item_name,
               p.quantity, p.unit_price, p.currency,
               ROUND(p.quantity*p.unit_price,0) AS total_amt,
               p.delivery_date, p.status, p.created_at
        FROM purchase_orders p LEFT JOIN suppliers s ON p.supplier_id=s.id""", conn)
    df_gr  = pd.read_sql_query("SELECT po_id, received_qty, created_at FROM goods_receipts", conn)
    df_iv  = pd.read_sql_query("SELECT match_status FROM invoice_verifications", conn)
    df_ev  = pd.read_sql_query("""
        SELECT s.name AS supplier, e.total_score
        FROM supplier_evaluations e LEFT JOIN suppliers s ON e.supplier_id=s.id""", conn)
    df_pay_kpi = pd.read_sql_query("""
        SELECT payment_amount, status, due_date FROM payment_schedule""", conn)
    conn.close()

    # KPI 계산
    total_po_amt  = df_po['total_amt'].sum() if not df_po.empty else 0
    po_cnt        = len(df_po) if not df_po.empty else 0
    gr_cnt        = len(df_gr) if not df_gr.empty else 0
    match_ok      = len(df_iv[df_iv['match_status'].str.contains('승인', na=False)]) if not df_iv.empty else 0
    avg_score     = df_ev['total_score'].mean() if not df_ev.empty else 0
    pay_overdue   = 0
    if not df_pay_kpi.empty:
        today_str = datetime.now().strftime("%Y-%m-%d")
        pay_overdue = len(df_pay_kpi[(df_pay_kpi['status']=='예정') & (df_pay_kpi['due_date']<today_str)])

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("총 발주금액", f"₩{total_po_amt:,.0f}")
    col2.metric("발주건수", f"{po_cnt}건")
    col3.metric("입고건수", f"{gr_cnt}건")
    col4.metric("송장검증 승인", f"{match_ok}건")
    col5.metric("공급사 평균점수", f"{avg_score:.1f}점")
    col6.metric("🔴 지급연체", f"{pay_overdue}건", delta_color="inverse")

    st.divider()
    if not df_po.empty:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("공급사별 발주금액")
            sup_amt = df_po.groupby('supplier')['total_amt'].sum().reset_index().sort_values('total_amt', ascending=False)
            st.bar_chart(sup_amt.set_index('supplier'))

        with col_r:
            st.subheader("품목별 발주금액 TOP 10")
            item_amt = df_po.groupby('item_name')['total_amt'].sum().reset_index().sort_values('total_amt', ascending=False).head(10)
            st.bar_chart(item_amt.set_index('item_name'))

        st.subheader("월별 발주금액 추이")
        df_po['월'] = pd.to_datetime(df_po['created_at']).dt.strftime('%Y-%m')
        monthly = df_po.groupby('월')['total_amt'].sum().reset_index()
        st.line_chart(monthly.set_index('월'))

        st.subheader("PO 상태 현황")
        status_cnt = df_po['status'].value_counts().reset_index()
        status_cnt.columns = ['상태','건수']
        st.dataframe(status_cnt, use_container_width=True, hide_index=True)
