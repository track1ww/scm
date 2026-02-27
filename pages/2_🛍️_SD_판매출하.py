import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number

st.title("🛍️ SD – Sales & Distribution (판매/출하/청구)")

tabs = st.tabs(["👥 고객 마스터", "💬 고객 견적(SD)", "📋 판매주문(SO)", "🚚 출하/피킹", "🧾 청구서", "↩️ 반품", "📊 수익성 분석"])

# ── 1. 고객 마스터 ──────────────────────────────────────
with tabs[0]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("고객 등록/수정")
        with st.form("cust_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            cust_code = col_a.text_input("고객코드 *")
            cust_name = col_b.text_input("고객명 *")
            col_c, col_d = st.columns(2)
            contact   = col_c.text_input("담당자")
            phone     = col_d.text_input("전화번호")
            email     = st.text_input("이메일")
            address   = st.text_area("주소", height=60)
            col_e, col_f = st.columns(2)
            cust_grp  = col_e.selectbox("고객군", ["일반","VIP","도매","소매","B2B","해외"])
            status    = col_f.selectbox("상태", ["활성","휴면","거래중지"])
            credit    = st.number_input("여신한도(₩)", min_value=0.0, format="%.0f")
            if st.form_submit_button("✅ 저장", use_container_width=True):
                if not cust_code or not cust_name:
                    st.error("고객코드, 고객명 필수")
                else:
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO customers
                            (customer_code,customer_name,contact,phone,email,address,customer_group,credit_limit,status)
                            VALUES(?,?,?,?,?,?,?,?,?)
                            ON CONFLICT(customer_code) DO UPDATE SET
                            customer_name=excluded.customer_name, contact=excluded.contact,
                            phone=excluded.phone, email=excluded.email, address=excluded.address,
                            customer_group=excluded.customer_group, credit_limit=excluded.credit_limit,
                            status=excluded.status""",
                            (cust_code,cust_name,contact,phone,email,address,cust_grp,credit,status))
                        conn.commit(); conn.close()
                        st.success("고객 저장 완료!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("고객 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT customer_code AS 고객코드, customer_name AS 고객명,
                   contact AS 담당자, phone AS 전화, email AS 이메일,
                   customer_group AS 고객군, credit_limit AS 여신한도,
                   credit_used AS 여신사용, status AS 상태
            FROM customers ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("고객 없음")
        else:
            search = st.text_input("🔍 고객 검색")
            if search:
                df = df[df['고객명'].str.contains(search, na=False)]
            def credit_highlight(row):
                if row['여신한도'] > 0 and row['여신사용'] >= row['여신한도']:
                    return ['background-color:#fee2e2'] * len(row)
                return [''] * len(row)
            st.dataframe(df.style.apply(credit_highlight, axis=1), use_container_width=True, hide_index=True)
            st.caption("🔴 빨간 행 = 여신한도 초과")

# ── 2. 고객 견적 (SD) ──────────────────────────────────────
with tabs[1]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("고객 견적 등록")
        conn = get_db()
        custs = conn.execute("SELECT id, customer_code, customer_name FROM customers WHERE status='활성'").fetchall()
        conn.close()
        cust_opts = {f"{c['customer_code']} - {c['customer_name']}": c['id'] for c in custs}

        with st.form("sdq_form", clear_on_submit=True):
            cust_sel  = st.selectbox("고객 *", list(cust_opts.keys()) if cust_opts else ["없음"])
            item_name = st.text_input("품목명 *")
            col_a, col_b, col_c = st.columns(3)
            qty       = col_a.number_input("수량", min_value=1, value=1)
            unit_price= col_b.number_input("단가", min_value=0.0, format="%.2f")
            disc_rate = col_c.number_input("할인율(%)", min_value=0.0, max_value=100.0, value=0.0, format="%.1f")
            final_price = unit_price * qty * (1 - disc_rate/100)
            st.info(f"할인 후 합계: ₩{final_price:,.0f}")
            valid_until = st.date_input("유효기간")
            status_q  = st.selectbox("상태", ["검토중","승인","반려","만료"])
            note_q    = st.text_area("비고", height=50)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_name or not cust_opts:
                    st.error("고객, 품목명 필수")
                else:
                    try:
                        qnum = gen_number("SDQ")
                        conn = get_db()
                        conn.execute("""INSERT INTO sd_quotations
                            (sd_quote_number,customer_id,item_name,quantity,unit_price,discount_rate,final_price,valid_until,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (qnum,cust_opts.get(cust_sel),item_name,qty,unit_price,disc_rate,final_price,str(valid_until),status_q,note_q))
                        conn.commit(); conn.close()
                        st.success(f"견적 {qnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("고객 견적 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT q.sd_quote_number AS 견적번호, c.customer_name AS 고객,
                   q.item_name AS 품목, q.quantity AS 수량,
                   q.unit_price AS 단가, q.discount_rate AS 할인율,
                   q.final_price AS 할인후금액,
                   q.valid_until AS 유효기간, q.status AS 상태
            FROM sd_quotations q LEFT JOIN customers c ON q.customer_id=c.id
            ORDER BY q.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("견적 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("견적 → SO 전환")
        conn = get_db()
        approved_q = conn.execute("SELECT id, sd_quote_number, item_name FROM sd_quotations WHERE status='승인'").fetchall()
        conn.close()
        if not approved_q:
            st.info("승인된 견적 없음")
        else:
            q_map = {f"{q['sd_quote_number']} - {q['item_name']}": q['id'] for q in approved_q}
            sel_q2so = st.selectbox("전환할 견적 선택", list(q_map.keys()))
            if st.button("🔄 판매주문(SO)으로 전환", use_container_width=True):
                conn = get_db()
                q_data = conn.execute("SELECT * FROM sd_quotations WHERE id=?", (q_map[sel_q2so],)).fetchone()
                if q_data:
                    so_num = gen_number("SO")
                    cust_info = conn.execute("SELECT customer_name FROM customers WHERE id=?", (q_data['customer_id'],)).fetchone()
                    conn.execute("""INSERT INTO sales_orders
                        (order_number,customer_id,sd_quote_id,customer_name,item_name,quantity,unit_price,discount_rate,status)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (so_num,q_data['customer_id'],q_data['id'],
                         cust_info['customer_name'] if cust_info else "",
                         q_data['item_name'],q_data['quantity'],q_data['unit_price'],
                         q_data['discount_rate'],'주문접수'))
                    conn.execute("UPDATE sd_quotations SET status='만료' WHERE id=?", (q_data['id'],))
                    conn.commit(); conn.close()
                    st.success(f"SO {so_num} 생성 완료!"); st.rerun()

# ── 3. 판매주문 SO ──────────────────────────────────────
with tabs[2]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("판매주문(SO) 등록")
        conn = get_db()
        custs2 = conn.execute("SELECT id, customer_code, customer_name, credit_limit, credit_used FROM customers WHERE status='활성'").fetchall()
        conn.close()
        cust2_opts = {f"{c['customer_code']} - {c['customer_name']}": c for c in custs2}

        with st.form("so_form", clear_on_submit=True):
            cust2_sel = st.selectbox("고객 *", list(cust2_opts.keys()) if cust2_opts else ["없음"])
            platform  = st.selectbox("판매채널", ["쿠팡","네이버","11번가","G마켓","자사몰","B2B직거래","기타"])
            item_name = st.text_input("품목명 *")
            col_a, col_b, col_c = st.columns(3)
            qty       = col_a.number_input("수량", min_value=1, value=1)
            unit_price= col_b.number_input("단가", min_value=0.0, format="%.2f")
            disc_rate = col_c.number_input("할인율(%)", min_value=0.0, max_value=100.0, value=0.0, format="%.1f")
            order_amt = qty * unit_price * (1 - disc_rate/100)
            st.info(f"주문금액: ₩{order_amt:,.0f}")

            # 여신 체크
            if cust2_opts and cust2_sel in cust2_opts:
                cust_data = cust2_opts[cust2_sel]
                remaining = cust_data['credit_limit'] - cust_data['credit_used']
                if cust_data['credit_limit'] > 0:
                    if order_amt > remaining:
                        st.warning(f"⚠️ 여신한도 초과! 잔여여신: ₩{remaining:,.0f}")
                    else:
                        st.success(f"✅ 여신 OK (잔여: ₩{remaining:,.0f})")

            col_d, col_e = st.columns(2)
            req_del   = col_d.date_input("납기요청일")
            conf_del  = col_e.date_input("납기확정일")

            # 재고(ATP) 체크
            conn = get_db()
            inv_check = conn.execute("SELECT SUM(stock_qty) FROM inventory WHERE item_name LIKE ?", (f"%{item_name}%",)).fetchone()[0] or 0
            conn.close()
            if item_name:
                if inv_check >= qty:
                    st.success(f"✅ ATP 확인: 재고 {inv_check}개 (요청 {qty}개 출하 가능)")
                else:
                    st.warning(f"⚠️ 재고 부족: 현재고 {inv_check}개 (요청 {qty}개)")

            status    = st.selectbox("상태", ["주문접수","출하지시","배송중","배송완료","취소"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_name or not cust2_opts:
                    st.error("고객, 품목명 필수")
                else:
                    cust_obj = cust2_opts.get(cust2_sel)
                    try:
                        onum = gen_number("SO")
                        conn = get_db()
                        conn.execute("""INSERT INTO sales_orders
                            (order_number,customer_id,platform,customer_name,item_name,quantity,
                             unit_price,discount_rate,requested_delivery,confirmed_delivery,
                             atp_checked,credit_checked,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (onum,cust_obj['id'],platform,cust_obj['customer_name'],
                             item_name,qty,unit_price,disc_rate,
                             str(req_del),str(conf_del),
                             1 if inv_check >= qty else 0,
                             1 if cust_obj['credit_limit']==0 or order_amt<=remaining else 0,
                             status))
                        # 여신 사용액 업데이트
                        conn.execute("UPDATE customers SET credit_used=credit_used+? WHERE id=?",
                                     (order_amt, cust_obj['id']))
                        conn.commit(); conn.close()
                        st.success(f"주문 {onum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("판매주문 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT order_number AS 주문번호, platform AS 채널,
                   customer_name AS 고객, item_name AS 품목,
                   quantity AS 수량, unit_price AS 단가,
                   discount_rate AS 할인율,
                   ROUND(quantity*unit_price*(1-discount_rate/100),0) AS 주문금액,
                   CASE atp_checked WHEN 1 THEN '✅' ELSE '⚠️' END AS ATP,
                   CASE credit_checked WHEN 1 THEN '✅' ELSE '⚠️' END AS 여신,
                   status AS 상태, ordered_at AS 주문일
            FROM sales_orders ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("주문 없음")
        else:
            col_f1, col_f2 = st.columns(2)
            p_filter = col_f1.multiselect("채널", df['채널'].unique().tolist(), default=df['채널'].unique().tolist())
            s_filter = col_f2.multiselect("상태", df['상태'].unique().tolist(), default=df['상태'].unique().tolist())
            filtered = df[df['채널'].isin(p_filter) & df['상태'].isin(s_filter)]
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("주문건수", f"{len(filtered)}건")
            col_m2.metric("총 주문금액", f"₩{filtered['주문금액'].sum():,.0f}")
            col_m3.metric("배송완료", len(filtered[filtered['상태']=='배송완료']))

        st.divider()
        st.subheader("SO 상태 변경")
        conn = get_db()
        sos = conn.execute("SELECT id, order_number, item_name, status FROM sales_orders WHERE status NOT IN ('배송완료','취소')").fetchall()
        conn.close()
        if sos:
            so_map = {f"{o['order_number']} - {o['item_name']} ({o['status']})": o['id'] for o in sos}
            sel_so = st.selectbox("주문 선택", list(so_map.keys()))
            new_so_st = st.selectbox("변경 상태", ["주문접수","출하지시","배송중","배송완료","취소"])
            if st.button("🔄 상태 변경", use_container_width=True, key="so_status"):
                conn = get_db()
                conn.execute("UPDATE sales_orders SET status=? WHERE id=?", (new_so_st, so_map[sel_so]))
                conn.commit(); conn.close()
                st.success("변경 완료!"); st.rerun()

# ── 4. 출하 / 피킹 ──────────────────────────────────────
with tabs[3]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("출하 등록 (피킹 → 포장 → 출하)")
        conn = get_db()
        sos_del = conn.execute("SELECT id, order_number, item_name, quantity FROM sales_orders WHERE status='출하지시'").fetchall()
        conn.close()
        so_del_opts = {f"{o['order_number']} - {o['item_name']} (주문:{o['quantity']})": (o['id'], o['item_name'], o['quantity']) for o in sos_del}

        with st.form("del_form", clear_on_submit=True):
            so_del_sel = st.selectbox("판매주문(SO) *", list(so_del_opts.keys()) if so_del_opts else ["출하지시 주문 없음"])
            if so_del_opts and so_del_sel in so_del_opts:
                so_id_val, item_auto, so_qty = so_del_opts[so_del_sel]
            else:
                so_id_val, item_auto, so_qty = None, "", 0

            item_del  = st.text_input("품목명", value=item_auto)
            col_a, col_b, col_c = st.columns(3)
            del_qty   = col_a.number_input("출하수량", min_value=0, value=so_qty)
            pick_qty  = col_b.number_input("피킹수량", min_value=0, value=so_qty)
            pack_qty  = col_c.number_input("포장수량", min_value=0, value=so_qty)
            col_d, col_e = st.columns(2)
            carrier   = col_d.text_input("배송사")
            tracking  = col_e.text_input("운송장번호")
            del_date  = st.date_input("출하일")
            status    = st.selectbox("상태", ["출하준비","피킹완료","포장완료","출하완료","배송중","배송완료"])
            if st.form_submit_button("✅ 출하 등록", use_container_width=True):
                if not so_del_opts:
                    st.error("출하지시 주문 없음")
                else:
                    try:
                        dnum = gen_number("DEL")
                        conn = get_db()
                        conn.execute("""INSERT INTO deliveries
                            (delivery_number,order_id,item_name,delivery_qty,pick_qty,pack_qty,
                             delivery_date,carrier,tracking_number,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (dnum,so_id_val,item_del,del_qty,pick_qty,pack_qty,
                             str(del_date),carrier,tracking,status))
                        # SO 상태 업데이트
                        conn.execute("UPDATE sales_orders SET status=? WHERE id=?",
                                     ('배송중' if status in ['출하완료','배송중'] else status, so_id_val))
                        # 재고 차감
                        conn.execute("""UPDATE inventory SET stock_qty=stock_qty-?, system_qty=system_qty-?,
                            updated_at=datetime('now','localtime') WHERE item_name LIKE ?""",
                            (del_qty, del_qty, f"%{item_del}%"))
                        conn.commit(); conn.close()
                        st.success(f"출하 {dnum} 등록! 재고 자동 차감"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("출하 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT d.delivery_number AS 출하번호, o.order_number AS 주문번호,
                   d.item_name AS 품목, d.delivery_qty AS 출하수량,
                   d.pick_qty AS 피킹, d.pack_qty AS 포장,
                   d.delivery_date AS 출하일, d.carrier AS 배송사,
                   d.tracking_number AS 운송장, d.status AS 상태
            FROM deliveries d LEFT JOIN sales_orders o ON d.order_id=o.id
            ORDER BY d.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("출하 데이터 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.metric("총 출하건수", len(df))

        st.divider()
        st.subheader("출하 상태 변경")
        conn = get_db()
        dels = conn.execute("SELECT id, delivery_number, item_name, status FROM deliveries WHERE status NOT IN ('배송완료')").fetchall()
        conn.close()
        if dels:
            del_map = {f"{d['delivery_number']} - {d['item_name']} ({d['status']})": d['id'] for d in dels}
            sel_del = st.selectbox("출하 선택", list(del_map.keys()))
            new_del_st = st.selectbox("변경 상태", ["출하준비","피킹완료","포장완료","출하완료","배송중","배송완료"])
            if st.button("🔄 상태 변경", use_container_width=True, key="del_status"):
                conn = get_db()
                conn.execute("UPDATE deliveries SET status=? WHERE id=?", (new_del_st, del_map[sel_del]))
                conn.commit(); conn.close()
                st.success("변경 완료!"); st.rerun()

# ── 5. 청구서 ──────────────────────────────────────
with tabs[4]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("청구서 등록")
        conn = get_db()
        sos_inv = conn.execute("SELECT id, order_number, customer_name, quantity, unit_price, discount_rate FROM sales_orders").fetchall()
        conn.close()
        so_inv_opts = {f"{o['order_number']} - {o['customer_name']}": o for o in sos_inv}

        with st.form("inv_form", clear_on_submit=True):
            so_inv_sel = st.selectbox("판매주문(SO) *", list(so_inv_opts.keys()) if so_inv_opts else ["없음"])
            if so_inv_opts and so_inv_sel in so_inv_opts:
                so_data = so_inv_opts[so_inv_sel]
                auto_amt = so_data['quantity'] * so_data['unit_price'] * (1 - so_data['discount_rate']/100)
                auto_cust = so_data['customer_name']
            else:
                auto_amt, auto_cust = 0.0, ""

            cust_name_inv = st.text_input("고객명", value=auto_cust)
            col_a, col_b = st.columns(2)
            amount    = col_a.number_input("공급가액", min_value=0.0, value=float(auto_amt), format="%.0f")
            tax_rate  = col_b.selectbox("세율(%)", [10, 0])
            tax_amt   = amount * tax_rate / 100
            st.info(f"세액: ₩{tax_amt:,.0f} | 청구합계: ₩{amount+tax_amt:,.0f}")
            col_c, col_d = st.columns(2)
            issue_dt  = col_c.date_input("발행일")
            due_dt    = col_d.date_input("결제기한")
            paid      = st.checkbox("결제완료")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not so_inv_opts:
                    st.error("판매주문 필요")
                else:
                    try:
                        inum = gen_number("INV")
                        so_obj = so_inv_opts[so_inv_sel]
                        conn = get_db()
                        conn.execute("""INSERT INTO invoices
                            (invoice_number,order_id,customer_name,amount,tax_amount,issue_date,due_date,paid,paid_at)
                            VALUES(?,?,?,?,?,?,?,?,?)""",
                            (inum,so_obj['id'],cust_name_inv,amount,tax_amt,
                             str(issue_dt),str(due_dt),1 if paid else 0,
                             str(issue_dt) if paid else None))
                        conn.commit(); conn.close()
                        st.success(f"청구서 {inum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("청구서 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT invoice_number AS 청구번호, customer_name AS 고객,
                   amount AS 공급가액, tax_amount AS 세액,
                   ROUND(amount+tax_amount,0) AS 합계,
                   issue_date AS 발행일, due_date AS 결제기한,
                   CASE paid WHEN 1 THEN '✅완료' ELSE '🔴미결' END AS 결제상태
            FROM invoices ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("청구서 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            unpaid = df[df['결제상태']=='🔴미결']['합계'].sum()
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("미결 합계", f"₩{unpaid:,.0f}", delta_color="inverse")
            col_m2.metric("총 청구건수", len(df))

        st.divider()
        st.subheader("결제 처리")
        conn = get_db()
        unpaid_invs = conn.execute("SELECT id, invoice_number, customer_name FROM invoices WHERE paid=0").fetchall()
        conn.close()
        if unpaid_invs:
            inv_map = {f"{i['invoice_number']} - {i['customer_name']}": i['id'] for i in unpaid_invs}
            sel_inv = st.selectbox("미결 청구서", list(inv_map.keys()))
            if st.button("💳 결제 완료 처리", use_container_width=True):
                conn = get_db()
                conn.execute("UPDATE invoices SET paid=1, paid_at=datetime('now','localtime') WHERE id=?",
                             (inv_map[sel_inv],))
                conn.commit(); conn.close()
                st.success("결제 완료 처리!"); st.rerun()

# ── 6. 반품 ──────────────────────────────────────
with tabs[5]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("반품 등록")
        conn = get_db()
        sos_ret = conn.execute("SELECT id, order_number, item_name, quantity, unit_price FROM sales_orders WHERE status IN ('배송완료','배송중')").fetchall()
        conn.close()
        so_ret_opts = {f"{o['order_number']} - {o['item_name']}": o for o in sos_ret}

        with st.form("return_form", clear_on_submit=True):
            so_ret_sel = st.selectbox("반품 주문", list(so_ret_opts.keys()) if so_ret_opts else ["없음"])
            if so_ret_opts and so_ret_sel in so_ret_opts:
                ret_data = so_ret_opts[so_ret_sel]
                auto_item = ret_data['item_name']
            else:
                ret_data, auto_item = None, ""

            item_ret  = st.text_input("품목명", value=auto_item)
            col_a, col_b = st.columns(2)
            ret_qty   = col_a.number_input("반품수량", min_value=1, value=1)
            reason    = col_b.selectbox("반품사유", ["고객변심","오배송","상품불량","파손","수량오류","기타"])
            refund_amt= st.number_input("환불금액", min_value=0.0, format="%.0f",
                                         value=float(ret_data['unit_price']*ret_qty) if ret_data else 0.0)
            status_r  = st.selectbox("처리상태", ["반품접수","검수중","재고반영","폐기처리","환불완료"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not so_ret_opts:
                    st.error("반품 가능한 주문 없음")
                else:
                    try:
                        rnum = gen_number("RET")
                        conn = get_db()
                        conn.execute("""INSERT INTO returns
                            (return_number,order_id,item_name,quantity,reason,refund_amount,status)
                            VALUES(?,?,?,?,?,?,?)""",
                            (rnum,ret_data['id'],item_ret,ret_qty,reason,refund_amt,status_r))
                        # 재고 복구 (재고반영 상태인 경우)
                        if status_r == '재고반영':
                            conn.execute("""UPDATE inventory SET stock_qty=stock_qty+?, system_qty=system_qty+?,
                                updated_at=datetime('now','localtime') WHERE item_name LIKE ?""",
                                (ret_qty, ret_qty, f"%{item_ret}%"))
                        conn.commit(); conn.close()
                        st.success(f"반품 {rnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("반품 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT r.return_number AS 반품번호, o.order_number AS 주문번호,
                   r.item_name AS 품목, r.quantity AS 수량,
                   r.reason AS 사유, r.refund_amount AS 환불금액,
                   r.status AS 상태, r.created_at AS 등록일
            FROM returns r LEFT JOIN sales_orders o ON r.order_id=o.id
            ORDER BY r.id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("반품 없음")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("반품건수", len(df))
            col_m2.metric("총 환불금액", f"₩{df['환불금액'].sum():,.0f}", delta_color="inverse")

        st.divider()
        st.subheader("반품 사유 분석")
        if not df.empty:
            reason_cnt = df['사유'].value_counts().reset_index()
            reason_cnt.columns = ['사유','건수']
            st.bar_chart(reason_cnt.set_index('사유'))

# ── 7. 수익성 분석 ──────────────────────────────────────
with tabs[6]:
    st.subheader("📊 SD 수익성 분석")
    conn = get_db()
    df_so = pd.read_sql_query("""
        SELECT platform AS 채널, customer_name AS 고객,
               item_name AS 품목, quantity AS 수량,
               unit_price AS 단가, discount_rate AS 할인율,
               ROUND(quantity*unit_price*(1-discount_rate/100),0) AS 매출,
               status AS 상태, ordered_at AS 주문일
        FROM sales_orders WHERE status != '취소'""", conn)
    df_ret = pd.read_sql_query("SELECT SUM(refund_amount) AS total_refund FROM returns", conn)
    df_inv = pd.read_sql_query("SELECT SUM(amount+tax_amount) AS total_inv, SUM(CASE paid WHEN 1 THEN amount+tax_amount ELSE 0 END) AS paid_inv FROM invoices", conn)
    conn.close()

    total_rev    = df_so['매출'].sum() if not df_so.empty else 0
    total_refund = df_ret['total_refund'][0] or 0
    net_rev      = total_rev - total_refund
    total_billed = df_inv['total_inv'][0] or 0
    paid_billed  = df_inv['paid_inv'][0] or 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 매출", f"₩{total_rev:,.0f}")
    col2.metric("반품 차감", f"₩{total_refund:,.0f}", delta_color="inverse")
    col3.metric("순 매출", f"₩{net_rev:,.0f}")
    col4.metric("청구 수금률", f"{paid_billed/total_billed*100:.1f}%" if total_billed > 0 else "0%")

    st.divider()
    if not df_so.empty:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("채널별 매출")
            ch = df_so.groupby('채널')['매출'].sum().reset_index().sort_values('매출', ascending=False)
            st.bar_chart(ch.set_index('채널'))
        with col_r:
            st.subheader("품목별 매출 TOP 10")
            item_rev = df_so.groupby('품목')['매출'].sum().reset_index().sort_values('매출', ascending=False).head(10)
            st.bar_chart(item_rev.set_index('품목'))

        st.subheader("고객별 매출")
        cust_rev = df_so.groupby('고객')['매출'].sum().reset_index().sort_values('매출', ascending=False)
        st.dataframe(cust_rev, use_container_width=True, hide_index=True)
