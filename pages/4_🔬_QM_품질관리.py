import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number
from datetime import datetime, timedelta, date

def _ac(t,c,ct="TEXT"):
    try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
    except: pass

def init_qm():
    conn=get_db(); c=conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inspection_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT NOT NULL,
        inspection_type TEXT DEFAULT '수입검사', aql_level TEXT DEFAULT 'II',
        sample_method TEXT DEFAULT 'AQL', min_sample INTEGER DEFAULT 1,
        spec_items TEXT, pass_criteria TEXT, valid_from TEXT, valid_to TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS capa_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nc_id INTEGER,
        capa_number TEXT UNIQUE NOT NULL, action_type TEXT DEFAULT '시정조치',
        description TEXT, responsible TEXT, due_date TEXT,
        completion_date TEXT, effectiveness TEXT,
        status TEXT DEFAULT '진행중',
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS customer_complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT, complaint_number TEXT UNIQUE NOT NULL,
        customer_name TEXT, item_name TEXT NOT NULL,
        complaint_type TEXT, description TEXT,
        severity TEXT DEFAULT '보통', quantity INTEGER DEFAULT 1,
        received_date TEXT, due_date TEXT,
        root_cause TEXT, countermeasure TEXT,
        status TEXT DEFAULT '접수',
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS measuring_instruments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, instrument_code TEXT UNIQUE NOT NULL,
        instrument_name TEXT NOT NULL, serial_number TEXT,
        location TEXT, calibration_cycle INTEGER DEFAULT 12,
        last_calibration TEXT, next_calibration TEXT,
        status TEXT DEFAULT '정상',
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS inspection_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT, inspection_id INTEGER,
        spec_item TEXT NOT NULL, spec_value TEXT, actual_value TEXT,
        result TEXT DEFAULT '합격', note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    conn.commit(); conn.close()

try: init_qm()
except: pass
_ac("quality_inspections","supplier_name"); _ac("quality_inspections","po_number")
_ac("quality_inspections","lot_size","INTEGER DEFAULT 0")
_ac("nonconformance","supplier_name"); _ac("nonconformance","po_number")
_ac("nonconformance","preventive_action","TEXT"); _ac("nonconformance","closed_at","TEXT")

st.title("🔬 QM – Quality Management (품질관리)")

main_tabs=st.tabs(["📋 검사 기준","🔍 품질검사","⚠️ 부적합·CAPA","📞 고객 클레임","🔧 교정 관리","🏭 공급사 감사","📊 품질 분석"])
tabs={}
with main_tabs[0]:
    s=st.tabs(["📋 검사 계획","📝 검사 스펙"])
    tabs.update({"iplan":s[0],"spec":s[1]})
with main_tabs[1]:
    s=st.tabs(["🔍 검사 등록","📄 검사 성적서(COA)","📊 검사 이력"])
    tabs.update({"insp":s[0],"coa":s[1],"insp_hist":s[2]})
with main_tabs[2]:
    s=st.tabs(["⚠️ 부적합(NC) 등록","🔧 CAPA 관리","📋 8D 리포트","📊 부적합 현황"])
    tabs.update({"nc":s[0],"capa":s[1],"d8":s[2],"nc_stat":s[3]})
with main_tabs[3]:
    s=st.tabs(["📞 클레임 접수","📊 클레임 분석"])
    tabs.update({"claim":s[0],"bi_claim":s[1]})
with main_tabs[4]:
    s=st.tabs(["🔧 계측기 등록","⏰ 교정 일정"])
    tabs.update({"instr":s[0],"calib":s[1]})
with main_tabs[5]:
    s=st.tabs(["🔍 감사 계획","📋 감사 실시","📊 감사 결과"])
    tabs.update({"audit_plan":s[0],"audit_exec":s[1],"audit_result":s[2]})
with main_tabs[6]:
    s=st.tabs(["📊 품질 KPI","📈 불량 추이","🏭 공급사 품질","📉 SPC 관리도"])
    tabs.update({"kpi":s[0],"bi_trend":s[1],"bi_sup":s[2],"spc":s[3]})

with st.sidebar:
    st.divider(); st.markdown("### 📊 분석 기간")
    bp=st.selectbox("기간",["최근 1개월","최근 3개월","최근 6개월","최근 1년","전체"],key="qm_bp")
    bi_from=(datetime.now()-timedelta(days={"최근 1개월":30,"최근 3개월":90,"최근 6개월":180,"최근 1년":365,"전체":9999}[bp])).strftime("%Y-%m-%d")

try:
    import plotly.express as px; import plotly.graph_objects as go
    import numpy as np; from plotly.subplots import make_subplots; HAS_PL=True
except: HAS_PL=False

def _ef(msg="데이터 없음"):
    if not HAS_PL: return None
    fig=go.Figure(); fig.add_annotation(text=msg,x=0.5,y=0.5,xref="paper",yref="paper",showarrow=False,font=dict(size=13,color="#9ca3af"))
    fig.update_layout(height=260,margin=dict(l=0,r=0,t=10,b=0),plot_bgcolor="#f9fafb",paper_bgcolor="#f9fafb"); return fig

