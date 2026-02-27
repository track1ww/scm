import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number

st.title("🔬 QM – Quality Management (품질관리)")

tab1, tab2, tab3 = st.tabs(["🔍 품질검사", "⚠️ 부적합(NC) 관리", "📊 품질 KPI"])

# ── 품질검사 ──────────────────────────────────────────
with tab1:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("품질검사 등록")
        with st.form("qm_form", clear_on_submit=True):
            insp_type = st.selectbox("검사유형", ["수입검사","공정검사","출하검사","반품검사","정기검사"])
            item_name = st.text_input("품목명 *")
            lot_num   = st.text_input("LOT 번호")
            col_a, col_b = st.columns(2)
            sample    = col_a.number_input("샘플수량", min_value=1, value=1)
            pass_qty  = col_b.number_input("합격수량", min_value=0, value=0)
            fail_qty  = st.number_input("불합격수량", min_value=0, value=0)
            inspector = st.text_input("검사자")
            result    = st.selectbox("검사결과", ["합격","조건부합격","불합격","보류"])
            note      = st.text_area("비고", height=60)
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_name:
                    st.error("품목명 필수")
                else:
                    inum = gen_number("QI")
                    conn = get_db()
                    conn.execute("""INSERT INTO quality_inspections
                        (inspection_number,inspection_type,item_name,lot_number,
                         sample_qty,pass_qty,fail_qty,inspector,result,note)
                        VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (inum, insp_type, item_name, lot_num,
                         sample, pass_qty, fail_qty, inspector, result, note))
                    conn.commit(); conn.close()
                    st.success(f"검사 {inum} 등록!"); st.rerun()
    with col_list:
        st.subheader("검사 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT inspection_number AS 검사번호, inspection_type AS 유형,
                   item_name AS 품목, lot_number AS LOT,
                   sample_qty AS 샘플, pass_qty AS 합격,
                   fail_qty AS 불합격, inspector AS 검사자,
                   result AS 결과, inspected_at AS 검사일시
            FROM quality_inspections ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("검사 데이터 없음")
        else:
            def color_result(val):
                if val == "합격":   return "color: green; font-weight: bold"
                if val == "불합격": return "color: red; font-weight: bold"
                return ""
            st.dataframe(df.style.map(color_result, subset=['결과']),
                         use_container_width=True, hide_index=True)

# ── 부적합 관리 ──────────────────────────────────────────
with tab2:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("부적합(NC) 등록")
        with st.form("nc_form", clear_on_submit=True):
            item_name = st.text_input("품목명 *")
            defect_tp = st.selectbox("부적합 유형", ["치수불량","외관불량","기능불량","라벨불량","포장불량","기타"])
            col_a, col_b = st.columns(2)
            qty       = col_a.number_input("수량", min_value=1, value=1)
            severity  = col_b.selectbox("심각도", ["경미","보통","심각","치명적"])
            root_cause = st.text_area("근본원인", height=70)
            corrective = st.text_area("시정조치", height=70)
            status    = st.selectbox("상태", ["조사중","시정조치중","검증중","종결","재발"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_name:
                    st.error("품목명 필수")
                else:
                    nnum = gen_number("NC")
                    conn = get_db()
                    conn.execute("""INSERT INTO nonconformance
                        (nc_number,item_name,defect_type,quantity,severity,
                         root_cause,corrective_action,status)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (nnum, item_name, defect_tp, qty, severity,
                         root_cause, corrective, status))
                    conn.commit(); conn.close()
                    st.success(f"부적합 {nnum} 등록!"); st.rerun()
    with col_list:
        st.subheader("부적합 목록")
        conn = get_db()
        df = pd.read_sql_query("""
            SELECT nc_number AS NC번호, item_name AS 품목,
                   defect_type AS 유형, quantity AS 수량,
                   severity AS 심각도, status AS 상태,
                   created_at AS 등록일
            FROM nonconformance ORDER BY id DESC""", conn)
        conn.close()
        if df.empty:
            st.info("부적합 없음")
        else:
            def sev_color(val):
                colors = {"치명적":"background-color:#fee2e2","심각":"background-color:#fef3c7",
                          "보통":"background-color:#fefce8","경미":""}
                return colors.get(val, "")
            st.dataframe(df.style.map(sev_color, subset=['심각도']),
                         use_container_width=True, hide_index=True)

# ── 품질 KPI ──────────────────────────────────────────
with tab3:
    st.subheader("📊 품질 KPI")
    conn = get_db()
    df_qi = pd.read_sql_query(
        "SELECT result, sample_qty, fail_qty, inspection_type FROM quality_inspections", conn)
    df_nc = pd.read_sql_query(
        "SELECT severity, status, COUNT(*) AS cnt FROM nonconformance GROUP BY severity, status", conn)
    conn.close()

    if df_qi.empty:
        st.info("검사 데이터가 없습니다.")
    else:
        total_insp   = len(df_qi)
        pass_cnt     = len(df_qi[df_qi['result'] == '합격'])
        fail_cnt     = len(df_qi[df_qi['result'] == '불합격'])
        pass_rate    = round(pass_cnt / total_insp * 100, 1) if total_insp > 0 else 0
        total_sample = df_qi['sample_qty'].sum()
        total_fail   = df_qi['fail_qty'].sum()
        defect_rate  = round(total_fail / total_sample * 100, 2) if total_sample > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 검사건수", f"{total_insp}건")
        col2.metric("합격률", f"{pass_rate}%",
                    delta="양호" if pass_rate >= 95 else "주의", delta_color="normal")
        col3.metric("불량률(PPM 기준)", f"{defect_rate}%",
                    delta="관리필요" if defect_rate > 1 else "양호",
                    delta_color="inverse" if defect_rate > 1 else "normal")
        col4.metric("부적합 건수", len(df_nc))

        st.divider()
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("검사유형별 현황")
            type_cnt = df_qi['inspection_type'].value_counts().reset_index()
            type_cnt.columns = ['유형','건수']
            st.bar_chart(type_cnt.set_index('유형'))
        with col_r:
            st.subheader("검사결과 분포")
            res_cnt = df_qi['result'].value_counts().reset_index()
            res_cnt.columns = ['결과','건수']
            st.bar_chart(res_cnt.set_index('결과'))
