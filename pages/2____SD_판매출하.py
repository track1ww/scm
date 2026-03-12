# -*- coding: utf-8 -*-
"""
Created on Sat Mar  7 13:42:40 2026

@author: yuns
"""
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  7 13:45:08 2026

@author: yuns
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number
from utils.design import inject_css, apply_plotly_theme
from datetime import datetime, timedelta, date

def _add_col(table, col, col_type="TEXT"):
    try:
        conn = get_db(); conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"); conn.commit(); conn.close()
    except: pass

# MySQL: db.py init_db()에서 모든 테이블 생성 — 중복 CREATE TABLE 불필요
_add_col("deliveries","customer_name"); _add_col("deliveries","address")
_add_col("deliveries","actual_delivery"); _add_col("customers","payment_terms","VARCHAR(50) DEFAULT '30일'")
_add_col("customers","tax_number"); _add_col("customers","region")

st.title("🛍️ SD – Sales & Distribution (판매/출하/청구)")
inject_css()
apply_plotly_theme()

main_tabs = st.tabs(["👥 고객·가격", "📋 수주 프로세스", "🚚 출하·배송", "💰 청구·채권", "👤 영업관리", "📊 영업 분석"])
tabs = {}
with main_tabs[0]:
    s = st.tabs(["👥 고객 마스터", "💳 신용한도 관리", "💲 가격 조건표", "📊 고객 분석"])
    tabs.update({"cust":s[0],"credit":s[1],"price":s[2],"bi_cust":s[3]})
with main_tabs[1]:
    s = st.tabs(["💬 고객 견적", "📋 판매주문(SO)", "✅ ATP 가용확인", "🔄 SO 상태관리", "🔗 PP 생산연동", "📊 수주 분석"])
    tabs.update({"sdq":s[0],"so":s[1],"atp":s[2],"so_st":s[3],"so_pp":s[4],"bi_so":s[5]})
with main_tabs[2]:
    s = st.tabs(["🚚 출하/피킹", "📦 부분출하 관리", "🔍 배송 추적", "📅 납기약속(CRD)", "↩️ 반품", "📦 포장명세서", "🔧 AS 접수", "📊 출하 분석"])
    tabs.update({"deli":s[0],"partial":s[1],"track":s[2],"crd":s[3],"ret":s[4],"packing":s[5],"as_":s[6],"bi_del":s[7]})
with main_tabs[3]:
    s = st.tabs(["🧾 청구서", "🧾 매출세금계산서", "💳 수금 관리", "💵 선수금 관리", "📋 채권 Aging", "📊 청구 분석"])
    tabs.update({"inv":s[0],"sti":s[1],"ar":s[2],"prepay":s[3],"aging":s[4],"bi_ar":s[5]})
with main_tabs[4]:
    s = st.tabs(["👤 영업사원 관리", "📊 영업사원 실적"])
    tabs.update({"sales_mgr":s[0],"bi_sales_rep":s[1]})
with main_tabs[5]:
    s = st.tabs(["🎯 매출 목표관리", "📈 매출 추이", "🏆 고객·품목", "↩️ 반품 분석", "💹 수익성"])
    tabs.update({"bi_target":s[0],"bi_sales":s[1],"bi_item":s[2],"bi_ret":s[3],"bi_profit":s[4]})

with st.sidebar:
    st.divider(); st.markdown("### 📊 분석 기간")
    bp = st.selectbox("기간",["최근 1개월","최근 3개월","최근 6개월","최근 1년","전체"],key="sd_bp")
    bi_from = (datetime.now()-timedelta(days={"최근 1개월":30,"최근 3개월":90,"최근 6개월":180,"최근 1년":365,"전체":9999}[bp])).strftime("%Y-%m-%d")

try:
    import plotly.express as px; import plotly.graph_objects as go
    from plotly.subplots import make_subplots; HAS_PL=True
except: HAS_PL=False

def _ef(msg="데이터 없음"):
    if not HAS_PL: return None
    fig=go.Figure(); fig.add_annotation(text=msg,x=0.5,y=0.5,xref="paper",yref="paper",showarrow=False,font=dict(size=13,color="#9ca3af"))
    fig.update_layout(height=260,margin=dict(l=0,r=0,t=10,b=0),plot_bgcolor="#f9fafb",paper_bgcolor="#f9fafb"); return fig