# ══ 검사 계획 ══════════════════════════════════════════
with tabs["iplan"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("검사 계획 등록")
        with st.form("ip_f",clear_on_submit=True):
            ip_item=st.text_input("품목명 *"); ip_type=st.selectbox("검사유형",["수입검사","공정검사","출하검사","반품검사","정기검사"])
            a,b=st.columns(2); ip_aql=a.selectbox("AQL 수준",["I","II","III"]); ip_sm=b.selectbox("샘플링방법",["AQL","전수","%샘플링","고정수량"])
            ip_ms=st.number_input("최소 샘플수",min_value=1,value=5)
            ip_spec=st.text_area("검사 항목 (줄바꿈으로 구분)",height=80); ip_pass=st.text_area("합격 기준",height=60)
            c,d=st.columns(2); ip_vf=c.date_input("유효시작"); ip_vt=d.date_input("유효종료",value=date(2099,12,31))
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not ip_item: st.error("품목명 필수")
                else:
                    conn=get_db(); conn.execute("INSERT INTO inspection_plans(item_name,inspection_type,aql_level,sample_method,min_sample,spec_items,pass_criteria,valid_from,valid_to) VALUES(?,?,?,?,?,?,?,?,?)",(ip_item,ip_type,ip_aql,ip_sm,ip_ms,ip_spec,ip_pass,str(ip_vf),str(ip_vt))); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
    with col_list:
        st.subheader("검사 계획 목록")
        conn=get_db(); df_ip=pd.read_sql_query("SELECT item_name AS 품목,inspection_type AS 검사유형,aql_level AS AQL,sample_method AS 샘플방법,min_sample AS 최소샘플,valid_from AS 유효시작,valid_to AS 유효종료 FROM inspection_plans ORDER BY id DESC",conn); conn.close()
        if df_ip.empty: st.info("없음")
        else: st.dataframe(df_ip,use_container_width=True,hide_index=True)

# ══ 검사 스펙 (검사계획 상세보기) ══════════════════════════
with tabs["spec"]:
    st.subheader("📝 품목별 검사 스펙 조회")
    conn=get_db(); items_ip=[r[0] for r in conn.execute("SELECT DISTINCT item_name FROM inspection_plans").fetchall()]; conn.close()
    if not items_ip: st.info("등록된 검사계획 없음")
    else:
        sel_ip=st.selectbox("품목 선택",items_ip)
        conn=get_db(); ip_data=conn.execute("SELECT * FROM inspection_plans WHERE item_name=? ORDER BY id DESC LIMIT 1",(sel_ip,)).fetchone(); conn.close()
        if ip_data:
            c1,c2,c3=st.columns(3); c1.metric("검사유형",ip_data['inspection_type']); c2.metric("AQL",ip_data['aql_level']); c3.metric("최소샘플",f"{ip_data['min_sample']}개")
            st.subheader("검사 항목")
            if ip_data['spec_items']:
                for item in ip_data['spec_items'].split('\n'):
                    if item.strip(): st.write(f"• {item.strip()}")
            st.subheader("합격 기준"); st.write(ip_data['pass_criteria'] or "-")

# ══ 검사 등록 ══════════════════════════════════════════
with tabs["insp"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("품질검사 등록")
        with st.form("qm_f",clear_on_submit=True):
            it=st.selectbox("검사유형",["수입검사","공정검사","출하검사","반품검사","정기검사"])
            item_n=st.text_input("품목명 *"); lot_n=st.text_input("LOT 번호")
            a,b,c=st.columns(3); ls=a.number_input("로트 크기",min_value=0,value=0); sq=b.number_input("샘플수량",min_value=1,value=5); pq=c.number_input("합격수량",min_value=0,value=0)
            fq=st.number_input("불합격수량",min_value=0,value=0)
            d,e=st.columns(2); sup_n=d.text_input("공급사"); po_n=e.text_input("PO번호")
            ins=st.text_input("검사자"); res=st.selectbox("검사결과",["합격","조건부합격","불합격","보류"]); note=st.text_area("비고",height=50)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not item_n: st.error("품목명 필수")
                else:
                    conn=get_db()
                    conn.execute("INSERT INTO quality_inspections(inspection_number,inspection_type,item_name,lot_number,lot_size,sample_qty,pass_qty,fail_qty,inspector,result,note,supplier_name,po_number) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(gen_number("QI"),it,item_n,lot_n,ls,sq,pq,fq,ins,res,note,sup_n,po_n))
                    if res=="불합격":
                        conn.execute("INSERT INTO nonconformance(nc_number,item_name,defect_type,quantity,severity,status,supplier_name,po_number) VALUES(?,?,?,?,?,?,?,?)",(gen_number("NC"),item_n,"검사불합격",fq,"보통","조사중",sup_n,po_n))
                    conn.commit(); conn.close(); st.success("등록!" + (" (NC 자동생성)" if res=="불합격" else "")); st.rerun()
    with col_list:
        st.subheader("검사 목록")
        conn=get_db(); df_qi=pd.read_sql_query("SELECT inspection_number AS 검사번호,inspection_type AS 유형,item_name AS 품목,lot_number AS LOT,sample_qty AS 샘플,pass_qty AS 합격,fail_qty AS 불합격,supplier_name AS 공급사,result AS 결과,inspected_at AS 일시 FROM quality_inspections ORDER BY id DESC",conn); conn.close()
        if df_qi.empty: st.info("없음")
        else:
            def cr(v): return "color:green;font-weight:bold" if v=="합격" else ("color:red;font-weight:bold" if v=="불합격" else "")
            st.dataframe(df_qi.style.map(cr,subset=['결과']),use_container_width=True,hide_index=True)

# ══ 검사 성적서 COA ══════════════════════════════════════════
with tabs["coa"]:
    st.subheader("📄 검사 성적서(COA) 조회")
    conn=get_db(); lots=[r[0] for r in conn.execute("SELECT DISTINCT lot_number FROM quality_inspections WHERE lot_number IS NOT NULL AND lot_number!=''").fetchall()]; conn.close()
    if not lots: st.info("LOT 데이터 없음")
    else:
        sel_lot=st.selectbox("LOT 선택",lots)
        conn=get_db(); coa_d=conn.execute("SELECT * FROM quality_inspections WHERE lot_number=? ORDER BY id DESC LIMIT 1",(sel_lot,)).fetchone(); conn.close()
        if coa_d:
            st.markdown(f"### 검사 성적서 (COA)")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("품목",coa_d['item_name']); c2.metric("검사유형",coa_d['inspection_type'])
            c3.metric("검사결과",coa_d['result']); c4.metric("검사자",coa_d['inspector'] or "-")
            st.divider()
            col_l,col_r=st.columns(2)
            with col_l:
                st.write(f"**LOT번호:** {coa_d['lot_number']}")
                st.write(f"**샘플수량:** {coa_d['sample_qty']}")
                st.write(f"**합격수량:** {coa_d['pass_qty']}")
                st.write(f"**불합격수량:** {coa_d['fail_qty']}")
            with col_r:
                st.write(f"**공급사:** {coa_d['supplier_name'] or '-'}")
                st.write(f"**PO번호:** {coa_d['po_number'] or '-'}")
                st.write(f"**검사일시:** {coa_d['inspected_at']}")
                st.write(f"**비고:** {coa_d['note'] or '-'}")
            # 검사 항목 결과
            conn=get_db(); res_d=pd.read_sql_query("SELECT spec_item AS 검사항목,spec_value AS 규격,actual_value AS 실측값,result AS 결과 FROM inspection_results WHERE inspection_id=?",(coa_d['id'],),conn); conn.close()
            if not res_d.empty:
                st.subheader("검사 항목별 결과")
                st.dataframe(res_d,use_container_width=True,hide_index=True)

# ══ 검사 이력 ══════════════════════════════════════════
with tabs["insp_hist"]:
    st.subheader("검사 이력 조회")
    conn=get_db()
    df_hist=pd.read_sql_query(f"SELECT inspection_number AS 검사번호,inspection_type AS 유형,item_name AS 품목,lot_number AS LOT,supplier_name AS 공급사,sample_qty AS 샘플,fail_qty AS 불합격,result AS 결과,inspected_at AS 일시 FROM quality_inspections WHERE inspected_at>='{bi_from}' ORDER BY id DESC",conn); conn.close()
    if df_hist.empty: st.info("없음")
    else:
        f_type=st.multiselect("유형 필터",df_hist['유형'].unique().tolist(),default=df_hist['유형'].unique().tolist())
        f_res=st.multiselect("결과 필터",df_hist['결과'].unique().tolist(),default=df_hist['결과'].unique().tolist())
        df_show=df_hist[df_hist['유형'].isin(f_type)&df_hist['결과'].isin(f_res)]
        st.dataframe(df_show,use_container_width=True,hide_index=True)

# ══ 부적합 NC ══════════════════════════════════════════
with tabs["nc"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("부적합(NC) 등록")
        with st.form("nc_f",clear_on_submit=True):
            ni=st.text_input("품목명 *"); nd=st.selectbox("부적합 유형",["치수불량","외관불량","기능불량","라벨불량","포장불량","오염","기타"])
            a,b=st.columns(2); nq=a.number_input("수량",min_value=1,value=1); ns=b.selectbox("심각도",["경미","보통","심각","치명적"])
            c,d=st.columns(2); nsup=c.text_input("공급사"); npo=d.text_input("PO번호")
            nrc=st.text_area("근본원인",height=60); nca=st.text_area("시정조치",height=60); npa=st.text_area("예방조치",height=50)
            nst=st.selectbox("상태",["조사중","시정조치중","검증중","종결","재발"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not ni: st.error("품목명 필수")
                else:
                    conn=get_db(); conn.execute("INSERT INTO nonconformance(nc_number,item_name,defect_type,quantity,severity,root_cause,corrective_action,preventive_action,status,supplier_name,po_number) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(gen_number("NC"),ni,nd,nq,ns,nrc,nca,npa,nst,nsup,npo)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
    with col_list:
        st.subheader("부적합 목록")
        conn=get_db(); df_nc=pd.read_sql_query("SELECT nc_number AS NC번호,item_name AS 품목,defect_type AS 유형,quantity AS 수량,severity AS 심각도,supplier_name AS 공급사,status AS 상태,created_at AS 등록일 FROM nonconformance ORDER BY id DESC",conn); conn.close()
        if df_nc.empty: st.info("없음")
        else:
            sev_c={"치명적":"background-color:#fee2e2","심각":"background-color:#fef3c7","보통":"background-color:#fefce8","경미":""}
            def sc(v): return sev_c.get(v,"")
            st.dataframe(df_nc.style.map(sc,subset=['심각도']),use_container_width=True,hide_index=True)

# ══ CAPA 관리 ══════════════════════════════════════════
with tabs["capa"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("CAPA 등록")
        conn=get_db(); ncs=conn.execute("SELECT id,nc_number,item_name FROM nonconformance WHERE status!='종결'").fetchall(); conn.close()
        nc_opts={f"{n['nc_number']}-{n['item_name']}":n['id'] for n in ncs}
        with st.form("capa_f",clear_on_submit=True):
            if not nc_opts: st.info("진행 중 NC 없음"); st.form_submit_button("등록",disabled=True)
            else:
                nc_sel=st.selectbox("NC 선택 *",list(nc_opts.keys()))
                at=st.selectbox("조치유형",["시정조치","예방조치","개선조치"]); desc=st.text_area("조치 내용 *",height=80)
                a,b=st.columns(2); resp=a.text_input("담당자"); dd=b.date_input("완료 기한")
                eff=st.text_area("효과 검증 방법",height=50); cst=st.selectbox("상태",["진행중","완료","검증중","보류"])
                if st.form_submit_button("✅ 등록",use_container_width=True):
                    if not desc: st.error("내용 필수")
                    else:
                        try:
                            conn=get_db(); conn.execute("INSERT INTO capa_actions(nc_id,capa_number,action_type,description,responsible,due_date,effectiveness,status) VALUES(?,?,?,?,?,?,?,?)",(nc_opts[nc_sel],gen_number("CAPA"),at,desc,resp,str(dd),eff,cst)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                        except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("CAPA 목록")
        conn=get_db(); df_cap=pd.read_sql_query("SELECT c.capa_number AS CAPA번호,n.nc_number AS NC번호,n.item_name AS 품목,c.action_type AS 유형,c.responsible AS 담당자,c.due_date AS 기한,c.status AS 상태 FROM capa_actions c LEFT JOIN nonconformance n ON c.nc_id=n.id ORDER BY c.id DESC",conn); conn.close()
        if df_cap.empty: st.info("없음")
        else: st.dataframe(df_cap,use_container_width=True,hide_index=True)

# ══ 부적합 현황 ══════════════════════════════════════════
with tabs["nc_stat"]:
    st.subheader("부적합 현황 분석")
    conn=get_db()
    open_nc=conn.execute("SELECT COUNT(*) FROM nonconformance WHERE status!='종결'").fetchone()[0]
    critical_nc=conn.execute("SELECT COUNT(*) FROM nonconformance WHERE severity IN ('치명적','심각') AND status!='종결'").fetchone()[0]
    c1,c2=st.columns(2); c1.metric("미결 NC",f"{open_nc}건",delta_color="inverse"); c2.metric("심각 NC",f"{critical_nc}건",delta_color="inverse")
    if HAS_PL:
        col_l,col_r=st.columns(2)
        with col_l:
            df_sev=pd.read_sql_query("SELECT severity AS 심각도,COUNT(*) AS 건수 FROM nonconformance GROUP BY severity",conn)
            cm={"치명적":"#ef4444","심각":"#f97316","보통":"#eab308","경미":"#22c55e"}
            if not df_sev.empty: st.plotly_chart(px.pie(df_sev,names='심각도',values='건수',color='심각도',color_discrete_map=cm,title="심각도별 분포",hole=0.4).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        with col_r:
            df_tp=pd.read_sql_query("SELECT defect_type AS 유형,COUNT(*) AS 건수 FROM nonconformance GROUP BY defect_type ORDER BY 건수 DESC",conn)
            if not df_tp.empty: st.plotly_chart(px.bar(df_tp,x='유형',y='건수',color='건수',color_continuous_scale='Oranges',title="불량 유형별").update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
    conn.close()

# ══ 고객 클레임 ══════════════════════════════════════════
with tabs["claim"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("클레임 접수")
        with st.form("cl_f",clear_on_submit=True):
            cn=st.text_input("고객명 *"); ci=st.text_input("품목명 *")
            a,b=st.columns(2); ct=a.selectbox("클레임유형",["품질불량","배송문제","수량오류","포장불량","기타"]); cs=b.selectbox("심각도",["경미","보통","심각","치명적"])
            cq=st.number_input("클레임 수량",min_value=1,value=1); cd=st.text_area("클레임 내용 *",height=70)
            e,f=st.columns(2); crd=e.date_input("접수일"); cdd=f.date_input("처리기한",value=date.today()+timedelta(days=14))
            crc=st.text_area("원인분석",height=50); ccm=st.text_area("대책",height=50)
            cst=st.selectbox("상태",["접수","조사중","조치중","완료","보류"])
            if st.form_submit_button("✅ 접수",use_container_width=True):
                if not cn or not ci or not cd: st.error("필수 누락")
                else:
                    try:
                        conn=get_db(); conn.execute("INSERT INTO customer_complaints(complaint_number,customer_name,item_name,complaint_type,description,severity,quantity,received_date,due_date,root_cause,countermeasure,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(gen_number("CLM"),cn,ci,ct,cd,cs,cq,str(crd),str(cdd),crc,ccm,cst)); conn.commit(); conn.close(); st.success("접수!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("클레임 목록")
        conn=get_db(); df_cl=pd.read_sql_query("SELECT complaint_number AS 클레임번호,customer_name AS 고객,item_name AS 품목,complaint_type AS 유형,severity AS 심각도,status AS 상태,received_date AS 접수일,due_date AS 기한 FROM customer_complaints ORDER BY id DESC",conn); conn.close()
        if df_cl.empty: st.info("없음")
        else:
            today_s=datetime.now().strftime("%Y-%m-%d")
            def cl_c(r): return ['background-color:#fee2e2']*len(r) if r['상태']!='완료' and str(r['기한'])<today_s else ['']*len(r)
            st.dataframe(df_cl.style.apply(cl_c,axis=1),use_container_width=True,hide_index=True)

# ══ 클레임 분석 BI ══════════════════════════════════════════
with tabs["bi_claim"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        tc=conn.execute(f"SELECT COUNT(*) FROM customer_complaints WHERE created_at>='{bi_from}'").fetchone()[0]
        oc=conn.execute(f"SELECT COUNT(*) FROM customer_complaints WHERE status!='완료' AND created_at>='{bi_from}'").fetchone()[0]
        c1,c2=st.columns(2); c1.metric("총 클레임",f"{tc}건"); c2.metric("미완료",f"{oc}건",delta_color="inverse")
        col_l,col_r=st.columns(2)
        with col_l:
            df_ct=pd.read_sql_query(f"SELECT complaint_type AS 유형,COUNT(*) AS 건수 FROM customer_complaints WHERE created_at>='{bi_from}' GROUP BY complaint_type ORDER BY 건수 DESC",conn)
            if not df_ct.empty: st.plotly_chart(px.pie(df_ct,names='유형',values='건수',title="클레임 유형",hole=0.4).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        with col_r:
            df_ctr=pd.read_sql_query(f"SELECT substr(received_date,1,7) AS 월,COUNT(*) AS 건수 FROM customer_complaints WHERE created_at>='{bi_from}' GROUP BY substr(received_date,1,7) ORDER BY 월",conn)
            if not df_ctr.empty: st.plotly_chart(px.bar(df_ctr,x='월',y='건수',title="월별 클레임",color_discrete_sequence=['#ef4444']).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()

# ══ 계측기 관리 ══════════════════════════════════════════
with tabs["instr"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("계측기 등록")
        with st.form("ins_f",clear_on_submit=True):
            ic=st.text_input("계측기 코드 *"); in2=st.text_input("계측기명 *")
            a,b=st.columns(2); sn=a.text_input("시리얼번호"); loc=b.text_input("위치")
            c,d=st.columns(2); cyc=c.number_input("교정주기(개월)",min_value=1,value=12); lc=d.date_input("최근교정일")
            nc2=lc+timedelta(days=30*cyc); st.info(f"다음교정 예정: {nc2}")
            ist=st.selectbox("상태",["정상","교정중","수리중","폐기"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not ic or not in2: st.error("필수 누락")
                else:
                    try:
                        conn=get_db(); conn.execute("INSERT INTO measuring_instruments(instrument_code,instrument_name,serial_number,location,calibration_cycle,last_calibration,next_calibration,status) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(instrument_code) DO UPDATE SET instrument_name=excluded.instrument_name,serial_number=excluded.serial_number,location=excluded.location,calibration_cycle=excluded.calibration_cycle,last_calibration=excluded.last_calibration,next_calibration=excluded.next_calibration,status=excluded.status",(ic,in2,sn,loc,cyc,str(lc),str(nc2),ist)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("계측기 목록")
        conn=get_db(); df_ins=pd.read_sql_query("SELECT instrument_code AS 코드,instrument_name AS 계측기명,serial_number AS 시리얼,location AS 위치,calibration_cycle AS 교정주기_월,last_calibration AS 최근교정,next_calibration AS 다음교정,status AS 상태 FROM measuring_instruments ORDER BY next_calibration",conn); conn.close()
        if df_ins.empty: st.info("없음")
        else:
            today_s=datetime.now().strftime("%Y-%m-%d")
            d30=(datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d")
            overdue=df_ins[df_ins['다음교정']<today_s]; soon=df_ins[(df_ins['다음교정']>=today_s)&(df_ins['다음교정']<=d30)]
            if not overdue.empty: st.error(f"🔴 교정 기한 초과: {len(overdue)}건")
            if not soon.empty: st.warning(f"🟡 30일 내 교정 예정: {len(soon)}건")
            st.dataframe(df_ins,use_container_width=True,hide_index=True)

# ══ 교정 일정 ══════════════════════════════════════════
with tabs["calib"]:
    st.subheader("⏰ 교정 일정 현황")
    conn=get_db(); df_cal=pd.read_sql_query("SELECT instrument_code AS 코드,instrument_name AS 계측기,location AS 위치,last_calibration AS 최근교정,next_calibration AS 다음교정,calibration_cycle AS 주기,CAST(julianday(next_calibration)-julianday('now') AS INTEGER) AS 잔여일,status AS 상태 FROM measuring_instruments ORDER BY next_calibration",conn); conn.close()
    if df_cal.empty: st.info("없음")
    else:
        def cal_c(r):
            if r['잔여일']<0: return ['background-color:#fee2e2']*len(r)
            if r['잔여일']<=30: return ['background-color:#fef9c3']*len(r)
            return ['']*len(r)
        st.dataframe(df_cal.style.apply(cal_c,axis=1),use_container_width=True,hide_index=True)

# ══ 품질 KPI ══════════════════════════════════════════
with tabs["kpi"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        df_qi2=pd.read_sql_query(f"SELECT result,sample_qty,fail_qty,inspection_type FROM quality_inspections WHERE inspected_at>='{bi_from}'",conn)
        ti2=len(df_qi2); pc=len(df_qi2[df_qi2['result']=='합격']) if not df_qi2.empty else 0
        pr=round(pc/ti2*100,1) if ti2 else 0; ts=df_qi2['sample_qty'].sum() if not df_qi2.empty else 0; tf=df_qi2['fail_qty'].sum() if not df_qi2.empty else 0
        dr=round(tf/ts*100,2) if ts else 0; nc_cnt=conn.execute(f"SELECT COUNT(*) FROM nonconformance WHERE created_at>='{bi_from}'").fetchone()[0]
        cl_cnt=conn.execute(f"SELECT COUNT(*) FROM customer_complaints WHERE created_at>='{bi_from}'").fetchone()[0]
        c1,c2,c3,c4=st.columns(4); c1.metric("총 검사건수",f"{ti2}건"); c2.metric("합격률",f"{pr}%",delta="양호" if pr>=95 else "주의",delta_color="normal" if pr>=95 else "inverse")
        c3.metric("불량률",f"{dr}%",delta_color="inverse"); c4.metric("클레임건수",f"{cl_cnt}건",delta_color="inverse")
        col_l,col_r=st.columns(2)
        with col_l:
            if not df_qi2.empty:
                tc2=df_qi2['inspection_type'].value_counts().reset_index(); tc2.columns=['유형','건수']
                st.plotly_chart(px.bar(tc2,x='유형',y='건수',color='건수',title="검사유형별",color_continuous_scale='Blues').update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
        with col_r:
            if not df_qi2.empty:
                rc2=df_qi2['result'].value_counts().reset_index(); rc2.columns=['결과','건수']
                clr={'합격':'#22c55e','조건부합격':'#eab308','불합격':'#ef4444','보류':'#9ca3af'}
                st.plotly_chart(px.pie(rc2,names='결과',values='건수',color='결과',color_discrete_map=clr,title="검사결과 분포",hole=0.4).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()

# ══ 불량 추이 BI ══════════════════════════════════════════
with tabs["bi_trend"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        df_tr=pd.read_sql_query(f"SELECT substr(inspected_at,1,7) AS 월,SUM(sample_qty) AS 샘플,SUM(fail_qty) AS 불합격,ROUND(SUM(fail_qty)*100.0/NULLIF(SUM(sample_qty),0),2) AS 불량률 FROM quality_inspections WHERE inspected_at>='{bi_from}' GROUP BY substr(inspected_at,1,7) ORDER BY 월",conn)
        if not df_tr.empty:
            fig=make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Bar(x=df_tr['월'],y=df_tr['샘플'],name='샘플수',marker_color='#93c5fd'),secondary_y=False)
            fig.add_trace(go.Scatter(x=df_tr['월'],y=df_tr['불량률'],name='불량률(%)',mode='lines+markers',line=dict(color='#ef4444',width=2)),secondary_y=True)
            fig.update_layout(title="월별 검사·불량률 추이",height=280,margin=dict(l=0,r=0,t=40,b=0),legend=dict(orientation="h",y=1.1)); st.plotly_chart(fig,use_container_width=True)
        else: st.plotly_chart(_ef("검사 데이터 없음"),use_container_width=True)
        conn.close()

# ══ 공급사 품질 BI ══════════════════════════════════════════
with tabs["bi_sup"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        df_sq=pd.read_sql_query(f"SELECT supplier_name AS 공급사,COUNT(*) AS 검사건수,SUM(fail_qty) AS 불합격,SUM(sample_qty) AS 샘플,ROUND(SUM(fail_qty)*100.0/NULLIF(SUM(sample_qty),0),2) AS 불량률 FROM quality_inspections WHERE supplier_name IS NOT NULL AND supplier_name!='' AND inspected_at>='{bi_from}' GROUP BY supplier_name ORDER BY 불량률 DESC",conn)
        if df_sq.empty: st.plotly_chart(_ef("공급사 검사 데이터 없음"),use_container_width=True)
        else:
            st.plotly_chart(px.bar(df_sq,x='공급사',y='불량률',color='불량률',color_continuous_scale='RdYlGn_r',title="공급사별 불량률(%)").add_hline(y=5,line_dash="dash",line_color="red",annotation_text="기준 5%").update_layout(height=300,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
            st.dataframe(df_sq,use_container_width=True,hide_index=True)
        conn.close()

# ══ SPC 관리도 ══════════════════════════════════════════
with tabs["spc"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        st.subheader("📉 SPC 관리도 (불합격률 기준)")
        st.caption("검사 이력 기반 P-관리도 — 공정 이상 탐지")
        conn=get_db()
        df_spc=pd.read_sql_query("SELECT item_name,inspected_at,sample_qty,fail_qty FROM quality_inspections WHERE sample_qty>0 ORDER BY inspected_at",conn); conn.close()
        items_spc=df_spc['item_name'].unique().tolist() if not df_spc.empty else []
        if not items_spc: st.info("검사 데이터 없음")
        else:
            sel_spc=st.selectbox("품목 선택",items_spc)
            df_s=df_spc[df_spc['item_name']==sel_spc].copy()
            if len(df_s)<5: st.warning("데이터 5건 이상 필요")
            else:
                df_s['p']=df_s['fail_qty']/df_s['sample_qty']
                p_bar=df_s['p'].mean(); n_bar=df_s['sample_qty'].mean()
                sigma=((p_bar*(1-p_bar)/n_bar)**0.5); ucl=min(1,p_bar+3*sigma); lcl=max(0,p_bar-3*sigma)
                df_s['위반']=df_s['p'].apply(lambda x: '🔴 이상' if x>ucl or x<lcl else '정상')
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=df_s['inspected_at'],y=df_s['p'],mode='lines+markers',name='불합격률',line=dict(color='#3b82f6',width=2),marker=dict(color=['#ef4444' if v=='🔴 이상' else '#3b82f6' for v in df_s['위반']],size=8)))
                fig.add_hline(y=ucl,line_dash="dash",line_color="red",annotation_text=f"UCL={ucl:.4f}")
                fig.add_hline(y=p_bar,line_dash="dot",line_color="blue",annotation_text=f"CL={p_bar:.4f}")
                fig.add_hline(y=lcl,line_dash="dash",line_color="green",annotation_text=f"LCL={lcl:.4f}")
                fig.update_layout(title=f"{sel_spc} P-관리도",height=320,margin=dict(l=0,r=0,t=40,b=0)); st.plotly_chart(fig,use_container_width=True)
                vio=df_s[df_s['위반']=='🔴 이상']
                if not vio.empty: st.error(f"⚠️ 관리한계 이탈 {len(vio)}건")

# ══ 8D 리포트 ══════════════════════════════════════════
with tabs["d8"]:
    try:
        conn=get_db()
        conn.execute('''CREATE TABLE IF NOT EXISTS d8_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            d8_number TEXT UNIQUE,
            nc_id INTEGER, claim_id INTEGER,
            title TEXT NOT NULL,
            d1_team TEXT, d2_problem TEXT, d3_containment TEXT,
            d4_root_cause TEXT, d5_corrective TEXT, d6_implementation TEXT,
            d7_prevention TEXT, d8_closure TEXT,
            status TEXT DEFAULT 'D1-팀구성',
            owner TEXT, due_date TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
        conn.commit(); conn.close()
    except: pass

    st.subheader("📋 8D 리포트 (8 Disciplines Problem Solving)")
    st.caption("D1 팀구성 → D2 문제기술 → D3 봉쇄조치 → D4 근본원인 → D5 시정조치 → D6 실행 → D7 재발방지 → D8 종결")

    col_form, col_list = st.columns([1, 2])
    with col_form:
        conn=get_db()
        ncs=[r for r in conn.execute("SELECT id,nc_number,item_name FROM nonconformance ORDER BY id DESC LIMIT 20").fetchall()]
        conn.close()
        nc_map={f"{r['nc_number']}-{r['item_name']}":r['id'] for r in ncs}
        with st.form("d8_f", clear_on_submit=True):
            title_d8=st.text_input("제목 *")
            nc_sel=st.selectbox("연결 NC",["없음"]+list(nc_map.keys()))
            owner_d8=st.text_input("책임자"); due_d8=st.date_input("완료목표일",value=date.today()+timedelta(days=30))
            st.divider()
            d1=st.text_area("D1 팀 구성",height=50,placeholder="팀원 명단, 역할")
            d2=st.text_area("D2 문제 기술",height=60,placeholder="5W1H: 무엇이/언제/어디서/누가/왜/어떻게")
            d3=st.text_area("D3 봉쇄 조치 (즉시)",height=50,placeholder="고객 피해 차단, 재공품 격리 등")
            d4=st.text_area("D4 근본 원인",height=60,placeholder="Why-Why 분석, 특성요인도")
            d5=st.text_area("D5 시정 조치 계획",height=50)
            d6=st.text_area("D6 시정 조치 실행",height=50)
            d7=st.text_area("D7 재발 방지",height=50,placeholder="표준화, 교육, FMEA 업데이트")
            d8=st.text_area("D8 종결 및 팀 인정",height=40)
            # 진행 단계 자동 계산
            steps=[d1,d2,d3,d4,d5,d6,d7,d8]
            step_names=["D1-팀구성","D2-문제기술","D3-봉쇄조치","D4-근본원인","D5-시정계획","D6-실행","D7-재발방지","D8-종결"]
            cur_step="D1-팀구성"
            for i,s2 in enumerate(steps):
                if s2.strip(): cur_step=step_names[min(i+1,7)]
            st.info(f"현재 단계: **{cur_step}**")
            if st.form_submit_button("✅ 저장",use_container_width=True):
                if not title_d8: st.error("제목 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO d8_reports(d8_number,nc_id,title,d1_team,d2_problem,d3_containment,d4_root_cause,d5_corrective,d6_implementation,d7_prevention,d8_closure,status,owner,due_date)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (gen_number("D8"),nc_map.get(nc_sel),title_d8,d1,d2,d3,d4,d5,d6,d7,d8,cur_step,owner_d8,str(due_d8)))
                        conn.commit(); conn.close(); st.success("저장!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        conn=get_db(); df_d8=pd.read_sql_query("""
            SELECT d8_number AS 번호, title AS 제목, owner AS 담당,
                   status AS 단계, due_date AS 완료목표, created_at AS 생성일
            FROM d8_reports ORDER BY id DESC""", conn); conn.close()
        if df_d8.empty: st.info("없음")
        else:
            step_order={"D1-팀구성":1,"D2-문제기술":2,"D3-봉쇄조치":3,"D4-근본원인":4,"D5-시정계획":5,"D6-실행":6,"D7-재발방지":7,"D8-종결":8}
            df_d8['진척도']=df_d8['단계'].map(lambda x: f"{step_order.get(x,0)*12.5:.0f}%")
            st.dataframe(df_d8,use_container_width=True,hide_index=True)
            # 상세 보기
            st.divider()
            sel_d8=st.selectbox("상세 보기",df_d8['번호'].tolist())
            conn=get_db(); row=conn.execute("SELECT * FROM d8_reports WHERE d8_number=?",(sel_d8,)).fetchone(); conn.close()
            if row:
                for lbl,val in [("D1 팀구성",row['d1_team']),("D2 문제기술",row['d2_problem']),("D3 봉쇄조치",row['d3_containment']),("D4 근본원인",row['d4_root_cause']),("D5 시정계획",row['d5_corrective']),("D6 실행",row['d6_implementation']),("D7 재발방지",row['d7_prevention']),("D8 종결",row['d8_closure'])]:
                    if val: st.markdown(f"**{lbl}:** {val}")


# ══ 공급사 품질 감사 ══════════════════════════════════════════
with tabs["audit_plan"]:
    try:
        conn=get_db()
        conn.execute('''CREATE TABLE IF NOT EXISTS supplier_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_number TEXT UNIQUE,
            supplier_name TEXT NOT NULL,
            audit_type TEXT DEFAULT '정기감사',
            planned_date TEXT, actual_date TEXT,
            lead_auditor TEXT, team_members TEXT,
            scope TEXT, checklist TEXT,
            status TEXT DEFAULT '계획',
            note TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS audit_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id INTEGER,
            finding_type TEXT DEFAULT '관찰사항',
            category TEXT, description TEXT,
            evidence TEXT, requirement TEXT,
            severity TEXT DEFAULT '경미',
            corrective_action TEXT, due_date TEXT,
            status TEXT DEFAULT '미조치',
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
        conn.commit(); conn.close()
    except: pass

    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("🔍 감사 계획 등록")
        conn=get_db(); sups_a=[r[0] for r in conn.execute("SELECT supplier_name FROM suppliers WHERE status='활성' ORDER BY supplier_name").fetchall()]; conn.close()
        with st.form("aud_f", clear_on_submit=True):
            sup_a=st.selectbox("공급사 *",sups_a if sups_a else ["직접입력"])
            if not sups_a: sup_a=st.text_input("공급사명 *")
            atype=st.selectbox("감사유형",["정기감사","긴급감사","신규공급사감사","재감사","시스템감사","공정감사"])
            a,b=st.columns(2); plan_d=a.date_input("계획일"); lead_a=b.text_input("주관 감사원")
            team=st.text_input("감사팀원")
            scope=st.text_area("감사 범위",height=50,placeholder="예: ISO9001 품질시스템, 공정관리, 측정관리")
            checklist=st.text_area("체크리스트",height=60,placeholder="감사 항목 목록")
            note_a=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                try:
                    conn=get_db()
                    conn.execute("INSERT INTO supplier_audits(audit_number,supplier_name,audit_type,planned_date,lead_auditor,team_members,scope,checklist,status,note) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (gen_number("AUD"),sup_a,atype,str(plan_d),lead_a,team,scope,checklist,"계획",note_a))
                    conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("감사 일정")
        conn=get_db(); df_aud=pd.read_sql_query("""
            SELECT audit_number AS 감사번호, supplier_name AS 공급사,
                   audit_type AS 유형, planned_date AS 계획일,
                   actual_date AS 실시일, lead_auditor AS 주감사원,
                   status AS 상태,
                   CAST(julianday(planned_date)-julianday('now') AS INTEGER) AS D_DAY
            FROM supplier_audits ORDER BY planned_date""", conn); conn.close()
        if df_aud.empty: st.info("없음")
        else:
            upcoming=df_aud[(df_aud['D_DAY']>=0)&(df_aud['D_DAY']<=14)]
            if not upcoming.empty: st.warning(f"⚠️ 14일 내 감사: {len(upcoming)}건")
            st.dataframe(df_aud,use_container_width=True,hide_index=True)

with tabs["audit_exec"]:
    st.subheader("📋 감사 실시 · 지적사항 등록")
    conn=get_db()
    auds=[r for r in conn.execute("SELECT id,audit_number,supplier_name,audit_type FROM supplier_audits WHERE status IN ('계획','진행중') ORDER BY planned_date").fetchall()]
    conn.close()
    if not auds: st.info("진행 가능한 감사 없음")
    else:
        aud_map={f"{r['audit_number']}-{r['supplier_name']}({r['audit_type']})":r for r in auds}
        sel_aud=st.selectbox("감사 선택",list(aud_map.keys()))
        aud_d=aud_map[sel_aud]
        c1,c2=st.columns(2)
        actual_d=c1.date_input("실시일",value=date.today())
        if c2.button("▶ 감사 시작",use_container_width=True):
            conn=get_db(); conn.execute("UPDATE supplier_audits SET status='진행중',actual_date=? WHERE id=?",(str(actual_d),aud_d['id']))
            conn.commit(); conn.close(); st.success("진행중!"); st.rerun()

        st.divider()
        st.subheader("지적사항 등록")
        with st.form("find_f", clear_on_submit=True):
            a,b=st.columns(2); ftype=a.selectbox("구분",["부적합","관찰사항","기회개선","강점"]); sev=b.selectbox("심각도",["경미","보통","심각","치명"])
            cat=st.selectbox("카테고리",["품질시스템","설계관리","구매관리","공정관리","검사측정","고객불만","문서관리","인적자원","기타"])
            desc=st.text_area("지적 내용 *",height=60); evid=st.text_area("객관적 증거",height=50); req=st.text_input("관련 요건/조항")
            ca=st.text_area("시정조치 요구사항",height=50); due_f=st.date_input("조치기한",value=date.today()+timedelta(days=30))
            if st.form_submit_button("✅ 지적사항 등록",use_container_width=True):
                if not desc: st.error("내용 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("INSERT INTO audit_findings(audit_id,finding_type,category,description,evidence,requirement,severity,corrective_action,due_date) VALUES(?,?,?,?,?,?,?,?,?)",
                            (aud_d['id'],ftype,cat,desc,evid,req,sev,ca,str(due_f)))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")

        conn=get_db(); df_find=pd.read_sql_query("SELECT finding_type AS 구분,category AS 카테고리,description AS 내용,severity AS 심각도,due_date AS 기한,status AS 상태 FROM audit_findings WHERE audit_id=? ORDER BY severity DESC",(aud_d['id'],),conn); conn.close()
        if not df_find.empty: st.dataframe(df_find,use_container_width=True,hide_index=True)

with tabs["audit_result"]:
    st.subheader("📊 감사 결과 분석")
    conn=get_db(); df_ar=pd.read_sql_query("""
        SELECT a.audit_number AS 감사번호, a.supplier_name AS 공급사,
               a.audit_type AS 유형, a.actual_date AS 실시일,
               COUNT(f.id) AS 지적건수,
               SUM(CASE f.finding_type WHEN '부적합' THEN 1 ELSE 0 END) AS 부적합,
               SUM(CASE f.severity WHEN '치명' THEN 1 ELSE 0 END) AS 치명,
               SUM(CASE f.severity WHEN '심각' THEN 1 ELSE 0 END) AS 심각,
               a.status AS 상태
        FROM supplier_audits a
        LEFT JOIN audit_findings f ON a.id=f.audit_id
        GROUP BY a.id ORDER BY a.actual_date DESC""", conn); conn.close()
    if df_ar.empty: st.info("없음")
    else:
        c1,c2,c3=st.columns(3)
        c1.metric("총 감사",len(df_ar))
        c2.metric("치명 지적",int(df_ar['치명'].sum()),delta_color="inverse")
        c3.metric("심각 지적",int(df_ar['심각'].sum()),delta_color="inverse")
        st.dataframe(df_ar,use_container_width=True,hide_index=True)
        try:
            import plotly.express as px
            fig=px.bar(df_ar,x='공급사',y=['부적합','치명','심각'],barmode='group',
                       title="공급사별 지적사항",color_discrete_map={'부적합':'#3b82f6','치명':'#ef4444','심각':'#f97316'})
            fig.update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig,use_container_width=True)
        except: pass