# ══ 고객 마스터 ══════════════════════════════════════════
with tabs["cust"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("고객 등록/수정")
        with st.form("cust_f",clear_on_submit=True):
            a,b=st.columns(2); cust_code=a.text_input("고객코드 *"); cust_name=b.text_input("고객명 *")
            c,d=st.columns(2); contact=c.text_input("담당자"); phone=d.text_input("전화")
            email=st.text_input("이메일"); address=st.text_area("주소",height=50)
            e,f=st.columns(2); cust_grp=e.selectbox("고객군",["일반","VIP","도매","소매","B2B","해외"]); region=f.text_input("지역")
            g,h=st.columns(2); tax_num=g.text_input("사업자번호"); pay_terms=h.selectbox("결제조건",["현금","30일","60일","90일","선불"])
            credit=st.number_input("여신한도(₩)",min_value=0.0,format="%.0f"); status=st.selectbox("상태",["활성","휴면","거래중지"])
            if st.form_submit_button("✅ 저장",use_container_width=True):
                if not cust_code or not cust_name: st.error("필수 항목 누락")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO customers(customer_code,customer_name,contact,phone,email,address,customer_group,credit_limit,status,tax_number,region,payment_terms)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                            ON DUPLICATE KEY UPDATE customer_name=VALUES(customer_name),contact=VALUES(contact),phone=VALUES(phone),email=VALUES(email),address=VALUES(address),customer_group=VALUES(customer_group),credit_limit=VALUES(credit_limit),status=VALUES(status),tax_number=VALUES(tax_number),region=VALUES(region),payment_terms=VALUES(payment_terms)""",
                            (cust_code,cust_name,contact,phone,email,address,cust_grp,credit,status,tax_num,region,pay_terms))
                        conn.commit(); conn.close(); st.success("저장!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("고객 목록")
        conn=get_db()
        df_c=pd.read_sql_query("SELECT customer_code AS 코드,customer_name AS 고객명,contact AS 담당자,customer_group AS 그룹,region AS 지역,payment_terms AS 결제조건,credit_limit AS 여신한도,credit_used AS 여신사용,status AS 상태 FROM customers ORDER BY id DESC",conn); conn.close()
        if df_c.empty: st.info("없음")
        else:
            srch=st.text_input("🔍 검색")
            if srch: df_c=df_c[df_c['고객명'].str.contains(srch,na=False)]
            def hl(r): return ['background-color:#fee2e2']*len(r) if r['여신한도']>0 and r['여신사용']>=r['여신한도'] else ['']*len(r)
            st.dataframe(df_c.style.apply(hl,axis=1),use_container_width=True,hide_index=True)

            # ── 행 수정/삭제 버튼 (고객) ──────────────────────────
            if not df_c.empty if hasattr(df_c, 'empty') else df_c is not None:
                _row_opts_customers = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 고객명 FROM customers ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('고객명','')}"
                        _row_opts_customers[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_customers:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_customers = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_customers.keys()),
                        key="_rbsel_customers", label_visibility="collapsed"
                    )
                    _rb_id_customers = _row_opts_customers[_rb_sel_customers]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_customers"):
                        st.session_state[f"_edit_customers"] = _rb_id_customers
                        st.session_state[f"_del_customers"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_customers"):
                        st.session_state[f"_del_customers"]  = _rb_id_customers
                        st.session_state[f"_edit_customers"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_customers"):
                    _del_id_customers = st.session_state[f"_del_customers"]
                    st.warning(f"⚠️ ID **{_del_id_customers}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_customers"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM customers WHERE id = ?", (_del_id_customers,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_customers"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_customers"):
                        st.session_state[f"_del_customers"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_customers"):
                    _edit_id_customers = st.session_state[f"_edit_customers"]
                    try:
                        _cx_e = get_db()
                        _edit_row_customers = dict(_cx_e.execute(
                            "SELECT * FROM customers WHERE id=?", (_edit_id_customers,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_customers = {}
                    with st.expander(f"✏️ 고객 수정 — ID {_edit_id_customers}", expanded=True):
                        if not _edit_row_customers:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_customers = [c for c in _edit_row_customers if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_customers)))
                            _ecols = st.columns(_ncols)
                            _new_vals_customers = {}
                            for _i, _fc in enumerate(_edit_fields_customers):
                                _cv = _edit_row_customers[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_customers[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_customers}_{_fc}_customers")
                                else:
                                    _new_vals_customers[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_customers}_{_fc}_customers")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_customers"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_customers])
                                _set_params = list(_new_vals_customers.values()) + [_edit_id_customers]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE customers SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_customers"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_customers"):
                                st.session_state[f"_edit_customers"] = None; st.rerun()


# ══ 가격 조건표 ══════════════════════════════════════════
with tabs["price"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("가격 조건 등록")
        conn=get_db(); custs_p=conn.execute("SELECT id,customer_code,customer_name FROM customers WHERE status='활성'").fetchall(); conn.close()
        with st.form("price_f",clear_on_submit=True):
            cp_opts={"공통(전체고객)":None}|{f"{c['customer_code']}-{c['customer_name']}":c['id'] for c in custs_p}
            cp_sel=st.selectbox("고객",list(cp_opts.keys())); item_p=st.text_input("품목명 *")
            a,b=st.columns(2); pt=a.selectbox("가격유형",["기본단가","고객특가","수량할인","시즌가","계약가"]); cur=b.selectbox("통화",["KRW","USD","EUR"])
            c,d=st.columns(2); up=c.number_input("단가",min_value=0.0,format="%.2f"); disc=d.number_input("할인율(%)",min_value=0.0,max_value=100.0,format="%.1f")
            e,f=st.columns(2); mq=e.number_input("최소수량",min_value=1,value=1); vf=f.date_input("유효시작")
            vt=st.date_input("유효종료",value=date.today()+timedelta(days=365)); note_p=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not item_p: st.error("품목명 필수")
                else:
                    conn=get_db()
                    conn.execute("INSERT INTO price_conditions(customer_id,item_name,price_type,unit_price,discount_rate,valid_from,valid_to,currency,min_qty,note) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (cp_opts[cp_sel],item_p,pt,up,disc,str(vf),str(vt),cur,mq,note_p))
                    conn.commit(); conn.close(); st.success("등록!"); st.rerun()
    with col_list:
        st.subheader("가격 조건 목록")
        conn=get_db()
        df_pc=pd.read_sql_query("SELECT p.item_name AS 품목,p.price_type AS 유형,COALESCE(c.customer_name,'공통') AS 고객,p.unit_price AS 단가,p.discount_rate AS 할인율,p.currency AS 통화,p.min_qty AS 최소수량,p.valid_from AS 시작,p.valid_to AS 종료 FROM price_conditions p LEFT JOIN customers c ON p.customer_id=c.id ORDER BY p.id DESC",conn); conn.close()
        if df_pc.empty: st.info("없음")
        else: st.dataframe(df_pc,use_container_width=True,hide_index=True)

        # ── 행 수정/삭제 버튼 (가격조건) ──────────────────────────
        if not df_pc.empty if hasattr(df_pc, 'empty') else df_pc is not None:
            _row_opts_price_conditions = {}
            try:
                _cx_opt = get_db()
                _opt_rs = [dict(r) for r in _cx_opt.execute(
                    "SELECT id, 품목 FROM price_conditions ORDER BY id DESC LIMIT 300"
                ).fetchall()]
                _cx_opt.close()
                for _r in _opt_rs:
                    _k = f"{_r['id']} | {_r.get('품목','')}"
                    _row_opts_price_conditions[_k] = _r['id']
            except Exception:
                pass

            if _row_opts_price_conditions:
                _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                _rb_sel_price_conditions = _rb_sel_col.selectbox(
                    "행 선택", list(_row_opts_price_conditions.keys()),
                    key="_rbsel_price_conditions", label_visibility="collapsed"
                )
                _rb_id_price_conditions = _row_opts_price_conditions[_rb_sel_price_conditions]

                if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_price_conditions"):
                    st.session_state[f"_edit_price_conditions"] = _rb_id_price_conditions
                    st.session_state[f"_del_price_conditions"]  = None

                if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_price_conditions"):
                    st.session_state[f"_del_price_conditions"]  = _rb_id_price_conditions
                    st.session_state[f"_edit_price_conditions"] = None

            # ── 삭제 확인 ──────────────────────────────────────────
            if st.session_state.get(f"_del_price_conditions"):
                _del_id_price_conditions = st.session_state[f"_del_price_conditions"]
                st.warning(f"⚠️ ID **{_del_id_price_conditions}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                _dc1, _dc2 = st.columns(2)
                if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_price_conditions"):
                    _cx_d = get_db()
                    _cx_d.execute("DELETE FROM price_conditions WHERE id = ?", (_del_id_price_conditions,))
                    _cx_d.commit(); _cx_d.close()
                    st.session_state[f"_del_price_conditions"] = None
                    st.success("✅ 삭제 완료!"); st.rerun()
                if _dc2.button("취소", use_container_width=True, key="_delcancel_price_conditions"):
                    st.session_state[f"_del_price_conditions"] = None; st.rerun()

            # ── 수정 인라인 폼 ─────────────────────────────────────
            if st.session_state.get(f"_edit_price_conditions"):
                _edit_id_price_conditions = st.session_state[f"_edit_price_conditions"]
                try:
                    _cx_e = get_db()
                    _edit_row_price_conditions = dict(_cx_e.execute(
                        "SELECT * FROM price_conditions WHERE id=?", (_edit_id_price_conditions,)
                    ).fetchone() or {})
                    _cx_e.close()
                except Exception:
                    _edit_row_price_conditions = {}
                with st.expander(f"✏️ 가격조건 수정 — ID {_edit_id_price_conditions}", expanded=True):
                    if not _edit_row_price_conditions:
                        st.warning("데이터를 불러올 수 없습니다.")
                    else:
                        _skip_cols = {'id','created_at','updated_at'}
                        _edit_fields_price_conditions = [c for c in _edit_row_price_conditions if c not in _skip_cols]
                        _ncols = min(3, max(1, len(_edit_fields_price_conditions)))
                        _ecols = st.columns(_ncols)
                        _new_vals_price_conditions = {}
                        for _i, _fc in enumerate(_edit_fields_price_conditions):
                            _cv = _edit_row_price_conditions[_fc]
                            _ec = _ecols[_i % _ncols]
                            if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                _new_vals_price_conditions[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_price_conditions}_{_fc}_price_conditions")
                            else:
                                _new_vals_price_conditions[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_price_conditions}_{_fc}_price_conditions")
                        _s1, _s2 = st.columns(2)
                        if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_price_conditions"):
                            _set_sql = ", ".join([f"{c}=?" for c in _new_vals_price_conditions])
                            _set_params = list(_new_vals_price_conditions.values()) + [_edit_id_price_conditions]
                            _cx_s = get_db()
                            _cx_s.execute(f"UPDATE price_conditions SET {_set_sql} WHERE id=?", _set_params)
                            _cx_s.commit(); _cx_s.close()
                            st.session_state[f"_edit_price_conditions"] = None
                            st.success("✅ 수정 저장 완료!"); st.rerun()
                        if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_price_conditions"):
                            st.session_state[f"_edit_price_conditions"] = None; st.rerun()

        st.divider(); st.subheader("💡 가격 시뮬레이션")
        conn=get_db(); items_sim=[r[0] for r in conn.execute("SELECT DISTINCT item_name FROM price_conditions").fetchall()]; conn.close()
        if items_sim:
            si=st.selectbox("품목",items_sim); sq=st.number_input("수량",min_value=1,value=10)
            conn=get_db(); pcs=conn.execute("SELECT p.*,COALESCE(c.customer_name,'공통') AS cname FROM price_conditions p LEFT JOIN customers c ON p.customer_id=c.id WHERE p.item_name=? AND (p.min_qty<=? OR p.customer_id IS NULL) ORDER BY p.discount_rate DESC",(si,sq)).fetchall(); conn.close()
            if pcs: st.dataframe(pd.DataFrame([{"고객":r['cname'],"유형":r['price_type'],"단가":r['unit_price'],"할인율":r['discount_rate'],"적용금액":round(r['unit_price']*sq*(1-r['discount_rate']/100),0)} for r in pcs]),use_container_width=True,hide_index=True)

# ══ 고객 분석 BI ══════════════════════════════════════════
with tabs["bi_cust"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        c1,c2,c3=st.columns(3)
        c1.metric("활성 고객",conn.execute("SELECT COUNT(*) FROM customers WHERE status='활성'").fetchone()[0])
        c2.metric("VIP",conn.execute("SELECT COUNT(*) FROM customers WHERE customer_group='VIP'").fetchone()[0])
        c3.metric("여신초과",conn.execute("SELECT COUNT(*) FROM customers WHERE credit_limit>0 AND credit_used>=credit_limit").fetchone()[0],delta_color="inverse")
        col_l,col_r=st.columns(2)
        with col_l:
            df_g=pd.read_sql_query("SELECT customer_group AS 그룹,COUNT(*) AS 수 FROM customers GROUP BY customer_group",conn)
            if not df_g.empty: st.plotly_chart(px.pie(df_g,names='그룹',values='수',title="고객군",hole=0.4).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        with col_r:
            df_tc=pd.read_sql_query(f"SELECT customer_name AS 고객,ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 매출 FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}' GROUP BY customer_name ORDER BY 매출 DESC LIMIT 8",conn)
            if not df_tc.empty: st.plotly_chart(px.bar(df_tc,y='고객',x='매출',orientation='h',color='매출',color_continuous_scale='Purples',title=f"고객 TOP8({bp})").update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
        conn.close()

# ══ 고객 견적 ══════════════════════════════════════════
with tabs["sdq"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("고객 견적 등록")
        conn=get_db(); custs2=conn.execute("SELECT id,customer_code,customer_name FROM customers WHERE status='활성'").fetchall(); conn.close()
        co={f"{c['customer_code']}-{c['customer_name']}":c['id'] for c in custs2}
        with st.form("sdq_f",clear_on_submit=True):
            cs=st.selectbox("고객 *",list(co.keys()) if co else ["없음"]); item_n=st.text_input("품목명 *")
            a,b,c=st.columns(3); qty=a.number_input("수량",min_value=1,value=1); up=b.number_input("단가",min_value=0.0,format="%.2f"); disc=c.number_input("할인율(%)",min_value=0.0,max_value=100.0)
            fp=qty*up*(1-disc/100); st.info(f"합계: ₩{fp:,.0f}")
            vu=st.date_input("유효기간",value=date.today()+timedelta(days=30)); st_q=st.selectbox("상태",["검토중","승인","반려","만료"]); note_q=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not item_n or not co: st.error("필수 누락")
                else:
                    try:
                        conn=get_db(); conn.execute("INSERT INTO sd_quotations(sd_quote_number,customer_id,item_name,quantity,unit_price,discount_rate,final_price,valid_until,status,note) VALUES(?,?,?,?,?,?,?,?,?,?)",(gen_number("SDQ"),co.get(cs),item_n,qty,up,disc,fp,str(vu),st_q,note_q)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("견적 목록")
        conn=get_db(); df_q=pd.read_sql_query("SELECT q.sd_quote_number AS 견적번호,c.customer_name AS 고객,q.item_name AS 품목,q.quantity AS 수량,q.unit_price AS 단가,q.discount_rate AS 할인율,q.final_price AS 견적금액,q.valid_until AS 유효기간,q.status AS 상태 FROM sd_quotations q LEFT JOIN customers c ON q.customer_id=c.id ORDER BY q.id DESC",conn); conn.close()
        if df_q.empty: st.info("없음")
        else: st.dataframe(df_q,use_container_width=True,hide_index=True)

        # ── 행 수정/삭제 버튼 (견적) ──────────────────────────
        if not df_q.empty if hasattr(df_q, 'empty') else df_q is not None:
            _row_opts_sd_quotations = {}
            try:
                _cx_opt = get_db()
                _opt_rs = [dict(r) for r in _cx_opt.execute(
                    "SELECT id, 품목 FROM sd_quotations ORDER BY id DESC LIMIT 300"
                ).fetchall()]
                _cx_opt.close()
                for _r in _opt_rs:
                    _k = f"{_r['id']} | {_r.get('품목','')}"
                    _row_opts_sd_quotations[_k] = _r['id']
            except Exception:
                pass

            if _row_opts_sd_quotations:
                _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                _rb_sel_sd_quotations = _rb_sel_col.selectbox(
                    "행 선택", list(_row_opts_sd_quotations.keys()),
                    key="_rbsel_sd_quotations", label_visibility="collapsed"
                )
                _rb_id_sd_quotations = _row_opts_sd_quotations[_rb_sel_sd_quotations]

                if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_sd_quotations"):
                    st.session_state[f"_edit_sd_quotations"] = _rb_id_sd_quotations
                    st.session_state[f"_del_sd_quotations"]  = None

                if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_sd_quotations"):
                    st.session_state[f"_del_sd_quotations"]  = _rb_id_sd_quotations
                    st.session_state[f"_edit_sd_quotations"] = None

            # ── 삭제 확인 ──────────────────────────────────────────
            if st.session_state.get(f"_del_sd_quotations"):
                _del_id_sd_quotations = st.session_state[f"_del_sd_quotations"]
                st.warning(f"⚠️ ID **{_del_id_sd_quotations}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                _dc1, _dc2 = st.columns(2)
                if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_sd_quotations"):
                    _cx_d = get_db()
                    _cx_d.execute("DELETE FROM sd_quotations WHERE id = ?", (_del_id_sd_quotations,))
                    _cx_d.commit(); _cx_d.close()
                    st.session_state[f"_del_sd_quotations"] = None
                    st.success("✅ 삭제 완료!"); st.rerun()
                if _dc2.button("취소", use_container_width=True, key="_delcancel_sd_quotations"):
                    st.session_state[f"_del_sd_quotations"] = None; st.rerun()

            # ── 수정 인라인 폼 ─────────────────────────────────────
            if st.session_state.get(f"_edit_sd_quotations"):
                _edit_id_sd_quotations = st.session_state[f"_edit_sd_quotations"]
                try:
                    _cx_e = get_db()
                    _edit_row_sd_quotations = dict(_cx_e.execute(
                        "SELECT * FROM sd_quotations WHERE id=?", (_edit_id_sd_quotations,)
                    ).fetchone() or {})
                    _cx_e.close()
                except Exception:
                    _edit_row_sd_quotations = {}
                with st.expander(f"✏️ 견적 수정 — ID {_edit_id_sd_quotations}", expanded=True):
                    if not _edit_row_sd_quotations:
                        st.warning("데이터를 불러올 수 없습니다.")
                    else:
                        _skip_cols = {'id','created_at','updated_at'}
                        _edit_fields_sd_quotations = [c for c in _edit_row_sd_quotations if c not in _skip_cols]
                        _ncols = min(3, max(1, len(_edit_fields_sd_quotations)))
                        _ecols = st.columns(_ncols)
                        _new_vals_sd_quotations = {}
                        for _i, _fc in enumerate(_edit_fields_sd_quotations):
                            _cv = _edit_row_sd_quotations[_fc]
                            _ec = _ecols[_i % _ncols]
                            if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                _new_vals_sd_quotations[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_sd_quotations}_{_fc}_sd_quotations")
                            else:
                                _new_vals_sd_quotations[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_sd_quotations}_{_fc}_sd_quotations")
                        _s1, _s2 = st.columns(2)
                        if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_sd_quotations"):
                            _set_sql = ", ".join([f"{c}=?" for c in _new_vals_sd_quotations])
                            _set_params = list(_new_vals_sd_quotations.values()) + [_edit_id_sd_quotations]
                            _cx_s = get_db()
                            _cx_s.execute(f"UPDATE sd_quotations SET {_set_sql} WHERE id=?", _set_params)
                            _cx_s.commit(); _cx_s.close()
                            st.session_state[f"_edit_sd_quotations"] = None
                            st.success("✅ 수정 저장 완료!"); st.rerun()
                        if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_sd_quotations"):
                            st.session_state[f"_edit_sd_quotations"] = None; st.rerun()

        st.divider(); st.subheader("견적 → SO 전환")
        conn=get_db(); aq=conn.execute("SELECT id,sd_quote_number,item_name FROM sd_quotations WHERE status='승인'").fetchall(); conn.close()
        if not aq: st.info("승인 견적 없음")
        else:
            qm={f"{q['sd_quote_number']}-{q['item_name']}":q['id'] for q in aq}; sq2=st.selectbox("전환할 견적",list(qm.keys()))
            if st.button("🔄 SO 전환",use_container_width=True):
                conn=get_db(); qd=conn.execute("SELECT * FROM sd_quotations WHERE id=?",(qm[sq2],)).fetchone()
                if qd:
                    ci=conn.execute("SELECT customer_name FROM customers WHERE id=?",(qd['customer_id'],)).fetchone()
                    conn.execute("INSERT INTO sales_orders(order_number,customer_id,sd_quote_id,customer_name,item_name,quantity,unit_price,discount_rate,status) VALUES(?,?,?,?,?,?,?,?,?)",(gen_number("SO"),qd['customer_id'],qd['id'],ci['customer_name'] if ci else "",qd['item_name'],qd['quantity'],qd['unit_price'],qd['discount_rate'],'주문접수'))
                    conn.execute("UPDATE sd_quotations SET status='만료' WHERE id=?",(qd['id'],)); conn.commit(); conn.close(); st.success("SO 생성!"); st.rerun()

# ══ 판매주문 SO ══════════════════════════════════════════
with tabs["so"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("판매주문 등록")
        conn=get_db(); custs3=conn.execute("SELECT id,customer_code,customer_name,credit_limit,credit_used FROM customers WHERE status='활성'").fetchall(); conn.close()
        c3o={f"{c['customer_code']}-{c['customer_name']}":c for c in custs3}
        with st.form("so_f",clear_on_submit=True):
            cs3=st.selectbox("고객 *",list(c3o.keys()) if c3o else ["없음"])
            a,b=st.columns(2); item_so=a.text_input("품목명 *"); pf=b.selectbox("채널",["직판","온라인","대리점","해외","도매","기타"])
            c,d,e=st.columns(3); qty_so=c.number_input("수량",min_value=1,value=1); up_so=d.number_input("단가",min_value=0.0,format="%.2f"); disc_so=e.number_input("할인율(%)",min_value=0.0,max_value=100.0)
            total_so=qty_so*up_so*(1-disc_so/100); st.info(f"주문금액: ₩{total_so:,.0f}")
            f2,g2=st.columns(2); rd=f2.date_input("납기요청일"); cd2=g2.date_input("납기확정일")
            if cs3 in c3o:
                cd_data=c3o[cs3]
                if cd_data['credit_limit']>0 and (cd_data['credit_used'] or 0)+total_so>cd_data['credit_limit']:
                    st.warning(f"⚠️ 여신한도 초과! 한도: ₩{cd_data['credit_limit']:,.0f}")
            if item_so:
                conn=get_db(); atp=conn.execute("SELECT COALESCE(stock_qty,0) FROM inventory WHERE item_name LIKE ?",(f"%{item_so}%",)).fetchone(); conn.close()
                if atp: st.info(f"{'🟢' if atp[0]>=qty_so else '🔴'} ATP 재고: {atp[0]}개 (요청: {qty_so}개)")
            st_so=st.selectbox("상태",["주문접수","신용검토중","생산/조달중","출하준비","배송중","배송완료","취소"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not item_so or not c3o: st.error("필수 누락")
                else:
                    try:
                        cd3=c3o.get(cs3); conn=get_db()
                        conn.execute("INSERT INTO sales_orders(order_number,customer_id,customer_name,item_name,platform,quantity,unit_price,discount_rate,requested_delivery,confirmed_delivery,atp_checked,credit_checked,status) VALUES(?,?,?,?,?,?,?,?,?,?,1,1,?)",(gen_number("SO"),cd3['id'] if cd3 else None,cd3['customer_name'] if cd3 else "",item_so,pf,qty_so,up_so,disc_so,str(rd),str(cd2),st_so))
                        if cd3: conn.execute("UPDATE customers SET credit_used=credit_used+? WHERE id=?",(total_so,cd3['id']))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("판매주문 목록")
        conn=get_db(); df_so2=pd.read_sql_query("SELECT order_number AS SO번호,customer_name AS 고객,item_name AS 품목,platform AS 채널,quantity AS 수량,ROUND(quantity*unit_price*(1-discount_rate/100),0) AS 주문금액,requested_delivery AS 납기요청,status AS 상태,ordered_at AS 주문일 FROM sales_orders ORDER BY id DESC",conn); conn.close()
        if df_so2.empty: st.info("없음")
        else:
            fs=st.multiselect("상태 필터",df_so2['상태'].unique().tolist(),default=df_so2['상태'].unique().tolist())
            st.dataframe(df_so2[df_so2['상태'].isin(fs)],use_container_width=True,hide_index=True)

            # ── 행 수정/삭제 버튼 (SO) ──────────────────────────
            if not df_so2.empty if hasattr(df_so2, 'empty') else df_so2 is not None:
                _row_opts_sales_orders = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM sales_orders ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_sales_orders[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_sales_orders:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_sales_orders = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_sales_orders.keys()),
                        key="_rbsel_sales_orders", label_visibility="collapsed"
                    )
                    _rb_id_sales_orders = _row_opts_sales_orders[_rb_sel_sales_orders]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_sales_orders"):
                        st.session_state[f"_edit_sales_orders"] = _rb_id_sales_orders
                        st.session_state[f"_del_sales_orders"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_sales_orders"):
                        st.session_state[f"_del_sales_orders"]  = _rb_id_sales_orders
                        st.session_state[f"_edit_sales_orders"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_sales_orders"):
                    _del_id_sales_orders = st.session_state[f"_del_sales_orders"]
                    st.warning(f"⚠️ ID **{_del_id_sales_orders}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_sales_orders"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM sales_orders WHERE id = ?", (_del_id_sales_orders,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_sales_orders"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_sales_orders"):
                        st.session_state[f"_del_sales_orders"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_sales_orders"):
                    _edit_id_sales_orders = st.session_state[f"_edit_sales_orders"]
                    try:
                        _cx_e = get_db()
                        _edit_row_sales_orders = dict(_cx_e.execute(
                            "SELECT * FROM sales_orders WHERE id=?", (_edit_id_sales_orders,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_sales_orders = {}
                    with st.expander(f"✏️ SO 수정 — ID {_edit_id_sales_orders}", expanded=True):
                        if not _edit_row_sales_orders:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_sales_orders = [c for c in _edit_row_sales_orders if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_sales_orders)))
                            _ecols = st.columns(_ncols)
                            _new_vals_sales_orders = {}
                            for _i, _fc in enumerate(_edit_fields_sales_orders):
                                _cv = _edit_row_sales_orders[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_sales_orders[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_sales_orders}_{_fc}_sales_orders")
                                else:
                                    _new_vals_sales_orders[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_sales_orders}_{_fc}_sales_orders")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_sales_orders"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_sales_orders])
                                _set_params = list(_new_vals_sales_orders.values()) + [_edit_id_sales_orders]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE sales_orders SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_sales_orders"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_sales_orders"):
                                st.session_state[f"_edit_sales_orders"] = None; st.rerun()


# ══ SO 상태관리 ══════════════════════════════════════════
with tabs["so_st"]:
    st.subheader("판매주문 상태 변경")
    conn=get_db(); df_so3=pd.read_sql_query("SELECT id,order_number,customer_name,item_name,status FROM sales_orders WHERE status NOT IN ('배송완료','취소') ORDER BY id DESC",conn); conn.close()
    if df_so3.empty: st.info("처리 중인 주문 없음")
    else:
        sm={f"{r['order_number']}-{r['customer_name']}/{r['item_name']}":r['id'] for _,r in df_so3.iterrows()}
        ss=st.selectbox("주문 선택",list(sm.keys())); ns=st.selectbox("변경 상태",["주문접수","신용검토중","생산/조달중","출하준비","배송중","배송완료","취소"])
        if st.button("✅ 상태 변경",use_container_width=True):
            conn=get_db(); conn.execute("UPDATE sales_orders SET status=? WHERE id=?",(ns,sm[ss])); conn.commit(); conn.close(); st.success("변경!"); st.rerun()
    st.divider()
    conn=get_db(); df_all=pd.read_sql_query("SELECT order_number AS SO번호,customer_name AS 고객,item_name AS 품목,status AS 상태,ordered_at AS 주문일 FROM sales_orders ORDER BY id DESC LIMIT 50",conn); conn.close()
    if not df_all.empty: st.dataframe(df_all,use_container_width=True,hide_index=True)

# ══ 수주 분석 BI ══════════════════════════════════════════
with tabs["bi_so"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        sc=conn.execute(f"SELECT COUNT(*) FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}'").fetchone()[0]
        sa=conn.execute(f"SELECT COALESCE(SUM(quantity*unit_price*(1-discount_rate/100)),0) FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}'").fetchone()[0]
        cc=conn.execute(f"SELECT COUNT(*) FROM sales_orders WHERE status='취소' AND ordered_at>='{bi_from}'").fetchone()[0]
        c1,c2,c3,c4=st.columns(4); c1.metric("수주건수",f"{sc}건"); c2.metric("수주금액",f"₩{sa:,.0f}"); c3.metric("평균금액",f"₩{round(sa/sc,0) if sc else 0:,.0f}"); c4.metric("취소",f"{cc}건",delta_color="inverse")
        col_l,col_r=st.columns(2)
        with col_l:
            df_t=pd.read_sql_query(f"SELECT DATE_FORMAT(ordered_at,'%%Y-%%m') AS 월,ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 수주금액,COUNT(*) AS 건수 FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}' GROUP BY DATE_FORMAT(ordered_at,'%%Y-%%m') ORDER BY 월",conn)
            if not df_t.empty:
                fig=make_subplots(specs=[[{"secondary_y":True}]])
                fig.add_trace(go.Bar(x=df_t['월'],y=df_t['수주금액'],name='수주금액',marker_color='#8b5cf6'),secondary_y=False)
                fig.add_trace(go.Scatter(x=df_t['월'],y=df_t['건수'],name='건수',mode='lines+markers',line=dict(color='#f97316',width=2)),secondary_y=True)
                fig.update_layout(title="월별 수주 추이",height=280,margin=dict(l=0,r=0,t=40,b=0),legend=dict(orientation="h",y=1.1))
                st.plotly_chart(fig,use_container_width=True)
        with col_r:
            df_ch=pd.read_sql_query(f"SELECT platform AS 채널,ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 금액 FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}' GROUP BY platform",conn)
            if not df_ch.empty: st.plotly_chart(px.pie(df_ch,names='채널',values='금액',title="채널별 구성",hole=0.4).update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()

# ══ 출하/피킹 ══════════════════════════════════════════
with tabs["deli"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("출하 등록")
        conn=get_db(); sod=conn.execute("SELECT id,order_number,customer_name,item_name,quantity FROM sales_orders WHERE status IN ('출하준비','주문접수','생산/조달중')").fetchall(); conn.close()
        sdo={f"{o['order_number']}-{o['customer_name']}/{o['item_name']}":o for o in sod}
        with st.form("del_f",clear_on_submit=True):
            dss=st.selectbox("판매주문 *",list(sdo.keys()) if sdo else ["없음"]); ad=sdo.get(dss)
            a,b=st.columns(2); dq=a.number_input("출하수량",min_value=1,value=int(ad['quantity']) if ad else 1); pq=b.number_input("피킹수량",min_value=0,value=int(ad['quantity']) if ad else 0)
            c,d=st.columns(2); packq=c.number_input("포장수량",min_value=0,value=0); carrier=d.text_input("운송사")
            tracking=st.text_input("운송장번호"); address=st.text_area("배송주소",height=40); dd=st.date_input("출하예정일")
            st_d=st.selectbox("상태",["출하준비","피킹완료","포장완료","출하완료","배송중","배송완료"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not sdo: st.error("출하 가능 주문 없음")
                else:
                    try:
                        conn=get_db()
                        conn.execute("INSERT INTO deliveries(delivery_number,order_id,item_name,delivery_qty,pick_qty,pack_qty,carrier,tracking_number,address,delivery_date,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(gen_number("DL"),ad['id'],ad['item_name'],dq,pq,packq,carrier,tracking,address,str(dd),st_d))
                        if st_d in ['배송중','배송완료']: conn.execute("UPDATE sales_orders SET status=? WHERE id=?",('배송중' if st_d=='배송중' else '배송완료',ad['id']))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("출하 목록")
        conn=get_db(); df_d=pd.read_sql_query("SELECT d.delivery_number AS 출하번호,o.order_number AS SO번호,d.item_name AS 품목,d.delivery_qty AS 수량,d.carrier AS 운송사,d.tracking_number AS 운송장,d.delivery_date AS 출하일,d.status AS 상태 FROM deliveries d LEFT JOIN sales_orders o ON d.order_id=o.id ORDER BY d.id DESC",conn); conn.close()
        if df_d.empty: st.info("없음")
        else: st.dataframe(df_d,use_container_width=True,hide_index=True)

        # ── 행 수정/삭제 버튼 (출하) ──────────────────────────
        if not df_d.empty if hasattr(df_d, 'empty') else df_d is not None:
            _row_opts_deliveries = {}
            try:
                _cx_opt = get_db()
                _opt_rs = [dict(r) for r in _cx_opt.execute(
                    "SELECT id, 품목명 FROM deliveries ORDER BY id DESC LIMIT 300"
                ).fetchall()]
                _cx_opt.close()
                for _r in _opt_rs:
                    _k = f"{_r['id']} | {_r.get('품목명','')}"
                    _row_opts_deliveries[_k] = _r['id']
            except Exception:
                pass

            if _row_opts_deliveries:
                _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                _rb_sel_deliveries = _rb_sel_col.selectbox(
                    "행 선택", list(_row_opts_deliveries.keys()),
                    key="_rbsel_deliveries", label_visibility="collapsed"
                )
                _rb_id_deliveries = _row_opts_deliveries[_rb_sel_deliveries]

                if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_deliveries"):
                    st.session_state[f"_edit_deliveries"] = _rb_id_deliveries
                    st.session_state[f"_del_deliveries"]  = None

                if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_deliveries"):
                    st.session_state[f"_del_deliveries"]  = _rb_id_deliveries
                    st.session_state[f"_edit_deliveries"] = None

            # ── 삭제 확인 ──────────────────────────────────────────
            if st.session_state.get(f"_del_deliveries"):
                _del_id_deliveries = st.session_state[f"_del_deliveries"]
                st.warning(f"⚠️ ID **{_del_id_deliveries}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                _dc1, _dc2 = st.columns(2)
                if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_deliveries"):
                    _cx_d = get_db()
                    _cx_d.execute("DELETE FROM deliveries WHERE id = ?", (_del_id_deliveries,))
                    _cx_d.commit(); _cx_d.close()
                    st.session_state[f"_del_deliveries"] = None
                    st.success("✅ 삭제 완료!"); st.rerun()
                if _dc2.button("취소", use_container_width=True, key="_delcancel_deliveries"):
                    st.session_state[f"_del_deliveries"] = None; st.rerun()

            # ── 수정 인라인 폼 ─────────────────────────────────────
            if st.session_state.get(f"_edit_deliveries"):
                _edit_id_deliveries = st.session_state[f"_edit_deliveries"]
                try:
                    _cx_e = get_db()
                    _edit_row_deliveries = dict(_cx_e.execute(
                        "SELECT * FROM deliveries WHERE id=?", (_edit_id_deliveries,)
                    ).fetchone() or {})
                    _cx_e.close()
                except Exception:
                    _edit_row_deliveries = {}
                with st.expander(f"✏️ 출하 수정 — ID {_edit_id_deliveries}", expanded=True):
                    if not _edit_row_deliveries:
                        st.warning("데이터를 불러올 수 없습니다.")
                    else:
                        _skip_cols = {'id','created_at','updated_at'}
                        _edit_fields_deliveries = [c for c in _edit_row_deliveries if c not in _skip_cols]
                        _ncols = min(3, max(1, len(_edit_fields_deliveries)))
                        _ecols = st.columns(_ncols)
                        _new_vals_deliveries = {}
                        for _i, _fc in enumerate(_edit_fields_deliveries):
                            _cv = _edit_row_deliveries[_fc]
                            _ec = _ecols[_i % _ncols]
                            if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                _new_vals_deliveries[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_deliveries}_{_fc}_deliveries")
                            else:
                                _new_vals_deliveries[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_deliveries}_{_fc}_deliveries")
                        _s1, _s2 = st.columns(2)
                        if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_deliveries"):
                            _set_sql = ", ".join([f"{c}=?" for c in _new_vals_deliveries])
                            _set_params = list(_new_vals_deliveries.values()) + [_edit_id_deliveries]
                            _cx_s = get_db()
                            _cx_s.execute(f"UPDATE deliveries SET {_set_sql} WHERE id=?", _set_params)
                            _cx_s.commit(); _cx_s.close()
                            st.session_state[f"_edit_deliveries"] = None
                            st.success("✅ 수정 저장 완료!"); st.rerun()
                        if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_deliveries"):
                            st.session_state[f"_edit_deliveries"] = None; st.rerun()


# ══ 배송 추적 ══════════════════════════════════════════
with tabs["track"]:
    st.subheader("🔍 배송 추적")
    tn=st.text_input("운송장번호 검색")
    conn=get_db()
    if tn:
        df_tr=pd.read_sql_query("SELECT d.delivery_number AS 출하번호,d.tracking_number AS 운송장,d.carrier AS 운송사,d.item_name AS 품목,d.delivery_qty AS 수량,d.address AS 배송주소,d.delivery_date AS 출하일,d.actual_delivery AS 배달완료,d.status AS 상태,o.customer_name AS 고객 FROM deliveries d LEFT JOIN sales_orders o ON d.order_id=o.id WHERE d.tracking_number LIKE ?",conn,params=[f"%{tn}%"])
        if not df_tr.empty:
            r=df_tr.iloc[0]; c1,c2,c3=st.columns(3); c1.metric("상태",r['상태']); c2.metric("운송사",r['운송사'] or '-'); c3.metric("고객",r['고객'] or '-')
            st.dataframe(df_tr,use_container_width=True,hide_index=True)
            if r['상태']!='배송완료':
                if st.button("📦 배달완료 처리"):
                    conn2=get_db(); conn2.execute("UPDATE deliveries SET status='배송완료',actual_delivery=CURDATE() WHERE tracking_number=?",(tn,)); conn2.commit(); conn2.close(); st.success("완료!"); st.rerun()
        else: st.warning("조회 결과 없음")
    else:
        df_ad=pd.read_sql_query("SELECT d.delivery_number AS 출하번호,o.customer_name AS 고객,d.item_name AS 품목,d.carrier AS 운송사,d.tracking_number AS 운송장,d.status AS 상태,d.delivery_date AS 출하일 FROM deliveries d LEFT JOIN sales_orders o ON d.order_id=o.id WHERE d.status NOT IN ('배송완료') ORDER BY d.id DESC",conn)
        if not df_ad.empty: st.subheader("배송 중 현황"); st.dataframe(df_ad,use_container_width=True,hide_index=True)
        else: st.info("배송 중인 건 없음")
    conn.close()

# ══ 반품 ══════════════════════════════════════════
with tabs["ret"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("반품 등록")
        conn=get_db(); sr=conn.execute("SELECT id,order_number,item_name,quantity,unit_price FROM sales_orders WHERE status IN ('배송완료','배송중')").fetchall(); conn.close()
        sro={f"{o['order_number']}-{o['item_name']}":o for o in sr}
        with st.form("ret_f",clear_on_submit=True):
            rss=st.selectbox("반품 주문",list(sro.keys()) if sro else ["없음"]); rd=sro.get(rss)
            ir=st.text_input("품목명",value=rd['item_name'] if rd else "")
            a,b=st.columns(2); rq=a.number_input("반품수량",min_value=1,value=1); rsn=b.selectbox("반품사유",["고객변심","오배송","상품불량","파손","수량오류","기타"])
            rfa=st.number_input("환불금액",min_value=0.0,format="%.0f",value=float(rd['unit_price']*rq) if rd else 0.0)
            rstat=st.selectbox("처리상태",["반품접수","검수중","재고반영","폐기처리","환불완료"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not sro: st.error("반품 가능 주문 없음")
                else:
                    try:
                        conn=get_db(); conn.execute("INSERT INTO returns(return_number,order_id,item_name,quantity,reason,refund_amount,status) VALUES(?,?,?,?,?,?,?)",(gen_number("RET"),rd['id'],ir,rq,rsn,rfa,rstat))
                        if rstat=='재고반영': conn.execute("UPDATE inventory SET stock_qty=stock_qty+? WHERE item_name LIKE ?",(rq,f"%{ir}%"))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("반품 목록")
        conn=get_db(); df_r=pd.read_sql_query("SELECT r.return_number AS 반품번호,o.order_number AS 주문번호,r.item_name AS 품목,r.quantity AS 수량,r.reason AS 사유,r.refund_amount AS 환불금액,r.status AS 상태,r.created_at AS 등록일 FROM returns r LEFT JOIN sales_orders o ON r.order_id=o.id ORDER BY r.id DESC",conn); conn.close()
        if df_r.empty: st.info("없음")
        else:
            st.dataframe(df_r,use_container_width=True,hide_index=True)

            # ── 행 수정/삭제 버튼 (반품) ──────────────────────────
            if not df_r.empty if hasattr(df_r, 'empty') else df_r is not None:
                _row_opts_returns = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 품목명 FROM returns ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('품목명','')}"
                        _row_opts_returns[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_returns:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_returns = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_returns.keys()),
                        key="_rbsel_returns", label_visibility="collapsed"
                    )
                    _rb_id_returns = _row_opts_returns[_rb_sel_returns]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_returns"):
                        st.session_state[f"_edit_returns"] = _rb_id_returns
                        st.session_state[f"_del_returns"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_returns"):
                        st.session_state[f"_del_returns"]  = _rb_id_returns
                        st.session_state[f"_edit_returns"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_returns"):
                    _del_id_returns = st.session_state[f"_del_returns"]
                    st.warning(f"⚠️ ID **{_del_id_returns}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_returns"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM returns WHERE id = ?", (_del_id_returns,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_returns"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_returns"):
                        st.session_state[f"_del_returns"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_returns"):
                    _edit_id_returns = st.session_state[f"_edit_returns"]
                    try:
                        _cx_e = get_db()
                        _edit_row_returns = dict(_cx_e.execute(
                            "SELECT * FROM returns WHERE id=?", (_edit_id_returns,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_returns = {}
                    with st.expander(f"✏️ 반품 수정 — ID {_edit_id_returns}", expanded=True):
                        if not _edit_row_returns:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_returns = [c for c in _edit_row_returns if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_returns)))
                            _ecols = st.columns(_ncols)
                            _new_vals_returns = {}
                            for _i, _fc in enumerate(_edit_fields_returns):
                                _cv = _edit_row_returns[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_returns[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_returns}_{_fc}_returns")
                                else:
                                    _new_vals_returns[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_returns}_{_fc}_returns")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_returns"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_returns])
                                _set_params = list(_new_vals_returns.values()) + [_edit_id_returns]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE returns SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_returns"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_returns"):
                                st.session_state[f"_edit_returns"] = None; st.rerun()

            c1,c2=st.columns(2); c1.metric("반품건수",len(df_r)); c2.metric("환불합계",f"₩{df_r['환불금액'].sum():,.0f}",delta_color="inverse")

# ══ 출하 분석 BI ══════════════════════════════════════════
with tabs["bi_del"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        dc=conn.execute(f"SELECT COUNT(*) FROM deliveries WHERE created_at>='{bi_from}'").fetchone()[0]
        done=conn.execute(f"SELECT COUNT(*) FROM deliveries WHERE status='배송완료' AND created_at>='{bi_from}'").fetchone()[0]
        rc=conn.execute(f"SELECT COUNT(*) FROM returns WHERE created_at>='{bi_from}'").fetchone()[0]
        ra=conn.execute(f"SELECT COALESCE(SUM(refund_amount),0) FROM returns WHERE created_at>='{bi_from}'").fetchone()[0]
        c1,c2,c3,c4=st.columns(4); c1.metric("출하건수",f"{dc}건"); c2.metric("배송완료율",f"{round(done/dc*100,1) if dc else 0}%"); c3.metric("반품건수",f"{rc}건",delta_color="inverse"); c4.metric("환불금액",f"₩{ra:,.0f}",delta_color="inverse")
        col_l,col_r=st.columns(2)
        with col_l:
            df_ds=pd.read_sql_query("SELECT status AS 상태,COUNT(*) AS 건수 FROM deliveries GROUP BY status",conn)
            if not df_ds.empty: st.plotly_chart(px.pie(df_ds,names='상태',values='건수',title="출하 상태",hole=0.4).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        with col_r:
            df_rr=pd.read_sql_query(f"SELECT reason AS 사유,COUNT(*) AS 건수 FROM returns WHERE created_at>='{bi_from}' GROUP BY reason ORDER BY 건수 DESC",conn)
            if not df_rr.empty: st.plotly_chart(px.bar(df_rr,x='사유',y='건수',title="반품 사유",color='건수',color_continuous_scale='Reds').update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
            else: st.plotly_chart(_ef("반품 데이터 없음"),use_container_width=True)
        conn.close()

# ══ 청구서 ══════════════════════════════════════════
with tabs["inv"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("청구서 등록")
        conn=get_db(); si=conn.execute("SELECT id,order_number,customer_name,quantity,unit_price,discount_rate FROM sales_orders WHERE status NOT IN ('취소')").fetchall(); conn.close()
        sim={f"{o['order_number']}-{o['customer_name']}":o for o in si}
        with st.form("inv_f",clear_on_submit=True):
            iss=st.selectbox("판매주문 *",list(sim.keys()) if sim else ["없음"]); idata=sim.get(iss)
            aa=round(idata['quantity']*idata['unit_price']*(1-idata['discount_rate']/100),0) if idata else 0
            a,b=st.columns(2); amt=a.number_input("공급가액",min_value=0.0,format="%.0f",value=float(aa)); tax=b.number_input("세액",min_value=0.0,format="%.0f",value=round(aa*0.1,0))
            idt=st.date_input("발행일"); pt=st.selectbox("결제조건",["현금","30일","60일","90일"])
            ddt=idt+timedelta(days={"현금":0,"30일":30,"60일":60,"90일":90}[pt]); st.info(f"결제기한: {ddt}")
            paid=st.checkbox("즉시 수금")
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not sim: st.error("주문 없음")
                else:
                    try:
                        conn=get_db(); conn.execute("INSERT INTO invoices(invoice_number,order_id,customer_name,amount,tax_amount,issue_date,due_date,paid,paid_at) VALUES(?,?,?,?,?,?,?,?,?)",(gen_number("INV"),idata['id'],idata['customer_name'],amt,tax,str(idt),str(ddt),1 if paid else 0,str(idt) if paid else None)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("청구서 목록")
        conn=get_db(); df_i=pd.read_sql_query("SELECT invoice_number AS 청구번호,customer_name AS 고객,amount AS 공급가액,tax_amount AS 세액,ROUND(amount+tax_amount,0) AS 합계,issue_date AS 발행일,due_date AS 결제기한,CASE paid WHEN 1 THEN '✅완료' ELSE '🔴미결' END AS 결제상태 FROM invoices ORDER BY id DESC",conn); conn.close()
        if df_i.empty: st.info("없음")
        else:
            st.dataframe(df_i,use_container_width=True,hide_index=True)

            # ── 행 수정/삭제 버튼 (청구서) ──────────────────────────
            if not df_i.empty if hasattr(df_i, 'empty') else df_i is not None:
                _row_opts_invoices = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 고객명 FROM invoices ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('고객명','')}"
                        _row_opts_invoices[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_invoices:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_invoices = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_invoices.keys()),
                        key="_rbsel_invoices", label_visibility="collapsed"
                    )
                    _rb_id_invoices = _row_opts_invoices[_rb_sel_invoices]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_invoices"):
                        st.session_state[f"_edit_invoices"] = _rb_id_invoices
                        st.session_state[f"_del_invoices"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_invoices"):
                        st.session_state[f"_del_invoices"]  = _rb_id_invoices
                        st.session_state[f"_edit_invoices"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_invoices"):
                    _del_id_invoices = st.session_state[f"_del_invoices"]
                    st.warning(f"⚠️ ID **{_del_id_invoices}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_invoices"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM invoices WHERE id = ?", (_del_id_invoices,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_invoices"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_invoices"):
                        st.session_state[f"_del_invoices"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_invoices"):
                    _edit_id_invoices = st.session_state[f"_edit_invoices"]
                    try:
                        _cx_e = get_db()
                        _edit_row_invoices = dict(_cx_e.execute(
                            "SELECT * FROM invoices WHERE id=?", (_edit_id_invoices,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_invoices = {}
                    with st.expander(f"✏️ 청구서 수정 — ID {_edit_id_invoices}", expanded=True):
                        if not _edit_row_invoices:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_invoices = [c for c in _edit_row_invoices if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_invoices)))
                            _ecols = st.columns(_ncols)
                            _new_vals_invoices = {}
                            for _i, _fc in enumerate(_edit_fields_invoices):
                                _cv = _edit_row_invoices[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_invoices[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_invoices}_{_fc}_invoices")
                                else:
                                    _new_vals_invoices[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_invoices}_{_fc}_invoices")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_invoices"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_invoices])
                                _set_params = list(_new_vals_invoices.values()) + [_edit_id_invoices]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE invoices SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_invoices"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_invoices"):
                                st.session_state[f"_edit_invoices"] = None; st.rerun()

            c1,c2=st.columns(2); c1.metric("미결합계",f"₩{df_i[df_i['결제상태']=='🔴미결']['합계'].sum():,.0f}",delta_color="inverse"); c2.metric("총건수",len(df_i))

# ══ 매출 세금계산서 ══════════════════════════════════════════
with tabs["sti"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("매출 세금계산서 발행")
        conn=get_db(); pi=conn.execute("SELECT id,invoice_number,customer_name,amount FROM invoices WHERE paid=0").fetchall(); conn.close()
        pio={f"{i['invoice_number']}-{i['customer_name']}":i for i in pi}
        with st.form("sti_f",clear_on_submit=True):
            pis=st.selectbox("청구서 *",list(pio.keys()) if pio else ["없음"]); pid=pio.get(pis)
            tin=st.text_input("세금계산서 번호")
            a,b=st.columns(2); sa=a.number_input("공급가액",min_value=0.0,format="%.0f",value=float(pid['amount']) if pid else 0.0); ta=b.number_input("세액",min_value=0.0,format="%.0f",value=round(float(pid['amount'])*0.1,0) if pid else 0.0)
            st.info(f"합계: ₩{sa+ta:,.0f}")
            c,d=st.columns(2); id2=c.date_input("발행일"); pt2=d.selectbox("결제조건",["현금","30일","60일","90일"])
            dd2=id2+timedelta(days={"현금":0,"30일":30,"60일":60,"90일":90}[pt2]); pm=st.selectbox("결제방법",["계좌이체","현금","카드","어음"])
            if st.form_submit_button("✅ 발행",use_container_width=True):
                if not pio: st.error("청구서 없음")
                else:
                    try:
                        conn=get_db(); conn.execute("INSERT INTO sales_tax_invoices(sti_number,order_id,customer_name,tax_invoice_no,supply_amount,tax_amount,total_amount,issue_date,due_date,payment_terms,payment_method,payment_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(gen_number("STI"),pid['id'] if pid else None,pid['customer_name'] if pid else "",tin,sa,ta,sa+ta,str(id2),str(dd2),pt2,pm,'미수금')); conn.commit(); conn.close(); st.success("발행!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("매출 세금계산서 목록")
        conn=get_db(); df_s=pd.read_sql_query("SELECT sti_number AS 번호,customer_name AS 고객,tax_invoice_no AS 계산서번호,supply_amount AS 공급가,tax_amount AS 세액,total_amount AS 합계,issue_date AS 발행일,due_date AS 만기일,payment_status AS 수금상태 FROM sales_tax_invoices ORDER BY id DESC",conn); conn.close()
        if df_s.empty: st.info("없음")
        else:
            today_s=datetime.now().strftime("%Y-%m-%d")
            def sc(r): return ['background-color:#d1fae5']*len(r) if r['수금상태']=='수금완료' else (['background-color:#fee2e2']*len(r) if str(r['만기일'])<today_s else ['']*len(r))
            st.dataframe(df_s.style.apply(sc,axis=1),use_container_width=True,hide_index=True)

            # ── 행 수정/삭제 버튼 (매출세금계산서) ──────────────────────────
            if not df_s.empty if hasattr(df_s, 'empty') else df_s is not None:
                _row_opts_sales_tax_invoices = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 고객명 FROM sales_tax_invoices ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('고객명','')}"
                        _row_opts_sales_tax_invoices[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_sales_tax_invoices:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_sales_tax_invoices = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_sales_tax_invoices.keys()),
                        key="_rbsel_sales_tax_invoices", label_visibility="collapsed"
                    )
                    _rb_id_sales_tax_invoices = _row_opts_sales_tax_invoices[_rb_sel_sales_tax_invoices]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_sales_tax_invoices"):
                        st.session_state[f"_edit_sales_tax_invoices"] = _rb_id_sales_tax_invoices
                        st.session_state[f"_del_sales_tax_invoices"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_sales_tax_invoices"):
                        st.session_state[f"_del_sales_tax_invoices"]  = _rb_id_sales_tax_invoices
                        st.session_state[f"_edit_sales_tax_invoices"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_sales_tax_invoices"):
                    _del_id_sales_tax_invoices = st.session_state[f"_del_sales_tax_invoices"]
                    st.warning(f"⚠️ ID **{_del_id_sales_tax_invoices}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_sales_tax_invoices"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM sales_tax_invoices WHERE id = ?", (_del_id_sales_tax_invoices,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_sales_tax_invoices"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_sales_tax_invoices"):
                        st.session_state[f"_del_sales_tax_invoices"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_sales_tax_invoices"):
                    _edit_id_sales_tax_invoices = st.session_state[f"_edit_sales_tax_invoices"]
                    try:
                        _cx_e = get_db()
                        _edit_row_sales_tax_invoices = dict(_cx_e.execute(
                            "SELECT * FROM sales_tax_invoices WHERE id=?", (_edit_id_sales_tax_invoices,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_sales_tax_invoices = {}
                    with st.expander(f"✏️ 매출세금계산서 수정 — ID {_edit_id_sales_tax_invoices}", expanded=True):
                        if not _edit_row_sales_tax_invoices:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_sales_tax_invoices = [c for c in _edit_row_sales_tax_invoices if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_sales_tax_invoices)))
                            _ecols = st.columns(_ncols)
                            _new_vals_sales_tax_invoices = {}
                            for _i, _fc in enumerate(_edit_fields_sales_tax_invoices):
                                _cv = _edit_row_sales_tax_invoices[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_sales_tax_invoices[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_sales_tax_invoices}_{_fc}_sales_tax_invoices")
                                else:
                                    _new_vals_sales_tax_invoices[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_sales_tax_invoices}_{_fc}_sales_tax_invoices")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_sales_tax_invoices"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_sales_tax_invoices])
                                _set_params = list(_new_vals_sales_tax_invoices.values()) + [_edit_id_sales_tax_invoices]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE sales_tax_invoices SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_sales_tax_invoices"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_sales_tax_invoices"):
                                st.session_state[f"_edit_sales_tax_invoices"] = None; st.rerun()


# ══ 수금 관리 ══════════════════════════════════════════
with tabs["ar"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("💳 수금 처리")
        conn=get_db(); ps=conn.execute("SELECT id,sti_number,customer_name,total_amount FROM sales_tax_invoices WHERE payment_status='미수금'").fetchall(); conn.close()
        pso={f"{s['sti_number']}-{s['customer_name']} ₩{s['total_amount']:,.0f}":s for s in ps}
        with st.form("ar_f",clear_on_submit=True):
            if not pso: st.info("미수금 없음"); st.form_submit_button("등록",disabled=True)
            else:
                pss=st.selectbox("미수금 세금계산서",list(pso.keys())); psd=pso[pss]
                ra2=st.number_input("수금금액",min_value=0.0,format="%.0f",value=float(psd['total_amount'])); rd2=st.date_input("수금일"); pm2=st.selectbox("수금방법",["계좌이체","현금","카드","어음"]); br=st.text_input("은행 참조번호"); nar=st.text_area("비고",height=40)
                if st.form_submit_button("✅ 수금 처리",use_container_width=True):
                    try:
                        conn=get_db(); conn.execute("INSERT INTO ar_receipts(receipt_number,sti_id,customer_name,amount,receipt_amount,receipt_date,payment_method,bank_ref,note) VALUES(?,?,?,?,?,?,?,?,?)",
    (gen_number("RCP"),psd['id'],psd['customer_name'],psd['total_amount'],ra2,str(rd2),pm2,br,nar))
                        conn.execute("UPDATE sales_tax_invoices SET payment_status='수금완료',paid_at=? WHERE id=?",(str(rd2),psd['id'])); conn.commit(); conn.close(); st.success("수금 완료!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("수금 이력")
        conn=get_db(); df_ar=pd.read_sql_query("SELECT receipt_number AS 수금번호,customer_name AS 고객,receipt_amount AS 수금금액,receipt_date AS 수금일,payment_method AS 방법,bank_ref AS 참조번호 FROM ar_receipts ORDER BY id DESC",conn); conn.close()
        if df_ar.empty: st.info("없음")
        else: st.dataframe(df_ar,use_container_width=True,hide_index=True)

        # ── 행 수정/삭제 버튼 (수금) ──────────────────────────
        if not df_ar.empty if hasattr(df_ar, 'empty') else df_ar is not None:
            _row_opts_ar_receipts = {}
            try:
                _cx_opt = get_db()
                _opt_rs = [dict(r) for r in _cx_opt.execute(
                    "SELECT id, 고객명 FROM ar_receipts ORDER BY id DESC LIMIT 300"
                ).fetchall()]
                _cx_opt.close()
                for _r in _opt_rs:
                    _k = f"{_r['id']} | {_r.get('고객명','')}"
                    _row_opts_ar_receipts[_k] = _r['id']
            except Exception:
                pass

            if _row_opts_ar_receipts:
                _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                _rb_sel_ar_receipts = _rb_sel_col.selectbox(
                    "행 선택", list(_row_opts_ar_receipts.keys()),
                    key="_rbsel_ar_receipts", label_visibility="collapsed"
                )
                _rb_id_ar_receipts = _row_opts_ar_receipts[_rb_sel_ar_receipts]

                if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_ar_receipts"):
                    st.session_state[f"_edit_ar_receipts"] = _rb_id_ar_receipts
                    st.session_state[f"_del_ar_receipts"]  = None

                if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_ar_receipts"):
                    st.session_state[f"_del_ar_receipts"]  = _rb_id_ar_receipts
                    st.session_state[f"_edit_ar_receipts"] = None

            # ── 삭제 확인 ──────────────────────────────────────────
            if st.session_state.get(f"_del_ar_receipts"):
                _del_id_ar_receipts = st.session_state[f"_del_ar_receipts"]
                st.warning(f"⚠️ ID **{_del_id_ar_receipts}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                _dc1, _dc2 = st.columns(2)
                if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_ar_receipts"):
                    _cx_d = get_db()
                    _cx_d.execute("DELETE FROM ar_receipts WHERE id = ?", (_del_id_ar_receipts,))
                    _cx_d.commit(); _cx_d.close()
                    st.session_state[f"_del_ar_receipts"] = None
                    st.success("✅ 삭제 완료!"); st.rerun()
                if _dc2.button("취소", use_container_width=True, key="_delcancel_ar_receipts"):
                    st.session_state[f"_del_ar_receipts"] = None; st.rerun()

            # ── 수정 인라인 폼 ─────────────────────────────────────
            if st.session_state.get(f"_edit_ar_receipts"):
                _edit_id_ar_receipts = st.session_state[f"_edit_ar_receipts"]
                try:
                    _cx_e = get_db()
                    _edit_row_ar_receipts = dict(_cx_e.execute(
                        "SELECT * FROM ar_receipts WHERE id=?", (_edit_id_ar_receipts,)
                    ).fetchone() or {})
                    _cx_e.close()
                except Exception:
                    _edit_row_ar_receipts = {}
                with st.expander(f"✏️ 수금 수정 — ID {_edit_id_ar_receipts}", expanded=True):
                    if not _edit_row_ar_receipts:
                        st.warning("데이터를 불러올 수 없습니다.")
                    else:
                        _skip_cols = {'id','created_at','updated_at'}
                        _edit_fields_ar_receipts = [c for c in _edit_row_ar_receipts if c not in _skip_cols]
                        _ncols = min(3, max(1, len(_edit_fields_ar_receipts)))
                        _ecols = st.columns(_ncols)
                        _new_vals_ar_receipts = {}
                        for _i, _fc in enumerate(_edit_fields_ar_receipts):
                            _cv = _edit_row_ar_receipts[_fc]
                            _ec = _ecols[_i % _ncols]
                            if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                _new_vals_ar_receipts[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_ar_receipts}_{_fc}_ar_receipts")
                            else:
                                _new_vals_ar_receipts[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_ar_receipts}_{_fc}_ar_receipts")
                        _s1, _s2 = st.columns(2)
                        if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_ar_receipts"):
                            _set_sql = ", ".join([f"{c}=?" for c in _new_vals_ar_receipts])
                            _set_params = list(_new_vals_ar_receipts.values()) + [_edit_id_ar_receipts]
                            _cx_s = get_db()
                            _cx_s.execute(f"UPDATE ar_receipts SET {_set_sql} WHERE id=?", _set_params)
                            _cx_s.commit(); _cx_s.close()
                            st.session_state[f"_edit_ar_receipts"] = None
                            st.success("✅ 수정 저장 완료!"); st.rerun()
                        if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_ar_receipts"):
                            st.session_state[f"_edit_ar_receipts"] = None; st.rerun()


# ══ 채권 Aging ══════════════════════════════════════════
with tabs["aging"]:
    st.subheader("📋 매출채권 Aging 분석")
    conn=get_db(); df_ag=pd.read_sql_query("SELECT customer_name AS 고객,sti_number AS 계산서,total_amount AS 금액,due_date AS 만기일,CAST(DATEDIFF(CURDATE(),due_date) AS SIGNED) AS 연체일수 FROM sales_tax_invoices WHERE payment_status='미수금' ORDER BY due_date",conn); conn.close()
    if df_ag.empty: st.success("✅ 미수금 없음")
    else:
        def ag_b(d): return "미도래" if d<=0 else ("1~30일" if d<=30 else ("31~60일" if d<=60 else ("61~90일" if d<=90 else "90일 초과")))
        df_ag['구간']=df_ag['연체일수'].apply(ag_b)
        tv=df_ag['금액'].sum(); ov=df_ag[df_ag['연체일수']>0]['금액'].sum()
        c1,c2,c3=st.columns(3); c1.metric("총 미수금",f"₩{tv:,.0f}"); c2.metric("연체 금액",f"₩{ov:,.0f}",delta_color="inverse"); c3.metric("연체율",f"{ov/tv*100:.1f}%" if tv else "0%",delta_color="inverse")
        if HAS_PL:
            col_l,col_r=st.columns(2)
            ags=df_ag.groupby('구간')['금액'].sum().reset_index()
            cm2={"미도래":"#3b82f6","1~30일":"#22c55e","31~60일":"#eab308","61~90일":"#f97316","90일 초과":"#ef4444"}
            with col_l: st.plotly_chart(px.bar(ags,x='구간',y='금액',color='구간',color_discrete_map=cm2,title="Aging 구간별 미수금").update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
            with col_r:
                ca=df_ag.groupby('고객')['금액'].sum().reset_index().sort_values('금액',ascending=False).head(8)
                st.plotly_chart(px.bar(ca,y='고객',x='금액',orientation='h',color='금액',color_continuous_scale='Reds',title="고객별 미수금 TOP8").update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
        st.dataframe(df_ag,use_container_width=True,hide_index=True)

# ══ 청구 분석 BI ══════════════════════════════════════════
with tabs["bi_ar"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        ti=conn.execute(f"SELECT COALESCE(SUM(amount+tax_amount),0) FROM invoices WHERE issue_date>='{bi_from}'").fetchone()[0]
        pi2=conn.execute(f"SELECT COALESCE(SUM(amount+tax_amount),0) FROM invoices WHERE paid=1 AND issue_date>='{bi_from}'").fetchone()[0]
        st2=conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM sales_tax_invoices WHERE payment_status='미수금'").fetchone()[0]
        c1,c2,c3=st.columns(3); c1.metric("청구합계",f"₩{ti:,.0f}"); c2.metric("수금률",f"{pi2/ti*100:.1f}%" if ti else "0%"); c3.metric("미수금",f"₩{st2:,.0f}",delta_color="inverse")
        df_it=pd.read_sql_query(f"SELECT DATE_FORMAT(issue_date,'%%Y-%%m') AS 월,ROUND(SUM(amount+tax_amount),0) AS 청구금액,ROUND(SUM(CASE paid WHEN 1 THEN amount+tax_amount ELSE 0 END),0) AS 수금금액 FROM invoices WHERE issue_date>='{bi_from}' GROUP BY DATE_FORMAT(issue_date,'%%Y-%%m') ORDER BY 월",conn)
        if not df_it.empty:
            fig=go.Figure(); fig.add_trace(go.Bar(x=df_it['월'],y=df_it['청구금액'],name='청구',marker_color='#3b82f6')); fig.add_trace(go.Bar(x=df_it['월'],y=df_it['수금금액'],name='수금',marker_color='#10b981'))
            fig.update_layout(barmode='group',title="월별 청구·수금",height=280,margin=dict(l=0,r=0,t=40,b=0),legend=dict(orientation="h",y=1.1)); st.plotly_chart(fig,use_container_width=True)
        conn.close()

# ══ 매출 추이 ══════════════════════════════════════════
with tabs["bi_sales"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        tr=conn.execute(f"SELECT COALESCE(SUM(quantity*unit_price*(1-discount_rate/100)),0) FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}'").fetchone()[0]
        ret2=conn.execute(f"SELECT COALESCE(SUM(refund_amount),0) FROM returns WHERE created_at>='{bi_from}'").fetchone()[0]
        bl=conn.execute(f"SELECT COALESCE(SUM(amount+tax_amount),0) FROM invoices WHERE issue_date>='{bi_from}'").fetchone()[0]
        pb=conn.execute(f"SELECT COALESCE(SUM(amount+tax_amount),0) FROM invoices WHERE paid=1 AND issue_date>='{bi_from}'").fetchone()[0]
        c1,c2,c3,c4=st.columns(4); c1.metric("수주금액",f"₩{tr:,.0f}"); c2.metric("반품차감",f"₩{ret2:,.0f}",delta_color="inverse"); c3.metric("순매출",f"₩{tr-ret2:,.0f}"); c4.metric("수금률",f"{pb/bl*100:.1f}%" if bl else "0%")
        df_st2=pd.read_sql_query(f"SELECT DATE_FORMAT(ordered_at,'%%Y-%%m') AS 월,ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 수주금액 FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}' GROUP BY DATE_FORMAT(ordered_at,'%%Y-%%m') ORDER BY 월",conn)
        if not df_st2.empty: st.plotly_chart(px.area(df_st2,x='월',y='수주금액',title=f"월별 매출 추이({bp})",color_discrete_sequence=['#8b5cf6']).update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()

# ══ 고객·품목 분석 ══════════════════════════════════════════
with tabs["bi_item"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        col_l,col_r=st.columns(2)
        with col_l:
            df_cr=pd.read_sql_query(f"SELECT customer_name AS 고객,ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 매출 FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}' GROUP BY customer_name ORDER BY 매출 DESC LIMIT 10",conn)
            if not df_cr.empty: st.plotly_chart(px.bar(df_cr,y='고객',x='매출',orientation='h',color='매출',color_continuous_scale='Purples',title="고객별 매출 TOP10").update_layout(height=300,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
        with col_r:
            df_ir=pd.read_sql_query(f"SELECT item_name AS 품목,ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 매출,SUM(quantity) AS 수량 FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}' GROUP BY item_name ORDER BY 매출 DESC LIMIT 10",conn)
            if not df_ir.empty: st.plotly_chart(px.treemap(df_ir,path=['품목'],values='매출',color='수량',color_continuous_scale='Blues',title="품목별 트리맵").update_layout(height=300,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()

# ══ 반품 분석 ══════════════════════════════════════════
with tabs["bi_ret"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        col_l,col_r=st.columns(2)
        with col_l:
            df_rt=pd.read_sql_query(f"SELECT DATE_FORMAT(created_at,'%%Y-%%m') AS 월,COUNT(*) AS 건수 FROM returns WHERE created_at>='{bi_from}' GROUP BY DATE_FORMAT(created_at,'%%Y-%%m') ORDER BY 월",conn)
            st.plotly_chart((px.bar(df_rt,x='월',y='건수',title="월별 반품",color_discrete_sequence=['#ef4444']).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)) if not df_rt.empty else _ef("반품 없음")),use_container_width=True)
        with col_r:
            df_rr2=pd.read_sql_query(f"SELECT reason AS 사유,COUNT(*) AS 건수 FROM returns WHERE created_at>='{bi_from}' GROUP BY reason ORDER BY 건수 DESC",conn)  # noqa
            st.plotly_chart((px.pie(df_rr2,names='사유',values='건수',title="반품 사유").update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)) if not df_rr2.empty else _ef()),use_container_width=True)
        conn.close()

# ══ 수익성 분석 ══════════════════════════════════════════
with tabs["bi_profit"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        df_pf=pd.read_sql_query(f"SELECT platform AS 채널,COUNT(*) AS 건수,ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 매출,ROUND(AVG(discount_rate),1) AS 평균할인율 FROM sales_orders WHERE status!='취소' AND ordered_at>='{bi_from}' GROUP BY platform ORDER BY 매출 DESC",conn)
        if not df_pf.empty:
            col_l,col_r=st.columns(2)
            with col_l: st.plotly_chart(px.bar(df_pf,x='채널',y='매출',color='평균할인율',color_continuous_scale='RdYlGn_r',title="채널별 매출·할인율").update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
            with col_r: st.plotly_chart(px.scatter(df_pf,x='건수',y='매출',size='건수',color='채널',text='채널',title="건수 vs 매출").update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
            st.dataframe(df_pf,use_container_width=True,hide_index=True)
        conn.close()

# ══ SO → PP 생산 연동 ══════════════════════════════════════════
with tabs["so_pp"]:
    st.subheader("🔗 판매주문 → 생산계획 연동")
    st.caption("주문접수 SO에서 PP 생산계획을 자동 생성합니다")
    conn=get_db()
    # 아직 생산계획 없는 SO 목록
    df_so_link=pd.read_sql_query("""
        SELECT s.id, s.order_number AS SO번호, s.customer_name AS 고객,
               s.item_name AS 품목, s.quantity AS 수량,
               s.requested_delivery AS 납기요청, s.status AS 상태
        FROM sales_orders s
        WHERE s.status IN ('주문접수','신용검토중','생산/조달중')
          AND NOT EXISTS (
              SELECT 1 FROM production_plans p
              WHERE p.product_name=s.item_name
                AND p.status NOT IN ('취소')
                AND p.created_at >= s.ordered_at
          )
        ORDER BY s.id DESC""", conn)

    if df_so_link.empty:
        st.success("✅ 모든 주문에 생산계획이 연결되어 있습니다")
    else:
        st.warning(f"⚠️ 생산계획 미연결 SO: {len(df_so_link)}건")
        st.dataframe(df_so_link.drop(columns=['id']), use_container_width=True, hide_index=True)

        # ── 행 수정/삭제 버튼 (production_plans) ──────────────────────────
        if not df_so_link.empty if hasattr(df_so_link, 'empty') else df_so_link is not None:
            _row_opts_production_plans = {}
            try:
                _cx_opt = get_db()
                _opt_rs = [dict(r) for r in _cx_opt.execute(
                    "SELECT id, * FROM production_plans ORDER BY id DESC LIMIT 300"
                ).fetchall()]
                _cx_opt.close()
                for _r in _opt_rs:
                    _k = f"{_r['id']} | {_r.get('품목명','')}"
                    _row_opts_production_plans[_k] = _r['id']
            except Exception:
                pass

            if _row_opts_production_plans:
                _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                _rb_sel_production_plans = _rb_sel_col.selectbox(
                    "행 선택", list(_row_opts_production_plans.keys()),
                    key="_rbsel_production_plans", label_visibility="collapsed"
                )
                _rb_id_production_plans = _row_opts_production_plans[_rb_sel_production_plans]

                if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_production_plans"):
                    st.session_state[f"_edit_production_plans"] = _rb_id_production_plans
                    st.session_state[f"_del_production_plans"]  = None

                if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_production_plans"):
                    st.session_state[f"_del_production_plans"]  = _rb_id_production_plans
                    st.session_state[f"_edit_production_plans"] = None

            # ── 삭제 확인 ──────────────────────────────────────────
            if st.session_state.get(f"_del_production_plans"):
                _del_id_production_plans = st.session_state[f"_del_production_plans"]
                st.warning(f"⚠️ ID **{_del_id_production_plans}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                _dc1, _dc2 = st.columns(2)
                if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_production_plans"):
                    _cx_d = get_db()
                    _cx_d.execute("DELETE FROM production_plans WHERE id = ?", (_del_id_production_plans,))
                    _cx_d.commit(); _cx_d.close()
                    st.session_state[f"_del_production_plans"] = None
                    st.success("✅ 삭제 완료!"); st.rerun()
                if _dc2.button("취소", use_container_width=True, key="_delcancel_production_plans"):
                    st.session_state[f"_del_production_plans"] = None; st.rerun()

            # ── 수정 인라인 폼 ─────────────────────────────────────
            if st.session_state.get(f"_edit_production_plans"):
                _edit_id_production_plans = st.session_state[f"_edit_production_plans"]
                try:
                    _cx_e = get_db()
                    _edit_row_production_plans = dict(_cx_e.execute(
                        "SELECT * FROM production_plans WHERE id=?", (_edit_id_production_plans,)
                    ).fetchone() or {})
                    _cx_e.close()
                except Exception:
                    _edit_row_production_plans = {}
                with st.expander(f"✏️ 정보 수정 — ID {_edit_id_production_plans}", expanded=True):
                    if not _edit_row_production_plans:
                        st.warning("데이터를 불러올 수 없습니다.")
                    else:
                        _skip_cols = {'id','created_at','updated_at','ordered_at'}
                        _edit_fields_production_plans = [c for c in _edit_row_production_plans if c not in _skip_cols]
                        _ncols = min(3, max(1, len(_edit_fields_production_plans)))
                        _ecols = st.columns(_ncols)
                        _new_vals_production_plans = {}
                        for _i, _fc in enumerate(_edit_fields_production_plans):
                            _cv = _edit_row_production_plans[_fc]
                            _ec = _ecols[_i % _ncols]
                            if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                _new_vals_production_plans[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_production_plans}_{_fc}_production_plans")
                            else:
                                _new_vals_production_plans[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_production_plans}_{_fc}_production_plans")
                        _s1, _s2 = st.columns(2)
                        if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_production_plans"):
                            _set_sql = ", ".join([f"{c}=?" for c in _new_vals_production_plans])
                            _set_params = list(_new_vals_production_plans.values()) + [_edit_id_production_plans]
                            _cx_s = get_db()
                            _cx_s.execute(f"UPDATE production_plans SET {_set_sql} WHERE id=?", _set_params)
                            _cx_s.commit(); _cx_s.close()
                            st.session_state[f"_edit_production_plans"] = None
                            st.success("✅ 수정 저장 완료!"); st.rerun()
                        if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_production_plans"):
                            st.session_state[f"_edit_production_plans"] = None; st.rerun()

        st.divider()
        st.subheader("생산계획 자동 생성")
        so_map={f"{r['SO번호']}-{r['고객']}/{r['품목']}":r for _,r in df_so_link.iterrows()}
        sel_so=st.selectbox("SO 선택", list(so_map.keys()))
        sd=so_map[sel_so]
        col1,col2=st.columns(2)
        wcs_link=[r[0] for r in conn.execute("SELECT wc_name FROM work_centers WHERE status='가동'").fetchall()]
        sel_wc_l=col1.selectbox("작업장",wcs_link if wcs_link else ["미지정"])
        plan_start=col2.date_input("생산시작일",value=date.today())
        plan_end=st.date_input("생산완료예정",value=date.today()+timedelta(days=7))
        conn.close()
        if st.button("🔗 생산계획 생성",use_container_width=True,type="primary"):
            try:
                conn=get_db()
                pnum=gen_number("PP")
                conn.execute("""INSERT INTO production_plans(plan_number,product_name,planned_qty,start_date,end_date,work_center,status)
                    VALUES(?,?,?,?,?,?,?)""",
                    (pnum,sd['품목'],sd['수량'],str(plan_start),str(plan_end),sel_wc_l,'확정'))
                conn.execute("UPDATE sales_orders SET status='생산/조달중' WHERE id=?",(sd['id'],))
                conn.commit(); conn.close()
                st.success(f"✅ 생산계획 {pnum} 생성! SO 상태 → 생산/조달중")
                st.rerun()
            except Exception as e: st.error(f"오류:{e}")

    # 연동 현황
    st.divider()
    st.subheader("📋 SO ↔ PP 연동 현황")
    conn=get_db()
    df_link_status=pd.read_sql_query("""
        SELECT s.order_number AS SO번호, s.customer_name AS 고객,
               s.item_name AS 품목, s.quantity AS 주문수량,
               s.status AS SO상태,
               p.plan_number AS 생산계획번호,
               p.planned_qty AS 계획수량,
               p.status AS 생산상태,
               p.start_date AS 생산시작,
               p.end_date AS 생산완료예정
        FROM sales_orders s
        LEFT JOIN production_plans p ON p.product_name=s.item_name
            AND p.status NOT IN ('취소')
        WHERE s.status NOT IN ('취소')
        ORDER BY s.id DESC LIMIT 30""", conn)
    conn.close()
    if not df_link_status.empty:
        st.dataframe(df_link_status, use_container_width=True, hide_index=True)


# ══ 부분출하 관리 ══════════════════════════════════════════
with tabs["partial"]:
    def _acd(t,c,ct="TEXT"):
        try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
        except: pass
    _acd("deliveries","partial_seq","INTEGER DEFAULT 1")
    _acd("sales_orders","shipped_qty","INTEGER DEFAULT 0")

    st.subheader("📦 부분출하 관리")
    st.caption("SO 1건을 여러 번에 나누어 출하 — 잔량 자동 추적")
    conn=get_db()
    df_so_part=pd.read_sql_query("""
        SELECT s.id, s.order_number AS SO번호, s.customer_name AS 고객,
               s.item_name AS 품목, s.quantity AS 주문수량,
               COALESCE(s.shipped_qty,0) AS 기출하수량,
               s.quantity - COALESCE(s.shipped_qty,0) AS 잔량,
               s.status AS 상태
        FROM sales_orders s
        WHERE s.quantity > COALESCE(s.shipped_qty,0)
          AND s.status NOT IN ('취소','배송완료')
        ORDER BY s.id DESC""", conn)

    if df_so_part.empty:
        st.info("부분출하 가능한 주문 없음")
    else:
        c1,c2,c3=st.columns(3)
        c1.metric("부분출하 대상",f"{len(df_so_part)}건")
        c2.metric("미출하 수량 합계",f"{df_so_part['잔량'].sum():,}개")

        st.dataframe(df_so_part.drop(columns=['id']),use_container_width=True,hide_index=True)
        st.divider()

        so_map_p={f"{r['SO번호']}-{r['고객']}/{r['품목']} (잔량:{r['잔량']})":r for _,r in df_so_part.iterrows()}
        sel_p=st.selectbox("출하할 주문",list(so_map_p.keys()))
        pd_=so_map_p[sel_p]

        col1,col2,col3=st.columns(3)
        ship_qty=col1.number_input("이번 출하수량",min_value=1,max_value=int(pd_['잔량']),value=int(pd_['잔량']))
        carrier_p=col2.text_input("운송사")
        track_p=col3.text_input("운송장번호")
        ship_date=st.date_input("출하일",value=date.today())
        conn.close()

        if st.button("✅ 부분출하 등록",use_container_width=True,type="primary"):
            try:
                conn=get_db()
                seq=conn.execute("SELECT COUNT(*)+1 FROM deliveries WHERE order_id=?",(pd_['id'],)).fetchone()[0]
                dnum=gen_number("DL")
                conn.execute("""INSERT INTO deliveries(delivery_number,order_id,item_name,delivery_qty,carrier,tracking_number,delivery_date,status,partial_seq)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (dnum,pd_['id'],pd_['품목'],ship_qty,carrier_p,track_p,str(ship_date),'출하완료',seq))
                new_shipped=pd_['기출하수량']+ship_qty
                new_status='배송완료' if new_shipped>=pd_['주문수량'] else '배송중'
                conn.execute("UPDATE sales_orders SET shipped_qty=?,status=? WHERE id=?",
                    (new_shipped,new_status,pd_['id']))
                conn.commit(); conn.close()
                st.success(f"✅ {seq}차 출하 등록! (누적:{new_shipped}/{pd_['주문수량']})")
                if new_status=='배송완료': st.info("🎉 전량 출하 완료!")
                st.rerun()
            except Exception as e: st.error(f"오류:{e}")

    # 부분출하 이력
    st.divider()
    st.subheader("부분출하 이력")
    conn=get_db()
    df_ph=pd.read_sql_query("""
        SELECT d.delivery_number AS 출하번호,
               o.order_number AS SO번호, o.customer_name AS 고객,
               d.item_name AS 품목,
               d.partial_seq AS 차수,
               d.delivery_qty AS 출하수량,
               o.quantity AS 주문수량,
               d.carrier AS 운송사, d.tracking_number AS 운송장,
               d.delivery_date AS 출하일, d.status AS 상태
        FROM deliveries d
        JOIN sales_orders o ON d.order_id=o.id
        WHERE d.partial_seq IS NOT NULL
        ORDER BY d.id DESC LIMIT 50""", conn)
    conn.close()
    if not df_ph.empty:
        st.dataframe(df_ph,use_container_width=True,hide_index=True)


# ══ 포장명세서 ══════════════════════════════════════════
with tabs["packing"]:
    def _acd2(t,c,ct="TEXT"):
        try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
        except: pass
    # MySQL: packing_lists 테이블은 db.py init_db()에서 이미 생성됨

    st.subheader("📦 포장명세서 (Packing List)")
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("포장명세서 등록")
        conn=get_db()
        delis=[r for r in conn.execute("SELECT id,delivery_number,item_name FROM deliveries ORDER BY id DESC LIMIT 50").fetchall()]
        conn.close()
        dmap={f"{d['delivery_number']}-{d['item_name']}":d for d in delis}
        with st.form("pl_f",clear_on_submit=True):
            d_sel=st.selectbox("출하번호 *",list(dmap.keys()) if dmap else ["없음"])
            dd=dmap.get(d_sel)
            a,b=st.columns(2); boxes=a.number_input("총 박스 수",min_value=1,value=1); qpb=b.number_input("박스당 수량",min_value=1,value=1)
            c,d=st.columns(2); gw=c.number_input("총중량(kg)",min_value=0.0,format="%.2f"); nw=d.number_input("순중량(kg)",min_value=0.0,format="%.2f")
            dims=st.text_input("박스 치수(L×W×H cm)")
            marks=st.text_area("화인(Shipping Marks)",height=50)
            note_pl=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not dmap: st.error("출하 없음")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO packing_lists(pl_number,delivery_id,item_name,box_number,qty_per_box,total_boxes,gross_weight,net_weight,dimensions,marks,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (gen_number("PL"),dd['id'],dd['item_name'],1,qpb,boxes,gw,nw,dims,marks,note_pl))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("포장명세서 목록")
        conn=get_db(); df_pl=pd.read_sql_query("""
            SELECT p.pl_number AS PL번호, d.delivery_number AS 출하번호,
                   p.item_name AS 품목, p.total_boxes AS 박스수,
                   p.qty_per_box AS 박스당수량,
                   p.total_boxes*p.qty_per_box AS 총수량,
                   p.gross_weight AS 총중량, p.net_weight AS 순중량,
                   p.dimensions AS 치수, p.marks AS 화인,
                   p.created_at AS 등록일
            FROM packing_lists p
            LEFT JOIN deliveries d ON p.delivery_id=d.id
            ORDER BY p.id DESC""", conn); conn.close()
        if df_pl.empty: st.info("없음")
        else: st.dataframe(df_pl,use_container_width=True,hide_index=True)

        # ── 행 수정/삭제 버튼 (포장명세서) ──────────────────────────
        if not df_pl.empty if hasattr(df_pl, 'empty') else df_pl is not None:
            _row_opts_packing_lists = {}
            try:
                _cx_opt = get_db()
                _opt_rs = [dict(r) for r in _cx_opt.execute(
                    "SELECT id, SO번호 FROM packing_lists ORDER BY id DESC LIMIT 300"
                ).fetchall()]
                _cx_opt.close()
                for _r in _opt_rs:
                    _k = f"{_r['id']} | {_r.get('SO번호','')}"
                    _row_opts_packing_lists[_k] = _r['id']
            except Exception:
                pass

            if _row_opts_packing_lists:
                _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                _rb_sel_packing_lists = _rb_sel_col.selectbox(
                    "행 선택", list(_row_opts_packing_lists.keys()),
                    key="_rbsel_packing_lists", label_visibility="collapsed"
                )
                _rb_id_packing_lists = _row_opts_packing_lists[_rb_sel_packing_lists]

                if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_packing_lists"):
                    st.session_state[f"_edit_packing_lists"] = _rb_id_packing_lists
                    st.session_state[f"_del_packing_lists"]  = None

                if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_packing_lists"):
                    st.session_state[f"_del_packing_lists"]  = _rb_id_packing_lists
                    st.session_state[f"_edit_packing_lists"] = None

            # ── 삭제 확인 ──────────────────────────────────────────
            if st.session_state.get(f"_del_packing_lists"):
                _del_id_packing_lists = st.session_state[f"_del_packing_lists"]
                st.warning(f"⚠️ ID **{_del_id_packing_lists}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                _dc1, _dc2 = st.columns(2)
                if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_packing_lists"):
                    _cx_d = get_db()
                    _cx_d.execute("DELETE FROM packing_lists WHERE id = ?", (_del_id_packing_lists,))
                    _cx_d.commit(); _cx_d.close()
                    st.session_state[f"_del_packing_lists"] = None
                    st.success("✅ 삭제 완료!"); st.rerun()
                if _dc2.button("취소", use_container_width=True, key="_delcancel_packing_lists"):
                    st.session_state[f"_del_packing_lists"] = None; st.rerun()

            # ── 수정 인라인 폼 ─────────────────────────────────────
            if st.session_state.get(f"_edit_packing_lists"):
                _edit_id_packing_lists = st.session_state[f"_edit_packing_lists"]
                try:
                    _cx_e = get_db()
                    _edit_row_packing_lists = dict(_cx_e.execute(
                        "SELECT * FROM packing_lists WHERE id=?", (_edit_id_packing_lists,)
                    ).fetchone() or {})
                    _cx_e.close()
                except Exception:
                    _edit_row_packing_lists = {}
                with st.expander(f"✏️ 포장명세서 수정 — ID {_edit_id_packing_lists}", expanded=True):
                    if not _edit_row_packing_lists:
                        st.warning("데이터를 불러올 수 없습니다.")
                    else:
                        _skip_cols = {'id','created_at','updated_at'}
                        _edit_fields_packing_lists = [c for c in _edit_row_packing_lists if c not in _skip_cols]
                        _ncols = min(3, max(1, len(_edit_fields_packing_lists)))
                        _ecols = st.columns(_ncols)
                        _new_vals_packing_lists = {}
                        for _i, _fc in enumerate(_edit_fields_packing_lists):
                            _cv = _edit_row_packing_lists[_fc]
                            _ec = _ecols[_i % _ncols]
                            if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                _new_vals_packing_lists[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_packing_lists}_{_fc}_packing_lists")
                            else:
                                _new_vals_packing_lists[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_packing_lists}_{_fc}_packing_lists")
                        _s1, _s2 = st.columns(2)
                        if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_packing_lists"):
                            _set_sql = ", ".join([f"{c}=?" for c in _new_vals_packing_lists])
                            _set_params = list(_new_vals_packing_lists.values()) + [_edit_id_packing_lists]
                            _cx_s = get_db()
                            _cx_s.execute(f"UPDATE packing_lists SET {_set_sql} WHERE id=?", _set_params)
                            _cx_s.commit(); _cx_s.close()
                            st.session_state[f"_edit_packing_lists"] = None
                            st.success("✅ 수정 저장 완료!"); st.rerun()
                        if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_packing_lists"):
                            st.session_state[f"_edit_packing_lists"] = None; st.rerun()


        # 출력용 뷰
        if not df_pl.empty:
            st.divider(); st.subheader("📄 포장명세서 출력 뷰")
            sel_pl=st.selectbox("PL 선택",df_pl['PL번호'].tolist())
            row=df_pl[df_pl['PL번호']==sel_pl].iloc[0]
            st.markdown(f"""
| 항목 | 내용 |
|---|---|
| **PL번호** | {row['PL번호']} |
| **출하번호** | {row['출하번호']} |
| **품목** | {row['품목']} |
| **박스 수** | {row['박스수']} boxes |
| **박스당 수량** | {row['박스당수량']} EA |
| **총 수량** | {row['총수량']} EA |
| **총중량** | {row['총중량']} kg |
| **순중량** | {row['순중량']} kg |
| **치수** | {row['치수']} |
| **화인** | {row['화인']} |
""")


# ══ 매출 목표 관리 ══════════════════════════════════════════
with tabs["bi_target"]:
    def _acd3(t,c,ct="TEXT"):
        try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
        except: pass
    # MySQL: sales_targets 테이블은 db.py init_db()에서 이미 생성됨

    st.subheader("🎯 매출 목표 관리")
    col_form,col_bi=st.columns([1,2])
    with col_form:
        st.subheader("목표 등록")
        with st.form("tgt_f",clear_on_submit=True):
            a,b=st.columns(2); yr=a.number_input("연도",min_value=2020,max_value=2030,value=datetime.now().year); mo=b.number_input("월",min_value=1,max_value=12,value=datetime.now().month)
            tamt=st.number_input("목표금액(₩)",min_value=0.0,format="%.0f")
            tqty=st.number_input("목표수량",min_value=0,value=0)
            c,d=st.columns(2); item_t=c.text_input("품목(선택)"); ch_t=d.selectbox("채널",["전체","직판","온라인","대리점","해외","도매"])
            note_t=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                try:
                    conn=get_db(); conn.execute("INSERT INTO sales_targets(year,month,target_amount,target_qty,item_name,channel,note) VALUES(?,?,?,?,?,?,?)",(yr,mo,tamt,tqty,item_t,ch_t,note_t))
                    conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")

    with col_bi:
        if not HAS_PL: st.warning("pip install plotly")
        else:
            conn=get_db()
            df_tgt=pd.read_sql_query("""
                SELECT year AS 연도, month AS 월, target_amount AS 목표금액,
                       target_qty AS 목표수량, channel AS 채널
                FROM sales_targets ORDER BY year,month""", conn)
            df_act=pd.read_sql_query("""
                SELECT YEAR(ordered_at) AS year,
                       MONTH(ordered_at) AS month,
                       ROUND(SUM(quantity*unit_price*(1-discount_rate/100)),0) AS 실적금액,
                       SUM(quantity) AS 실적수량
                FROM sales_orders WHERE status!='취소'
                GROUP BY YEAR(ordered_at), MONTH(ordered_at)""", conn)
            conn.close()

            if df_tgt.empty: st.info("목표 없음 — 좌측에서 목표를 등록하세요")
            else:
                df_tgt['ym']=df_tgt['연도'].astype(str)+"-"+df_tgt['월'].astype(str).str.zfill(2)
                df_act['ym']=df_act['year'].astype(str)+"-"+df_act['month'].astype(str).str.zfill(2)
                df_merge=df_tgt.merge(df_act[['ym','실적금액','실적수량']],on='ym',how='left').fillna(0)
                df_merge['달성률%']=(df_merge['실적금액']/df_merge['목표금액']*100).round(1).where(df_merge['목표금액']>0,0)

                # KPI
                cur_ym=datetime.now().strftime("%Y-%m")
                cur=df_merge[df_merge['ym']==cur_ym]
                if not cur.empty:
                    c1,c2,c3=st.columns(3)
                    c1.metric("이번달 목표",f"₩{cur.iloc[0]['목표금액']:,.0f}")
                    c2.metric("이번달 실적",f"₩{cur.iloc[0]['실적금액']:,.0f}")
                    c3.metric("달성률",f"{cur.iloc[0]['달성률%']}%",
                              delta="달성" if cur.iloc[0]['달성률%']>=100 else "미달",
                              delta_color="normal" if cur.iloc[0]['달성률%']>=100 else "inverse")

                fig=go.Figure()
                fig.add_trace(go.Bar(x=df_merge['ym'],y=df_merge['목표금액'],name='목표',marker_color='#cbd5e1'))
                fig.add_trace(go.Bar(x=df_merge['ym'],y=df_merge['실적금액'],name='실적',marker_color='#3b82f6'))
                fig.add_trace(go.Scatter(x=df_merge['ym'],y=df_merge['달성률%'],name='달성률(%)',
                                          mode='lines+markers',yaxis='y2',
                                          line=dict(color='#f97316',width=2)))
                fig.update_layout(
                    barmode='overlay',title="월별 목표 vs 실적",height=320,
                    margin=dict(l=0,r=0,t=40,b=0),
                    legend=dict(orientation="h",y=1.1),
                    yaxis2=dict(overlaying='y',side='right',title='달성률%'))
                st.plotly_chart(fig,use_container_width=True)
                st.dataframe(df_merge[['ym','목표금액','실적금액','달성률%']].rename(columns={'ym':'월'}), use_container_width=True, hide_index=True)

                # ── 행 수정/삭제 버튼 (sales_targets) ──────────────────────────
                if not df_merge.empty if hasattr(df_merge, 'empty') else df_merge is not None:
                    _row_opts_sales_targets = {}
                    try:
                        _cx_opt = get_db()
                        _opt_rs = [dict(r) for r in _cx_opt.execute(
                            "SELECT id, * FROM sales_targets ORDER BY id DESC LIMIT 300"
                        ).fetchall()]
                        _cx_opt.close()
                        for _r in _opt_rs:
                            _k = f"{_r['id']} | {_r.get('item_name','')}"
                            _row_opts_sales_targets[_k] = _r['id']
                    except Exception:
                        pass
    
                    if _row_opts_sales_targets:
                        _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                        _rb_sel_sales_targets = _rb_sel_col.selectbox(
                            "행 선택", list(_row_opts_sales_targets.keys()),
                            key="_rbsel_sales_targets", label_visibility="collapsed"
                        )
                        _rb_id_sales_targets = _row_opts_sales_targets[_rb_sel_sales_targets]
    
                        if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_sales_targets"):
                            st.session_state[f"_edit_sales_targets"] = _rb_id_sales_targets
                            st.session_state[f"_del_sales_targets"]  = None
    
                        if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_sales_targets"):
                            st.session_state[f"_del_sales_targets"]  = _rb_id_sales_targets
                            st.session_state[f"_edit_sales_targets"] = None
    
                    # ── 삭제 확인 ──────────────────────────────────────────
                    if st.session_state.get(f"_del_sales_targets"):
                        _del_id_sales_targets = st.session_state[f"_del_sales_targets"]
                        st.warning(f"⚠️ ID **{_del_id_sales_targets}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                        _dc1, _dc2 = st.columns(2)
                        if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_sales_targets"):
                            _cx_d = get_db()
                            _cx_d.execute("DELETE FROM sales_targets WHERE id = ?", (_del_id_sales_targets,))
                            _cx_d.commit(); _cx_d.close()
                            st.session_state[f"_del_sales_targets"] = None
                            st.success("✅ 삭제 완료!"); st.rerun()
                        if _dc2.button("취소", use_container_width=True, key="_delcancel_sales_targets"):
                            st.session_state[f"_del_sales_targets"] = None; st.rerun()
    
                    # ── 수정 인라인 폼 ─────────────────────────────────────
                    if st.session_state.get(f"_edit_sales_targets"):
                        _edit_id_sales_targets = st.session_state[f"_edit_sales_targets"]
                        try:
                            _cx_e = get_db()
                            _edit_row_sales_targets = dict(_cx_e.execute(
                                "SELECT * FROM sales_targets WHERE id=?", (_edit_id_sales_targets,)
                            ).fetchone() or {})
                            _cx_e.close()
                        except Exception:
                            _edit_row_sales_targets = {}
                        with st.expander(f"✏️ 정보 수정 — ID {_edit_id_sales_targets}", expanded=True):
                            if not _edit_row_sales_targets:
                                st.warning("데이터를 불러올 수 없습니다.")
                            else:
                                _skip_cols = {'id','created_at','updated_at','ordered_at'}
                                _edit_fields_sales_targets = [c for c in _edit_row_sales_targets if c not in _skip_cols]
                                _ncols = min(3, max(1, len(_edit_fields_sales_targets)))
                                _ecols = st.columns(_ncols)
                                _new_vals_sales_targets = {}
                                for _i, _fc in enumerate(_edit_fields_sales_targets):
                                    _cv = _edit_row_sales_targets[_fc]
                                    _ec = _ecols[_i % _ncols]
                                    if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                        _new_vals_sales_targets[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_sales_targets}_{_fc}_sales_targets")
                                    else:
                                        _new_vals_sales_targets[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_sales_targets}_{_fc}_sales_targets")
                                _s1, _s2 = st.columns(2)
                                if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_sales_targets"):
                                    _set_sql = ", ".join([f"{c}=?" for c in _new_vals_sales_targets])
                                    _set_params = list(_new_vals_sales_targets.values()) + [_edit_id_sales_targets]
                                    _cx_s = get_db()
                                    _cx_s.execute(f"UPDATE sales_targets SET {_set_sql} WHERE id=?", _set_params)
                                    _cx_s.commit(); _cx_s.close()
                                    st.session_state[f"_edit_sales_targets"] = None
                                    st.success("✅ 수정 저장 완료!"); st.rerun()
                                if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_sales_targets"):
                                    st.session_state[f"_edit_sales_targets"] = None; st.rerun()

# ══ 고객 신용한도 관리 ══════════════════════════════════════════
with tabs["credit"]:
    def _acd_sd(t,c,ct="TEXT"):
        try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
        except: pass
    # MySQL: customers/sales_orders 컬럼 추가 안전 시도
    _acd_sd("customers","credit_limit","DECIMAL(18,2) DEFAULT 0")
    _acd_sd("customers","credit_used","DECIMAL(18,2) DEFAULT 0")
    _acd_sd("customers","credit_status","VARCHAR(20) DEFAULT '정상'")
    _acd_sd("customers","payment_terms","VARCHAR(100) DEFAULT 'NET30'")
    _acd_sd("sales_orders","sales_rep","VARCHAR(100)")

    st.subheader("💳 고객 신용한도 관리")
    col_set, col_mon = st.columns([1, 2])
    with col_set:
        st.subheader("신용한도 설정")
        conn=get_db()
        custs=[r for r in conn.execute("SELECT id,customer_name,credit_limit,credit_used,payment_terms FROM customers ORDER BY customer_name").fetchall()]
        conn.close()
        if not custs: st.info("고객 없음")
        else:
            cmap={r['customer_name']:r for r in custs}
            sel_c=st.selectbox("고객 선택",list(cmap.keys()))
            cd=cmap[sel_c]
            with st.form("credit_f"):
                a,b=st.columns(2)
                lim=a.number_input("신용한도(₩)",min_value=0.0,value=float(cd['credit_limit'] or 0),format="%.0f",step=1000000.0)
                terms=b.selectbox("결제조건",["NET30","NET60","NET90","현금","선불","기타"],
                    index=["NET30","NET60","NET90","현금","선불","기타"].index(cd['payment_terms']) if cd['payment_terms'] in ["NET30","NET60","NET90","현금","선불","기타"] else 0)
                if st.form_submit_button("✅ 저장",use_container_width=True):
                    conn=get_db(); conn.execute("UPDATE customers SET credit_limit=?,payment_terms=? WHERE id=?",(lim,terms,cd['id']))
                    conn.commit(); conn.close(); st.success("저장!"); st.rerun()

        if st.button("🔄 신용 사용액 재계산",use_container_width=True):
            conn=get_db()
            for c2 in custs:
                used=conn.execute("SELECT COALESCE(SUM(quantity*unit_price*(1-discount_rate/100)),0) FROM sales_orders WHERE customer_name=? AND status NOT IN ('취소','배송완료')",(c2['customer_name'],)).fetchone()[0]
                status_cr="초과" if used>(c2['credit_limit'] or 0) and (c2['credit_limit'] or 0)>0 else ("경고" if used>(c2['credit_limit'] or 0)*0.8 and (c2['credit_limit'] or 0)>0 else "정상")
                conn.execute("UPDATE customers SET credit_used=?,credit_status=? WHERE id=?",(used,status_cr,c2['id']))
            conn.commit(); conn.close(); st.success("재계산 완료!"); st.rerun()

    with col_mon:
        st.subheader("📊 신용 현황 모니터링")
        conn=get_db(); df_cr=pd.read_sql_query("""
            SELECT customer_name AS 고객, credit_limit AS 한도,
                   credit_used AS 사용액,
                   ROUND(credit_used*100.0/GREATEST(credit_limit,1),1) AS 사용률,
                   credit_limit-credit_used AS 잔여한도,
                   payment_terms AS 결제조건,
                   CASE credit_status WHEN '초과' THEN '🔴 초과' WHEN '경고' THEN '🟠 경고' ELSE '🟢 정상' END AS 상태
            FROM customers WHERE credit_limit>0 ORDER BY 사용률 DESC""", conn); conn.close()
        if df_cr.empty: st.info("신용한도 설정된 고객 없음")
        else:
            over=df_cr[df_cr['상태'].str.contains('초과')]
            warn=df_cr[df_cr['상태'].str.contains('경고')]
            if not over.empty: st.error(f"🚨 신용 초과: {len(over)}개사")
            if not warn.empty: st.warning(f"⚠️ 신용 경고(80% 이상): {len(warn)}개사")
            st.dataframe(df_cr, use_container_width=True, hide_index=True)
            try:
                import plotly.express as px
                fig=px.bar(df_cr,x='고객',y=['한도','사용액'],barmode='overlay',
                    title="고객별 신용한도 현황",color_discrete_map={'한도':'#cbd5e1','사용액':'#3b82f6'})
                fig.update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig,use_container_width=True)
            except: pass


# ══ ATP 가용재고 확인 ══════════════════════════════════════════
with tabs["atp"]:
    st.subheader("✅ ATP — Available to Promise (납기 약속 가능 확인)")
    st.caption("판매주문 등록 전 재고·생산계획 기준으로 납기 약속 가능 여부 자동 계산")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        item_atp=st.text_input("품목명 *")
        req_qty=st.number_input("요청 수량",min_value=1,value=1)
        req_date=st.date_input("요청 납기",value=date.today()+timedelta(days=14))
        if st.button("🔍 ATP 확인",use_container_width=True,type="primary"):
            if not item_atp: st.error("품목명 필수")
            else:
                conn=get_db()
                # 현재 가용재고
                stock=conn.execute("SELECT COALESCE(SUM(stock_qty),0) FROM inventory WHERE item_name LIKE ?",(f"%{item_atp}%",)).fetchone()[0]
                # 미출하 주문 예약 수량
                reserved=conn.execute("SELECT COALESCE(SUM(quantity-COALESCE(shipped_qty,0)),0) FROM sales_orders WHERE item_name LIKE ? AND status NOT IN ('취소','배송완료')",(f"%{item_atp}%",)).fetchone()[0]
                # 납기일 이전 생산완료 예정
                planned=conn.execute("SELECT COALESCE(SUM(planned_qty),0) FROM production_plans WHERE product_name LIKE ? AND end_date<=? AND status NOT IN ('취소')",(f"%{item_atp}%",str(req_date))).fetchone()[0]
                conn.close()
                available=stock-reserved+planned
                can_promise=available>=req_qty
                st.divider()
                c1,c2,c3=st.columns(3)
                c1.metric("현재고",f"{stock:,}")
                c2.metric("예약수량",f"-{reserved:,}")
                c3.metric("생산예정",f"+{planned:,}")
                st.metric("ATP 가용수량",f"{available:,}",delta=f"{'✅ 납기약속 가능' if can_promise else '❌ 납기약속 불가'}", delta_color="normal" if can_promise else "inverse")
                if can_promise: st.success(f"✅ {req_qty:,}개 → {req_date} 납기 약속 가능")
                else:
                    shortage=req_qty-available
                    st.error(f"❌ {shortage:,}개 부족 — 납기 재조정 필요")
                    # 가능한 최초 납기 계산
                    conn=get_db()
                    next_pp=conn.execute("SELECT end_date,planned_qty FROM production_plans WHERE product_name LIKE ? AND status NOT IN ('취소') ORDER BY end_date",(f"%{item_atp}%",)).fetchall()
                    conn.close()
                    if next_pp: st.info(f"💡 가장 빠른 생산완료: {next_pp[0]['end_date']} ({next_pp[0]['planned_qty']:,}개)")

    with col_r:
        st.subheader("품목별 ATP 현황")
        conn=get_db(); df_atp=pd.read_sql_query("""
            SELECT i.item_name AS 품목,
                   COALESCE(i.stock_qty,0) AS 현재고,
                   COALESCE(so_res.reserved,0) AS 예약수량,
                   COALESCE(pp_plan.planned,0) AS 생산예정,
                   COALESCE(i.stock_qty,0)-COALESCE(so_res.reserved,0)+COALESCE(pp_plan.planned,0) AS ATP수량
            FROM inventory i
            LEFT JOIN (SELECT item_name, SUM(quantity-COALESCE(shipped_qty,0)) AS reserved
                       FROM sales_orders WHERE status NOT IN ('취소','배송완료') GROUP BY item_name) so_res ON i.item_name=so_res.item_name
            LEFT JOIN (SELECT product_name, SUM(planned_qty) AS planned
                       FROM production_plans WHERE status NOT IN ('취소') GROUP BY product_name) pp_plan ON i.item_name=pp_plan.product_name
            WHERE i.stock_qty>0 OR so_res.reserved>0
            ORDER BY ATP수량""", conn); conn.close()
        if df_atp.empty: st.info("재고 없음")
        else:
            def atp_c(r): return ['background-color:#fee2e2']*len(r) if r['ATP수량']<0 else (['background-color:#fef3c7']*len(r) if r['ATP수량']<10 else ['']*len(r))
            st.dataframe(df_atp.style.apply(atp_c,axis=1), use_container_width=True, hide_index=True)


# ══ 납기약속(CRD) 관리 ══════════════════════════════════════════
with tabs["crd"]:
    _acd_sd("sales_orders","confirmed_delivery_date","TEXT")
    _acd_sd("sales_orders","actual_delivery_date","TEXT")

    st.subheader("📅 납기약속(CRD) — Customer Required Date 관리")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.subheader("확정납기 등록")
        conn=get_db()
        open_so=[r for r in conn.execute("""SELECT id,order_number,customer_name,item_name,quantity,requested_delivery,confirmed_delivery_date
            FROM sales_orders WHERE status NOT IN ('취소','배송완료') ORDER BY requested_delivery""").fetchall()]
        conn.close()
        if not open_so: st.info("진행중 SO 없음")
        else:
            so_m={f"{r['order_number']}-{r['customer_name']}/{r['item_name']}":r for r in open_so}
            sel_crd=st.selectbox("SO 선택",list(so_m.keys()))
            sd=so_m[sel_crd]
            a,b=st.columns(2)
            req_d=a.text_input("요청납기",value=sd['requested_delivery'] or '-',disabled=True)
            conf_d=b.date_input("확정납기",value=date.today()+timedelta(days=7))
            act_d=st.date_input("실제납기(완료시)",value=date.today())
            note_crd=st.text_input("비고")
            if st.button("✅ 납기 확정",use_container_width=True):
                conn=get_db(); conn.execute("UPDATE sales_orders SET confirmed_delivery_date=?,actual_delivery_date=? WHERE id=?",(str(conf_d),str(act_d) if sd['status'] in ['배송완료'] else None,sd['id']))
                conn.commit(); conn.close(); st.success("납기 확정!"); st.rerun()
    with col_r:
        st.subheader("납기 달성률 현황")
        conn=get_db(); df_crd=pd.read_sql_query("""
            SELECT order_number AS SO번호, customer_name AS 고객, item_name AS 품목,
                   requested_delivery AS 요청납기, confirmed_delivery_date AS 확정납기,
                   actual_delivery_date AS 실납기,
                   CASE
                     WHEN actual_delivery_date IS NOT NULL AND actual_delivery_date<=requested_delivery THEN '✅ 준수'
                     WHEN actual_delivery_date IS NOT NULL AND actual_delivery_date>requested_delivery THEN '❌ 지연'
                     WHEN confirmed_delivery_date<=CURDATE() AND status NOT IN ('배송완료') THEN '⚠️ 지연위험'
                     ELSE '🔄 진행중'
                   END AS 납기상태,
                   status AS SO상태
            FROM sales_orders WHERE status NOT IN ('취소')
            ORDER BY requested_delivery""", conn); conn.close()
        if df_crd.empty: st.info("없음")
        else:
            total=len(df_crd[df_crd['실납기'].notna()])
            on_time=len(df_crd[df_crd['납기상태']=='✅ 준수'])
            rate=round(on_time/max(total,1)*100,1)
            c1,c2,c3=st.columns(3)
            c1.metric("납기준수율",f"{rate}%",delta="목표 95%" if rate>=95 else "개선필요",delta_color="normal" if rate>=95 else "inverse")
            c2.metric("준수",f"{on_time}건")
            c3.metric("지연",f"{len(df_crd[df_crd['납기상태']=='❌ 지연'])}건",delta_color="inverse")
            st.dataframe(df_crd, use_container_width=True, hide_index=True)


# ══ 선수금 관리 ══════════════════════════════════════════
with tabs["prepay"]:
    # MySQL: prepayments 테이블은 db.py init_db()에서 이미 생성됨

    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("💵 선수금 등록")
        conn=get_db()
        open_so2=[r for r in conn.execute("SELECT id,order_number,customer_name,item_name,quantity*unit_price AS total FROM sales_orders WHERE status NOT IN ('취소') ORDER BY id DESC LIMIT 30").fetchall()]
        conn.close()
        so_m2={f"{r['order_number']}-{r['customer_name']}(₩{r['total']:,.0f})":r for r in open_so2}
        with st.form("pp_f", clear_on_submit=True):
            sel_pp=st.selectbox("SO 선택 *",list(so_m2.keys()) if so_m2 else ["없음"])
            pp_d=so_m2.get(sel_pp)
            cust_pp=st.text_input("고객명",value=pp_d['customer_name'] if pp_d else "")
            a,b=st.columns(2); amt_pp=a.number_input("선수금액(₩)",min_value=0.0,format="%.0f"); recv_pp=b.date_input("입금일")
            bank_pp=st.text_input("입금 참조번호"); note_pp=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                try:
                    conn=get_db()
                    conn.execute("INSERT INTO prepayments(prepay_number,order_id,customer_name,prepay_amount,received_date,bank_ref,note,status) VALUES(?,?,?,?,?,?,?,?)",
                        (gen_number("PPY"),pp_d['id'] if pp_d else None,cust_pp,amt_pp,str(recv_pp),bank_pp,note_pp,"미적용"))
                    conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")

        st.divider()
        st.subheader("선수금 청구서 적용")
        conn=get_db()
        pp_unapplied=[r for r in conn.execute("SELECT id,prepay_number,customer_name,prepay_amount,applied_amount FROM prepayments WHERE status='미적용'").fetchall()]
        conn.close()
        if pp_unapplied:
            pp_sel_m={f"{r['prepay_number']}-{r['customer_name']}(₩{r['prepay_amount']:,.0f})":r for r in pp_unapplied}
            sel_ppu=st.selectbox("선수금 선택",list(pp_sel_m.keys()))
            apply_amt=st.number_input("적용금액",min_value=0.0,format="%.0f")
            if st.button("✅ 청구서 차감 적용",use_container_width=True):
                r2=pp_sel_m[sel_ppu]; new_app=r2['applied_amount']+apply_amt
                new_st="전액적용" if new_app>=r2['prepay_amount'] else "부분적용"
                conn=get_db(); conn.execute("UPDATE prepayments SET applied_amount=?,status=? WHERE id=?",(new_app,new_st,r2['id']))
                conn.commit(); conn.close(); st.success(f"적용 완료! (누적적용: ₩{new_app:,.0f})"); st.rerun()

    with col_list:
        st.subheader("선수금 현황")
        conn=get_db(); df_pp=pd.read_sql_query("""
            SELECT prepay_number AS 선수금번호, customer_name AS 고객,
                   prepay_amount AS 선수금액, applied_amount AS 적용금액,
                   prepay_amount-applied_amount AS 잔여선수금,
                   received_date AS 입금일, status AS 상태
            FROM prepayments ORDER BY id DESC""", conn); conn.close()
        if df_pp.empty: st.info("없음")
        else:
            c1,c2=st.columns(2); c1.metric("미적용 선수금",f"₩{df_pp[df_pp['상태']=='미적용']['선수금액'].sum():,.0f}")
            c2.metric("총 선수금",f"₩{df_pp['선수금액'].sum():,.0f}")
            st.dataframe(df_pp, use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (선수금) ──────────────────────────
            if not df_pp.empty if hasattr(df_pp, 'empty') else df_pp is not None:
                _row_opts_prepayments = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 고객명 FROM prepayments ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('고객명','')}"
                        _row_opts_prepayments[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_prepayments:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_prepayments = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_prepayments.keys()),
                        key="_rbsel_prepayments", label_visibility="collapsed"
                    )
                    _rb_id_prepayments = _row_opts_prepayments[_rb_sel_prepayments]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_prepayments"):
                        st.session_state[f"_edit_prepayments"] = _rb_id_prepayments
                        st.session_state[f"_del_prepayments"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_prepayments"):
                        st.session_state[f"_del_prepayments"]  = _rb_id_prepayments
                        st.session_state[f"_edit_prepayments"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_prepayments"):
                    _del_id_prepayments = st.session_state[f"_del_prepayments"]
                    st.warning(f"⚠️ ID **{_del_id_prepayments}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_prepayments"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM prepayments WHERE id = ?", (_del_id_prepayments,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_prepayments"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_prepayments"):
                        st.session_state[f"_del_prepayments"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_prepayments"):
                    _edit_id_prepayments = st.session_state[f"_edit_prepayments"]
                    try:
                        _cx_e = get_db()
                        _edit_row_prepayments = dict(_cx_e.execute(
                            "SELECT * FROM prepayments WHERE id=?", (_edit_id_prepayments,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_prepayments = {}
                    with st.expander(f"✏️ 선수금 수정 — ID {_edit_id_prepayments}", expanded=True):
                        if not _edit_row_prepayments:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_prepayments = [c for c in _edit_row_prepayments if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_prepayments)))
                            _ecols = st.columns(_ncols)
                            _new_vals_prepayments = {}
                            for _i, _fc in enumerate(_edit_fields_prepayments):
                                _cv = _edit_row_prepayments[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_prepayments[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_prepayments}_{_fc}_prepayments")
                                else:
                                    _new_vals_prepayments[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_prepayments}_{_fc}_prepayments")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_prepayments"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_prepayments])
                                _set_params = list(_new_vals_prepayments.values()) + [_edit_id_prepayments]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE prepayments SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_prepayments"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_prepayments"):
                                st.session_state[f"_edit_prepayments"] = None; st.rerun()



# ══ AS 접수 ══════════════════════════════════════════
with tabs["as_"]:
    # MySQL: as_requests 테이블은 db.py init_db()에서 이미 생성됨

    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("🔧 AS 접수")
        conn=get_db()
        delis_as=[r for r in conn.execute("SELECT d.id,d.delivery_number,o.customer_name,d.item_name FROM deliveries d JOIN sales_orders o ON d.order_id=o.id WHERE d.status='배송완료' ORDER BY d.id DESC LIMIT 30").fetchall()]
        conn.close()
        dmap_as={f"{r['delivery_number']}-{r['customer_name']}/{r['item_name']}":r for r in delis_as}
        with st.form("as_f", clear_on_submit=True):
            sel_as=st.selectbox("출하건 선택",["직접입력"]+list(dmap_as.keys()))
            as_d=dmap_as.get(sel_as)
            cust_as=st.text_input("고객명",value=as_d['customer_name'] if as_d else "")
            item_as=st.text_input("품목명",value=as_d['item_name'] if as_d else "")
            a,b=st.columns(2); atype=a.selectbox("AS 유형",["수리","교환","반품","현장방문","원격지원"]); pri=b.selectbox("우선순위",["긴급","높음","일반","낮음"])
            symptom=st.text_area("증상/불량내용 *",height=70)
            assigned=st.text_input("담당자")
            note_as=st.text_area("비고",height=40)
            link_qm=st.checkbox("QM 클레임 연동 생성")
            if st.form_submit_button("✅ AS 접수",use_container_width=True):
                if not symptom: st.error("증상 필수")
                else:
                    try:
                        conn=get_db()
                        asn=gen_number("AS")
                        conn.execute("INSERT INTO as_requests(as_number,order_id,customer_name,item_name,delivery_number,symptom,as_type,priority,assigned_to,received_date,qm_claim_linked,status) VALUES(?,?,?,?,?,?,?,?,?,CURDATE(),?,?)",
                            (asn,as_d['id'] if as_d else None,cust_as,item_as,as_d['delivery_number'] if as_d else "",symptom,atype,pri,assigned,1 if link_qm else 0,"접수"))
                        if link_qm:
                            conn.execute("INSERT INTO quality_inspections(inspection_number,inspection_type,item_name,lot_size,sample_qty,result,note) VALUES(?,?,?,?,?,?,?)",
                                (gen_number("QI"),"고객클레임",item_as,1,1,"불합격",f"AS연동:{asn} / {symptom[:50]}"))
                        conn.commit(); conn.close(); st.success(f"AS {asn} 접수!" + (" + QM 클레임 생성" if link_qm else "")); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("AS 현황")
        conn=get_db(); df_as=pd.read_sql_query("""
            SELECT as_number AS AS번호, customer_name AS 고객, item_name AS 품목,
                   as_type AS 유형, priority AS 우선순위,
                   symptom AS 증상, assigned_to AS 담당자,
                   received_date AS 접수일, completed_date AS 완료일,
                   status AS 상태
            FROM as_requests ORDER BY
            CASE priority WHEN '긴급' THEN 1 WHEN '높음' THEN 2 WHEN '일반' THEN 3 ELSE 4 END,
            id DESC""", conn); conn.close()
        if df_as.empty: st.info("없음")
        else:
            c1,c2,c3=st.columns(3)
            c1.metric("전체",len(df_as))
            c2.metric("긴급",len(df_as[df_as['우선순위']=='긴급']),delta_color="inverse")
            c3.metric("완료",len(df_as[df_as['상태']=='완료']))
            def as_c(r): return ['background-color:#fee2e2']*len(r) if r['우선순위']=='긴급' and r['상태']!='완료' else ['']*len(r)
            st.dataframe(df_as.style.apply(as_c,axis=1), use_container_width=True, hide_index=True)

            # ── 행 수정/삭제 버튼 (AS접수) ──────────────────────────
            if not df_as.empty if hasattr(df_as, 'empty') else df_as is not None:
                _row_opts_as_requests = {}
                try:
                    _cx_opt = get_db()
                    _opt_rs = [dict(r) for r in _cx_opt.execute(
                        "SELECT id, 고객명 FROM as_requests ORDER BY id DESC LIMIT 300"
                    ).fetchall()]
                    _cx_opt.close()
                    for _r in _opt_rs:
                        _k = f"{_r['id']} | {_r.get('고객명','')}"
                        _row_opts_as_requests[_k] = _r['id']
                except Exception:
                    pass

                if _row_opts_as_requests:
                    _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                    _rb_sel_as_requests = _rb_sel_col.selectbox(
                        "행 선택", list(_row_opts_as_requests.keys()),
                        key="_rbsel_as_requests", label_visibility="collapsed"
                    )
                    _rb_id_as_requests = _row_opts_as_requests[_rb_sel_as_requests]

                    if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_as_requests"):
                        st.session_state[f"_edit_as_requests"] = _rb_id_as_requests
                        st.session_state[f"_del_as_requests"]  = None

                    if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_as_requests"):
                        st.session_state[f"_del_as_requests"]  = _rb_id_as_requests
                        st.session_state[f"_edit_as_requests"] = None

                # ── 삭제 확인 ──────────────────────────────────────────
                if st.session_state.get(f"_del_as_requests"):
                    _del_id_as_requests = st.session_state[f"_del_as_requests"]
                    st.warning(f"⚠️ ID **{_del_id_as_requests}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                    _dc1, _dc2 = st.columns(2)
                    if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_as_requests"):
                        _cx_d = get_db()
                        _cx_d.execute("DELETE FROM as_requests WHERE id = ?", (_del_id_as_requests,))
                        _cx_d.commit(); _cx_d.close()
                        st.session_state[f"_del_as_requests"] = None
                        st.success("✅ 삭제 완료!"); st.rerun()
                    if _dc2.button("취소", use_container_width=True, key="_delcancel_as_requests"):
                        st.session_state[f"_del_as_requests"] = None; st.rerun()

                # ── 수정 인라인 폼 ─────────────────────────────────────
                if st.session_state.get(f"_edit_as_requests"):
                    _edit_id_as_requests = st.session_state[f"_edit_as_requests"]
                    try:
                        _cx_e = get_db()
                        _edit_row_as_requests = dict(_cx_e.execute(
                            "SELECT * FROM as_requests WHERE id=?", (_edit_id_as_requests,)
                        ).fetchone() or {})
                        _cx_e.close()
                    except Exception:
                        _edit_row_as_requests = {}
                    with st.expander(f"✏️ AS접수 수정 — ID {_edit_id_as_requests}", expanded=True):
                        if not _edit_row_as_requests:
                            st.warning("데이터를 불러올 수 없습니다.")
                        else:
                            _skip_cols = {'id','created_at','updated_at'}
                            _edit_fields_as_requests = [c for c in _edit_row_as_requests if c not in _skip_cols]
                            _ncols = min(3, max(1, len(_edit_fields_as_requests)))
                            _ecols = st.columns(_ncols)
                            _new_vals_as_requests = {}
                            for _i, _fc in enumerate(_edit_fields_as_requests):
                                _cv = _edit_row_as_requests[_fc]
                                _ec = _ecols[_i % _ncols]
                                if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                    _new_vals_as_requests[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_as_requests}_{_fc}_as_requests")
                                else:
                                    _new_vals_as_requests[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_as_requests}_{_fc}_as_requests")
                            _s1, _s2 = st.columns(2)
                            if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_as_requests"):
                                _set_sql = ", ".join([f"{c}=?" for c in _new_vals_as_requests])
                                _set_params = list(_new_vals_as_requests.values()) + [_edit_id_as_requests]
                                _cx_s = get_db()
                                _cx_s.execute(f"UPDATE as_requests SET {_set_sql} WHERE id=?", _set_params)
                                _cx_s.commit(); _cx_s.close()
                                st.session_state[f"_edit_as_requests"] = None
                                st.success("✅ 수정 저장 완료!"); st.rerun()
                            if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_as_requests"):
                                st.session_state[f"_edit_as_requests"] = None; st.rerun()

            # 상태 변경
            open_as=[r for r in get_db().execute("SELECT id,as_number FROM as_requests WHERE status!='완료'").fetchall()]
            get_db().close()
            if open_as:
                st.divider()
                am={r['as_number']:r['id'] for r in open_as}
                c1,c2=st.columns(2); sel_asu=c1.selectbox("AS건",list(am.keys())); new_ast=c2.selectbox("상태",["접수","진행중","부품대기","완료","불가"])
                action=st.text_input("처리내용")
                if st.button("🔄 처리",use_container_width=True):
                    conn=get_db()
                    completed_val = str(date.today()) if new_ast=='완료' else None
                    conn.execute("UPDATE as_requests SET status=?,action_taken=?,completed_date=? WHERE id=?",(new_ast,action,completed_val,am[sel_asu]))
                    conn.commit(); conn.close(); st.rerun()


# ══ 영업사원 관리 ══════════════════════════════════════════
with tabs["sales_mgr"]:
    # MySQL: sales_reps 테이블은 db.py init_db()에서 이미 생성됨

    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("👤 영업사원 등록")
        with st.form("rep_f", clear_on_submit=True):
            a,b=st.columns(2); rc=a.text_input("사원코드 *"); rn=b.text_input("이름 *")
            c,d=st.columns(2); reg=c.text_input("담당지역"); team=d.text_input("소속팀")
            e,f=st.columns(2); phn=e.text_input("전화"); eml=f.text_input("이메일")
            tgt=st.number_input("월간목표(₩)",min_value=0.0,format="%.0f",step=1000000.0)
            rst=st.selectbox("상태",["재직","휴직","퇴직"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not rc or not rn: st.error("코드·이름 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("INSERT INTO sales_reps(rep_code,rep_name,region,team,phone,email,monthly_target,status) VALUES(?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE rep_name=VALUES(rep_name),monthly_target=VALUES(monthly_target)",
                            (rc,rn,reg,team,phn,eml,tgt,rst))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        conn=get_db(); df_reps=pd.read_sql_query("SELECT rep_code AS 코드,rep_name AS 이름,region AS 지역,team AS 팀,monthly_target AS 월목표,status AS 상태 FROM sales_reps ORDER BY rep_name",conn); conn.close()
        if not df_reps.empty: st.dataframe(df_reps,use_container_width=True,hide_index=True)

        # ── 행 수정/삭제 버튼 (영업사원) ──────────────────────────
        if not df_reps.empty if hasattr(df_reps, 'empty') else df_reps is not None:
            _row_opts_sales_reps = {}
            try:
                _cx_opt = get_db()
                _opt_rs = [dict(r) for r in _cx_opt.execute(
                    "SELECT id, 성명 FROM sales_reps ORDER BY id DESC LIMIT 300"
                ).fetchall()]
                _cx_opt.close()
                for _r in _opt_rs:
                    _k = f"{_r['id']} | {_r.get('성명','')}"
                    _row_opts_sales_reps[_k] = _r['id']
            except Exception:
                pass

            if _row_opts_sales_reps:
                _rb_sel_col, _rb_ed_col, _rb_del_col = st.columns([4, 1, 1])
                _rb_sel_sales_reps = _rb_sel_col.selectbox(
                    "행 선택", list(_row_opts_sales_reps.keys()),
                    key="_rbsel_sales_reps", label_visibility="collapsed"
                )
                _rb_id_sales_reps = _row_opts_sales_reps[_rb_sel_sales_reps]

                if _rb_ed_col.button("✏️ 수정", use_container_width=True, key="_rbed_sales_reps"):
                    st.session_state[f"_edit_sales_reps"] = _rb_id_sales_reps
                    st.session_state[f"_del_sales_reps"]  = None

                if _rb_del_col.button("🗑️ 삭제", use_container_width=True, key="_rbdel_sales_reps"):
                    st.session_state[f"_del_sales_reps"]  = _rb_id_sales_reps
                    st.session_state[f"_edit_sales_reps"] = None

            # ── 삭제 확인 ──────────────────────────────────────────
            if st.session_state.get(f"_del_sales_reps"):
                _del_id_sales_reps = st.session_state[f"_del_sales_reps"]
                st.warning(f"⚠️ ID **{_del_id_sales_reps}** 항목을 삭제합니다. 이 작업은 되돌릴 수 없습니다.")
                _dc1, _dc2 = st.columns(2)
                if _dc1.button("🗑️ 삭제 확인", type="primary", use_container_width=True, key="_delok_sales_reps"):
                    _cx_d = get_db()
                    _cx_d.execute("DELETE FROM sales_reps WHERE id = ?", (_del_id_sales_reps,))
                    _cx_d.commit(); _cx_d.close()
                    st.session_state[f"_del_sales_reps"] = None
                    st.success("✅ 삭제 완료!"); st.rerun()
                if _dc2.button("취소", use_container_width=True, key="_delcancel_sales_reps"):
                    st.session_state[f"_del_sales_reps"] = None; st.rerun()

            # ── 수정 인라인 폼 ─────────────────────────────────────
            if st.session_state.get(f"_edit_sales_reps"):
                _edit_id_sales_reps = st.session_state[f"_edit_sales_reps"]
                try:
                    _cx_e = get_db()
                    _edit_row_sales_reps = dict(_cx_e.execute(
                        "SELECT * FROM sales_reps WHERE id=?", (_edit_id_sales_reps,)
                    ).fetchone() or {})
                    _cx_e.close()
                except Exception:
                    _edit_row_sales_reps = {}
                with st.expander(f"✏️ 영업사원 수정 — ID {_edit_id_sales_reps}", expanded=True):
                    if not _edit_row_sales_reps:
                        st.warning("데이터를 불러올 수 없습니다.")
                    else:
                        _skip_cols = {'id','created_at','updated_at'}
                        _edit_fields_sales_reps = [c for c in _edit_row_sales_reps if c not in _skip_cols]
                        _ncols = min(3, max(1, len(_edit_fields_sales_reps)))
                        _ecols = st.columns(_ncols)
                        _new_vals_sales_reps = {}
                        for _i, _fc in enumerate(_edit_fields_sales_reps):
                            _cv = _edit_row_sales_reps[_fc]
                            _ec = _ecols[_i % _ncols]
                            if isinstance(_cv, (int, float)) and not isinstance(_cv, bool):
                                _new_vals_sales_reps[_fc] = _ec.number_input(_fc, value=float(_cv or 0), key=f"_ef_{_edit_id_sales_reps}_{_fc}_sales_reps")
                            else:
                                _new_vals_sales_reps[_fc] = _ec.text_input(_fc, value=str(_cv or ""), key=f"_ef_{_edit_id_sales_reps}_{_fc}_sales_reps")
                        _s1, _s2 = st.columns(2)
                        if _s1.button("💾 저장", type="primary", use_container_width=True, key="_edsave_sales_reps"):
                            _set_sql = ", ".join([f"{c}=?" for c in _new_vals_sales_reps])
                            _set_params = list(_new_vals_sales_reps.values()) + [_edit_id_sales_reps]
                            _cx_s = get_db()
                            _cx_s.execute(f"UPDATE sales_reps SET {_set_sql} WHERE id=?", _set_params)
                            _cx_s.commit(); _cx_s.close()
                            st.session_state[f"_edit_sales_reps"] = None
                            st.success("✅ 수정 저장 완료!"); st.rerun()
                        if _s2.button("✖ 취소", use_container_width=True, key="_edcancel_sales_reps"):
                            st.session_state[f"_edit_sales_reps"] = None; st.rerun()

        else: st.info("없음")

        st.divider()
        st.subheader("SO에 영업사원 배정")
        conn=get_db()
        reps_active=[r[0] for r in conn.execute("SELECT rep_name FROM sales_reps WHERE status='재직'").fetchall()]
        sos_norep=[r for r in conn.execute("SELECT id,order_number,customer_name,item_name FROM sales_orders WHERE COALESCE(sales_rep,'') = '' AND status NOT IN ('취소') ORDER BY id DESC LIMIT 20").fetchall()]
        conn.close()
        if reps_active and sos_norep:
            so_norep_m={f"{r['order_number']}-{r['customer_name']}":r['id'] for r in sos_norep}
            c1,c2=st.columns(2); sel_norep=c1.selectbox("미배정 SO",list(so_norep_m.keys())); sel_rep=c2.selectbox("영업사원",reps_active)
            if st.button("배정",use_container_width=True):
                conn=get_db(); conn.execute("UPDATE sales_orders SET sales_rep=? WHERE id=?",(sel_rep,so_norep_m[sel_norep])); conn.commit(); conn.close(); st.success("배정!"); st.rerun()


# ══ 영업사원 실적 분석 ══════════════════════════════════════════
with tabs["bi_sales_rep"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        st.subheader("📊 영업사원별 실적 분석")
        conn=get_db()
        df_rep_perf=pd.read_sql_query("""
            SELECT s.sales_rep AS 영업사원,
                   COUNT(s.id) AS 수주건수,
                   ROUND(SUM(s.quantity*s.unit_price*(1-s.discount_rate/100)),0) AS 매출액,
                   ROUND(AVG(s.discount_rate),1) AS 평균할인율,
                   COUNT(CASE WHEN s.status='배송완료' THEN 1 END) AS 완료건수,
                   MAX(r.monthly_target) AS 월목표
            FROM sales_orders s
            LEFT JOIN sales_reps r ON s.sales_rep=r.rep_name
            WHERE s.sales_rep IS NOT NULL AND s.status!='취소'
            GROUP BY s.sales_rep ORDER BY 매출액 DESC""", conn)
        df_rep_crd=pd.read_sql_query("""
            SELECT sales_rep AS 영업사원,
                   COUNT(*) AS 총건,
                   SUM(CASE WHEN actual_delivery_date<=requested_delivery AND actual_delivery_date IS NOT NULL THEN 1 ELSE 0 END) AS 납기준수
            FROM sales_orders WHERE sales_rep IS NOT NULL AND status='배송완료'
            GROUP BY sales_rep""", conn)
        conn.close()

        if df_rep_perf.empty: st.info("영업사원 배정된 SO 없음")
        else:
            df_rep_perf['달성률%']=df_rep_perf.apply(lambda r: round(r['매출액']/r['월목표']*100,1) if r['월목표']>0 else 0,axis=1)
            c1,c2,c3=st.columns(3)
            c1.metric("최고 매출",df_rep_perf.iloc[0]['영업사원'])
            c2.metric("총 수주",f"{df_rep_perf['수주건수'].sum()}건")
            c3.metric("총 매출",f"₩{df_rep_perf['매출액'].sum():,.0f}")

            col_a,col_b=st.columns(2)
            with col_a:
                fig=px.bar(df_rep_perf,x='영업사원',y='매출액',color='달성률%',
                    color_continuous_scale='RdYlGn',title="영업사원별 매출액",text='달성률%')
                fig.update_traces(texttemplate='%{text:.0f}%',textposition='outside')
                fig.update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig,use_container_width=True)
            with col_b:
                fig2=px.scatter(df_rep_perf,x='수주건수',y='매출액',color='영업사원',
                    size='달성률%',title="수주건수 vs 매출액",text='영업사원')
                fig2.update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig2,use_container_width=True)

            st.dataframe(df_rep_perf,use_container_width=True,hide_index=True)
            if not df_rep_crd.empty:
                df_rep_crd['납기준수율%']=(df_rep_crd['납기준수']/df_rep_crd['총건']*100).round(1)
                st.subheader("영업사원별 납기준수율")
                st.dataframe(df_rep_crd,use_container_width=True,hide_index=True)
