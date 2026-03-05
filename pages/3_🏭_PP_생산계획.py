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

def init_pp():
    conn=get_db(); c=conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS work_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, wo_number TEXT UNIQUE NOT NULL,
        plan_id INTEGER, product_name TEXT NOT NULL, work_center TEXT,
        planned_qty INTEGER NOT NULL, actual_qty INTEGER DEFAULT 0,
        defect_qty INTEGER DEFAULT 0, start_date TEXT, end_date TEXT,
        actual_start TEXT, actual_end TEXT,
        worker TEXT, machine TEXT,
        status TEXT DEFAULT '대기', note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS routings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT NOT NULL,
        operation_seq INTEGER NOT NULL, operation_name TEXT NOT NULL,
        work_center TEXT, standard_time REAL DEFAULT 0,
        machine TEXT, note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    c.execute('''CREATE TABLE IF NOT EXISTS work_centers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, wc_code TEXT UNIQUE NOT NULL,
        wc_name TEXT NOT NULL, capacity_per_day REAL DEFAULT 8.0,
        machine_count INTEGER DEFAULT 1,
        status TEXT DEFAULT '가동', note TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')))''')
    conn.commit(); conn.close()

try: init_pp()
except: pass
_ac("production_plans","actual_qty","INTEGER DEFAULT 0")
_ac("production_plans","defect_qty","INTEGER DEFAULT 0")
_ac("production_plans","completion_rate","REAL DEFAULT 0")
_ac("bom","bom_level","INTEGER DEFAULT 1")
_ac("bom","valid_from","TEXT"); _ac("bom","valid_to","TEXT")

st.title("🏭 PP – Production Planning (생산계획/MRP)")
inject_css()
apply_plotly_theme()

main_tabs=st.tabs(["🗂️ 기준정보","📋 생산계획·WO","⚙️ MRP","📊 생산 분석"])
tabs={}
with main_tabs[0]:
    s=st.tabs(["📐 BOM","🔄 공정 라우팅","🏗️ 작업장","🔧 외주 관리"])
    tabs.update({"bom":s[0],"routing":s[1],"wc":s[2],"subcon":s[3]})
with main_tabs[1]:
    s=st.tabs(["📅 생산계획","📋 작업지시(WO)","✅ 생산실적","📊 진행 현황","🗓️ S&OP"])
    tabs.update({"plan":s[0],"wo":s[1],"result":s[2],"progress":s[3],"sop":s[4]})
with main_tabs[2]:
    s=st.tabs(["⚙️ MRP 소요량 계산","📋 발주요청(MRP)","🌳 다단계 BOM 전개"])
    tabs.update({"mrp":s[0],"mrp_req":s[1],"bom_exp":s[2]})
with main_tabs[3]:
    s=st.tabs(["📈 생산 추이","🏭 작업장 부하","🔧 품질·불량","📅 간트차트","⚙️ CRP 능력소요","🔩 OEE 설비효율"])
    tabs.update({"bi_prod":s[0],"bi_wc":s[1],"bi_qual":s[2],"gantt":s[3],"crp":s[4],"oee":s[5]})

with st.sidebar:
    st.divider(); st.markdown("### 📊 분석 기간")
    bp=st.selectbox("기간",["최근 1개월","최근 3개월","최근 6개월","최근 1년","전체"],key="pp_bp")
    bi_from=(datetime.now()-timedelta(days={"최근 1개월":30,"최근 3개월":90,"최근 6개월":180,"최근 1년":365,"전체":9999}[bp])).strftime("%Y-%m-%d")

try:
    import plotly.express as px; import plotly.graph_objects as go
    from plotly.subplots import make_subplots; HAS_PL=True
except: HAS_PL=False

def _ef(msg="데이터 없음"):
    if not HAS_PL: return None
    fig=go.Figure(); fig.add_annotation(text=msg,x=0.5,y=0.5,xref="paper",yref="paper",showarrow=False,font=dict(size=13,color="#9ca3af"))
    fig.update_layout(height=260,margin=dict(l=0,r=0,t=10,b=0),plot_bgcolor="#f9fafb",paper_bgcolor="#f9fafb"); return fig

# ══ BOM ══════════════════════════════════════════
with tabs["bom"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("BOM 등록")
        with st.form("bom_f",clear_on_submit=True):
            prod=st.text_input("완제품명 *"); comp=st.text_input("구성자재명 *"); code=st.text_input("자재코드")
            a,b,c=st.columns(3); qty=a.number_input("소요수량",min_value=0.01,value=1.0,format="%.3f"); unit=b.selectbox("단위",["EA","KG","L","M","BOX","SET"]); lv=c.number_input("BOM레벨",min_value=1,max_value=5,value=1)
            d,e=st.columns(2); vf=d.date_input("유효시작"); vt=e.date_input("유효종료",value=date(2099,12,31))
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not prod or not comp: st.error("필수 누락")
                else:
                    conn=get_db(); conn.execute("INSERT INTO bom(product_name,component_name,component_code,quantity,unit,bom_level,valid_from,valid_to) VALUES(?,?,?,?,?,?,?,?)",(prod,comp,code,qty,unit,lv,str(vf),str(vt))); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
    with col_list:
        st.subheader("BOM 목록")
        conn=get_db(); df_b=pd.read_sql_query("SELECT product_name AS 완제품,component_code AS 자재코드,component_name AS 구성자재,quantity AS 소요수량,unit AS 단위,bom_level AS 레벨,valid_from AS 유효시작,valid_to AS 유효종료 FROM bom ORDER BY product_name,bom_level,id",conn); conn.close()
        if df_b.empty: st.info("BOM 없음")
        else:
            pf=st.selectbox("완제품 필터",["전체"]+df_b['완제품'].unique().tolist())
            df_show=df_b if pf=="전체" else df_b[df_b['완제품']==pf]
            st.dataframe(df_show,use_container_width=True,hide_index=True)
            if pf!="전체":
                st.caption(f"📊 총 구성자재: {len(df_show)}종 / 총 소요수량 합계: {df_show['소요수량'].sum():.2f}")

# ══ 공정 라우팅 ══════════════════════════════════════════
with tabs["routing"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("공정 라우팅 등록")
        with st.form("rt_f",clear_on_submit=True):
            rprod=st.text_input("완제품명 *"); rseq=st.number_input("공정순서",min_value=1,value=10,step=10); rop=st.text_input("공정명 *")
            a,b=st.columns(2); rwc=a.text_input("작업장"); rmach=b.text_input("설비/기계")
            rst=st.number_input("표준작업시간(분)",min_value=0.0,format="%.1f"); rnote=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not rprod or not rop: st.error("필수 누락")
                else:
                    conn=get_db(); conn.execute("INSERT INTO routings(product_name,operation_seq,operation_name,work_center,standard_time,machine,note) VALUES(?,?,?,?,?,?,?)",(rprod,rseq,rop,rwc,rst,rmach,rnote)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
    with col_list:
        st.subheader("공정 라우팅 목록")
        conn=get_db(); df_rt=pd.read_sql_query("SELECT product_name AS 완제품,operation_seq AS 순서,operation_name AS 공정명,work_center AS 작업장,standard_time AS 표준시간_분,machine AS 설비 FROM routings ORDER BY product_name,operation_seq",conn); conn.close()
        if df_rt.empty: st.info("없음")
        else:
            rpf=st.selectbox("완제품 필터",["전체"]+df_rt['완제품'].unique().tolist())
            st.dataframe(df_rt if rpf=="전체" else df_rt[df_rt['완제품']==rpf],use_container_width=True,hide_index=True)

# ══ 작업장 ══════════════════════════════════════════
with tabs["wc"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("작업장 등록")
        with st.form("wc_f",clear_on_submit=True):
            wcc=st.text_input("작업장코드 *"); wcn=st.text_input("작업장명 *")
            a,b=st.columns(2); cap=a.number_input("일 가용시간(h)",min_value=0.0,value=8.0,format="%.1f"); mc=b.number_input("설비 대수",min_value=1,value=1)
            wcs=st.selectbox("상태",["가동","점검중","휴지"]); wcnote=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not wcc or not wcn: st.error("필수 누락")
                else:
                    try:
                        conn=get_db(); conn.execute("INSERT INTO work_centers(wc_code,wc_name,capacity_per_day,machine_count,status,note) VALUES(?,?,?,?,?,?) ON CONFLICT(wc_code) DO UPDATE SET wc_name=excluded.wc_name,capacity_per_day=excluded.capacity_per_day,machine_count=excluded.machine_count,status=excluded.status",(wcc,wcn,cap,mc,wcs,wcnote)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("작업장 목록")
        conn=get_db(); df_wc=pd.read_sql_query("SELECT wc_code AS 코드,wc_name AS 작업장명,capacity_per_day AS 일가용시간,machine_count AS 설비수,status AS 상태 FROM work_centers ORDER BY id",conn); conn.close()
        if df_wc.empty: st.info("없음")
        else: st.dataframe(df_wc,use_container_width=True,hide_index=True)

# ══ 생산계획 ══════════════════════════════════════════
with tabs["plan"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("생산계획 등록")
        conn=get_db(); wcs2=[r[0] for r in conn.execute("SELECT wc_name FROM work_centers WHERE status='가동'").fetchall()]; conn.close()
        with st.form("pp_f",clear_on_submit=True):
            pprod=st.text_input("생산품목 *")
            a,b=st.columns(2); pqty=a.number_input("계획수량",min_value=1,value=1); pwc=b.selectbox("작업장",wcs2 if wcs2 else ["직접입력"])
            c,d=st.columns(2); psd=c.date_input("시작일"); ped=d.date_input("완료예정일")
            pst=st.selectbox("상태",["계획","확정","진행중","완료","취소"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not pprod: st.error("품목 필수")
                else:
                    conn=get_db(); conn.execute("INSERT INTO production_plans(plan_number,product_name,planned_qty,start_date,end_date,work_center,status) VALUES(?,?,?,?,?,?,?)",(gen_number("PP"),pprod,pqty,str(psd),str(ped),pwc,pst)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
    with col_list:
        st.subheader("생산계획 목록")
        conn=get_db(); df_pp=pd.read_sql_query("SELECT plan_number AS 계획번호,product_name AS 품목,planned_qty AS 계획수량,actual_qty AS 실적수량,work_center AS 작업장,start_date AS 시작일,end_date AS 완료예정,status AS 상태 FROM production_plans ORDER BY id DESC",conn); conn.close()
        if df_pp.empty: st.info("없음")
        else:
            pf2=st.multiselect("상태 필터",df_pp['상태'].unique().tolist(),default=df_pp['상태'].unique().tolist())
            st.dataframe(df_pp[df_pp['상태'].isin(pf2)],use_container_width=True,hide_index=True)

# ══ 작업지시 WO ══════════════════════════════════════════
with tabs["wo"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("작업지시(WO) 생성")
        conn=get_db(); plans=conn.execute("SELECT id,plan_number,product_name,planned_qty FROM production_plans WHERE status IN ('확정','계획')").fetchall(); conn.close()
        pm={f"{p['plan_number']}-{p['product_name']}":p for p in plans}
        with st.form("wo_f",clear_on_submit=True):
            if not pm: st.warning("확정/계획 상태 생산계획 없음"); st.form_submit_button("생성",disabled=True)
            else:
                pss=st.selectbox("생산계획 *",list(pm.keys())); pd2=pm[pss]
                conn=get_db(); wcs3=[r[0] for r in conn.execute("SELECT wc_name FROM work_centers WHERE status='가동'").fetchall()]; conn.close()
                a,b=st.columns(2); woq=a.number_input("지시수량",min_value=1,value=int(pd2['planned_qty'])); wowc=b.selectbox("작업장",wcs3 if wcs3 else ["직접입력"])
                c,d=st.columns(2); wosd=c.date_input("시작일"); woed=d.date_input("완료예정")
                e,f=st.columns(2); wkr=e.text_input("작업자"); mach=f.text_input("설비")
                wost=st.selectbox("상태",["대기","작업중","완료","취소","보류"]); wonote=st.text_area("비고",height=40)
                if st.form_submit_button("✅ 생성",use_container_width=True):
                    try:
                        conn=get_db(); conn.execute("INSERT INTO work_orders(wo_number,plan_id,product_name,work_center,planned_qty,start_date,end_date,worker,machine,status,note) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(gen_number("WO"),pd2['id'],pd2['product_name'],wowc,woq,str(wosd),str(woed),wkr,mach,wost,wonote))
                        conn.execute("UPDATE production_plans SET status='진행중' WHERE id=?",(pd2['id'],)); conn.commit(); conn.close(); st.success("WO 생성!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("작업지시 목록")
        conn=get_db(); df_wo=pd.read_sql_query("SELECT wo_number AS WO번호,product_name AS 품목,work_center AS 작업장,planned_qty AS 지시수량,actual_qty AS 실적수량,defect_qty AS 불량수량,worker AS 작업자,start_date AS 시작일,end_date AS 완료예정,status AS 상태 FROM work_orders ORDER BY id DESC",conn); conn.close()
        if df_wo.empty: st.info("없음")
        else: st.dataframe(df_wo,use_container_width=True,hide_index=True)

# ══ 생산실적 ══════════════════════════════════════════
with tabs["result"]:
    st.subheader("✅ 생산실적 등록")
    conn=get_db(); wos=conn.execute("SELECT id,wo_number,product_name,planned_qty FROM work_orders WHERE status IN ('작업중','대기')").fetchall(); conn.close()
    wom={f"{w['wo_number']}-{w['product_name']}":w for w in wos}
    col_form,col_list=st.columns([1,2])
    with col_form:
        with st.form("res_f",clear_on_submit=True):
            if not wom: st.info("진행 중인 WO 없음"); st.form_submit_button("등록",disabled=True)
            else:
                wss=st.selectbox("작업지시 *",list(wom.keys())); wd=wom[wss]
                a,b=st.columns(2); aq=a.number_input("실생산수량",min_value=0,value=int(wd['planned_qty'])); dq=b.number_input("불량수량",min_value=0,value=0)
                c,d=st.columns(2); ast2=c.date_input("실제시작"); aed=d.date_input("실제완료")
                note_r=st.text_area("특이사항",height=50)
                if st.form_submit_button("✅ 실적 등록",use_container_width=True):
                    try:
                        cr=round(aq/wd['planned_qty']*100,1) if wd['planned_qty']>0 else 0
                        conn=get_db(); conn.execute("UPDATE work_orders SET actual_qty=?,defect_qty=?,actual_start=?,actual_end=?,status='완료',note=? WHERE id=?",(aq,dq,str(ast2),str(aed),note_r,wd['id']))
                        conn.execute("UPDATE production_plans SET actual_qty=actual_qty+?,defect_qty=defect_qty+?,completion_rate=? WHERE id=(SELECT plan_id FROM work_orders WHERE id=?)",(aq,dq,cr,wd['id']))
                        # 재고에 반영
                        conn.execute("UPDATE inventory SET stock_qty=stock_qty+? WHERE item_name LIKE ?",(aq-dq,f"%{wd['product_name']}%"))
                        conn.commit(); conn.close(); st.success(f"실적 등록! (달성률: {cr}%)"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("완료 실적 목록")
        conn=get_db(); df_res=pd.read_sql_query("SELECT wo_number AS WO번호,product_name AS 품목,planned_qty AS 계획,actual_qty AS 실적,defect_qty AS 불량,ROUND((actual_qty-defect_qty)*100.0/NULLIF(planned_qty,0),1) AS 달성률,actual_start AS 실제시작,actual_end AS 실제완료 FROM work_orders WHERE status='완료' ORDER BY id DESC",conn); conn.close()
        if df_res.empty: st.info("완료 실적 없음")
        else: st.dataframe(df_res,use_container_width=True,hide_index=True)

# ══ 진행 현황 ══════════════════════════════════════════
with tabs["progress"]:
    st.subheader("📊 생산 진행 현황")
    conn=get_db(); df_pg=pd.read_sql_query("SELECT p.plan_number AS 계획번호,p.product_name AS 품목,p.planned_qty AS 계획수량,COALESCE(p.actual_qty,0) AS 실적수량,COALESCE(p.defect_qty,0) AS 불량수량,p.start_date AS 시작일,p.end_date AS 완료예정,p.status AS 상태,COUNT(w.id) AS WO수 FROM production_plans p LEFT JOIN work_orders w ON p.id=w.plan_id GROUP BY p.id ORDER BY p.id DESC",conn); conn.close()
    if df_pg.empty: st.info("없음")
    else:
        # 진행율 컬럼
        df_pg['진행률%']=df_pg.apply(lambda r: round(r['실적수량']/r['계획수량']*100,1) if r['계획수량']>0 else 0, axis=1)
        c1,c2,c3=st.columns(3)
        c1.metric("총 생산계획",len(df_pg))
        c2.metric("진행중",len(df_pg[df_pg['상태']=='진행중']))
        c3.metric("완료",len(df_pg[df_pg['상태']=='완료']))
        st.dataframe(df_pg,use_container_width=True,hide_index=True)

# ══ MRP ══════════════════════════════════════════
with tabs["mrp"]:
    st.subheader("⚙️ MRP 소요량 계산")
    st.info("확정/진행중 생산계획 기반 BOM 전개 → 자재 소요량 자동 계산")
    conn=get_db()
    plans2=conn.execute("SELECT plan_number,product_name,planned_qty FROM production_plans WHERE status IN ('확정','진행중')").fetchall()
    boms2=conn.execute("SELECT product_name,component_name,component_code,quantity,unit FROM bom").fetchall()
    inv2=conn.execute("SELECT item_name,stock_qty FROM inventory").fetchall()
    conn.close()
    if not plans2: st.warning("확정/진행중 생산계획 없음")
    else:
        inv_map={i['item_name']:i['stock_qty'] for i in inv2}
        bom_map={}
        for b in boms2: bom_map.setdefault(b['product_name'],[]).append(b)
        rows=[]
        for p in plans2:
            comps=bom_map.get(p['product_name'],[])
            if not comps:
                rows.append({"계획번호":p['plan_number'],"완제품":p['product_name'],"구성자재":"BOM 없음","소요량":"-","현재고":"-","발주필요량":"확인필요"})
            for cc in comps:
                req=cc['quantity']*p['planned_qty']; stk=inv_map.get(cc['component_name'],0); need=max(0,req-stk)
                rows.append({"계획번호":p['plan_number'],"완제품":p['product_name'],"구성자재":cc['component_name'],"자재코드":cc['component_code'] or "-",f"소요량":f"{req:.2f} {cc['unit']}","현재고":stk,"발주필요량":f"🔴 {need:.2f}" if need>0 else "✅ 충족"})
        df_mrp=pd.DataFrame(rows); st.dataframe(df_mrp,use_container_width=True,hide_index=True)
        if HAS_PL:
            need_rows=[r for r in rows if "🔴" in str(r.get("발주필요량",""))]
            if need_rows: st.error(f"⚠️ 부족 자재 {len(need_rows)}건 — MRP 발주요청 탭에서 등록하세요")

# ══ MRP 발주요청 ══════════════════════════════════════════
with tabs["mrp_req"]:
    col_form,col_list=st.columns([1,2])
    with col_form:
        st.subheader("MRP 발주요청 등록")
        with st.form("mrp_f",clear_on_submit=True):
            mn=st.text_input("자재명 *"); mq=st.number_input("필요수량",min_value=1,value=1)
            a,b=st.columns(2); mrd=a.date_input("필요일"); src=b.selectbox("요청출처",["MRP자동","수동입력","생산계획연동"])
            mst=st.selectbox("상태",["요청","발주완료","입고완료","취소"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not mn: st.error("자재명 필수")
                else:
                    conn=get_db(); conn.execute("INSERT INTO mrp_requests(mrp_number,material_name,required_qty,required_date,source,status) VALUES(?,?,?,?,?,?)",(gen_number("MRP"),mn,mq,str(mrd),src,mst)); conn.commit(); conn.close(); st.success("등록!"); st.rerun()
    with col_list:
        conn=get_db(); df_mr=pd.read_sql_query("SELECT mrp_number AS MRP번호,material_name AS 자재명,required_qty AS 필요수량,required_date AS 필요일,source AS 출처,status AS 상태 FROM mrp_requests ORDER BY id DESC",conn); conn.close()
        if df_mr.empty: st.info("없음")
        else: st.dataframe(df_mr,use_container_width=True,hide_index=True)

# ══ 생산 추이 BI ══════════════════════════════════════════
with tabs["bi_prod"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        tc=conn.execute(f"SELECT COUNT(*) FROM production_plans WHERE created_at>='{bi_from}'").fetchone()[0]
        done_c=conn.execute(f"SELECT COUNT(*) FROM production_plans WHERE status='완료' AND created_at>='{bi_from}'").fetchone()[0]
        ach=conn.execute(f"SELECT ROUND(AVG((actual_qty*1.0/NULLIF(planned_qty,0))*100),1) FROM production_plans WHERE status='완료' AND created_at>='{bi_from}'").fetchone()[0] or 0
        df_rate=conn.execute(f"SELECT ROUND(SUM(defect_qty)*100.0/NULLIF(SUM(actual_qty),0),2) FROM work_orders WHERE status='완료' AND created_at>='{bi_from}'").fetchone()[0] or 0
        c1,c2,c3,c4=st.columns(4); c1.metric("생산계획수",f"{tc}건"); c2.metric("완료건수",f"{done_c}건"); c3.metric("평균달성률",f"{ach}%"); c4.metric("불량률",f"{df_rate}%",delta_color="inverse")
        df_trend=pd.read_sql_query(f"SELECT substr(created_at,1,7) AS 월,SUM(planned_qty) AS 계획수량,SUM(actual_qty) AS 실적수량 FROM production_plans WHERE created_at>='{bi_from}' GROUP BY substr(created_at,1,7) ORDER BY 월",conn)
        if not df_trend.empty:
            fig=go.Figure()
            fig.add_trace(go.Bar(x=df_trend['월'],y=df_trend['계획수량'],name='계획',marker_color='#93c5fd'))
            fig.add_trace(go.Bar(x=df_trend['월'],y=df_trend['실적수량'],name='실적',marker_color='#2563eb'))
            fig.update_layout(barmode='group',title="월별 계획 vs 실적",height=280,margin=dict(l=0,r=0,t=40,b=0),legend=dict(orientation="h",y=1.1)); st.plotly_chart(fig,use_container_width=True)
        df_pst=pd.read_sql_query("SELECT status AS 상태,COUNT(*) AS 건수 FROM production_plans GROUP BY status",conn)
        if not df_pst.empty: st.plotly_chart(px.pie(df_pst,names='상태',values='건수',title="생산계획 상태 분포",hole=0.4).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()

# ══ 작업장 부하 BI ══════════════════════════════════════════
with tabs["bi_wc"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        df_wc2=pd.read_sql_query(f"SELECT work_center AS 작업장,COUNT(*) AS WO건수,SUM(planned_qty) AS 계획수량,SUM(actual_qty) AS 실적수량,ROUND(AVG((actual_qty*1.0/NULLIF(planned_qty,0))*100),1) AS 달성률 FROM work_orders WHERE created_at>='{bi_from}' GROUP BY work_center ORDER BY WO건수 DESC",conn)
        if df_wc2.empty: st.plotly_chart(_ef("작업지시 데이터 없음"),use_container_width=True)
        else:
            col_l,col_r=st.columns(2)
            with col_l: st.plotly_chart(px.bar(df_wc2,x='작업장',y='WO건수',color='달성률',color_continuous_scale='RdYlGn',range_color=[0,100],title="작업장별 WO건수·달성률").update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
            with col_r: st.plotly_chart(px.bar(df_wc2,x='작업장',y=['계획수량','실적수량'],title="작업장별 계획·실적",barmode='group').update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
            st.dataframe(df_wc2,use_container_width=True,hide_index=True)
        conn.close()

# ══ 품질·불량 BI ══════════════════════════════════════════
with tabs["bi_qual"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        conn=get_db()
        df_dq=pd.read_sql_query(f"SELECT product_name AS 품목,SUM(planned_qty) AS 계획,SUM(actual_qty) AS 실적,SUM(defect_qty) AS 불량,ROUND(SUM(defect_qty)*100.0/NULLIF(SUM(actual_qty),0),2) AS 불량률 FROM work_orders WHERE status='완료' AND created_at>='{bi_from}' GROUP BY product_name ORDER BY 불량률 DESC",conn)
        if df_dq.empty: st.plotly_chart(_ef("완료 실적 없음"),use_container_width=True)
        else:
            st.plotly_chart(px.bar(df_dq,x='품목',y='불량률',color='불량률',color_continuous_scale='RdYlGn_r',title="품목별 불량률(%)").add_hline(y=5,line_dash="dash",line_color="red",annotation_text="기준 5%").update_layout(height=300,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
            st.dataframe(df_dq,use_container_width=True,hide_index=True)
        conn.close()

# ══ 다단계 BOM 전개 ══════════════════════════════════════════
with tabs["bom_exp"]:
    st.subheader("🌳 다단계 BOM 전개")
    st.caption("완제품 → 반제품 → 원자재 단계별 소요량 계산 (최대 5레벨)")
    conn=get_db()
    prods=[r[0] for r in conn.execute("SELECT DISTINCT product_name FROM bom ORDER BY product_name").fetchall()]
    conn.close()
    if not prods:
        st.info("BOM 없음")
    else:
        col_l,col_r=st.columns([1,3])
        with col_l:
            sel_prod=st.selectbox("완제품 선택",prods)
            top_qty=st.number_input("생산수량",min_value=1,value=1)
        with col_r:
            def expand_bom(product, qty, level=1, visited=None):
                if visited is None: visited=set()
                if product in visited or level>5: return []
                visited=visited|{product}
                conn=get_db()
                comps=conn.execute("SELECT component_name,component_code,quantity,unit,bom_level FROM bom WHERE product_name=?",(product,)).fetchall()
                conn.close()
                rows=[]
                for c in comps:
                    need=c['quantity']*qty
                    rows.append({"레벨":level,"├"+"─"*level+" "+c['component_name']:c['component_name'],
                                  "자재코드":c['component_code'] or "-","단위소요":c['quantity'],
                                  "단위":c['unit'],"총소요량":round(need,3),"_name":c['component_name']})
                    rows+=expand_bom(c['component_name'],need,level+1,visited)
                return rows
            rows=expand_bom(sel_prod,top_qty)
            if not rows:
                st.warning("BOM 구성 없음")
            else:
                df_exp=pd.DataFrame(rows)
                # 트리 표시용 들여쓰기
                df_disp=df_exp[["레벨","_name","자재코드","단위소요","단위","총소요량"]].copy()
                df_disp.columns=["레벨","구성자재","자재코드","단위소요","단위","총소요량"]
                df_disp["구성자재"]=df_disp.apply(lambda r: "  "*r["레벨"]+"└ "+r["구성자재"],axis=1)
                st.dataframe(df_disp.drop(columns=["레벨"]),use_container_width=True,hide_index=True)
                # 총 소요량 집계
                st.divider()
                st.subheader("📋 자재별 총 소요량 집계")
                agg=df_exp.groupby("_name").agg(총소요량=("총소요량","sum"),단위=("단위","first")).reset_index()
                agg.columns=["자재명","총소요량","단위"]
                conn=get_db()
                for i,row in agg.iterrows():
                    stk=conn.execute("SELECT COALESCE(stock_qty,0) FROM inventory WHERE item_name LIKE ?",(f"%{row['자재명']}%",)).fetchone()
                    agg.loc[i,"현재고"]=stk[0] if stk else 0
                conn.close()
                agg["발주필요"]=agg.apply(lambda r: max(0,r["총소요량"]-r["현재고"]),axis=1)
                agg["상태"]=agg["발주필요"].apply(lambda x: "🔴 부족" if x>0 else "✅ 충족")
                st.dataframe(agg,use_container_width=True,hide_index=True)
                short=agg[agg["발주필요"]>0]
                if not short.empty: st.error(f"⚠️ 부족 자재 {len(short)}종 — MRP 발주요청 탭에서 등록하세요")


# ══ 간트차트 ══════════════════════════════════════════
with tabs["gantt"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        st.subheader("📅 생산 일정 간트차트")
        conn=get_db()
        df_g=pd.read_sql_query("""
            SELECT p.plan_number, p.product_name AS 품목, p.work_center AS 작업장,
                   p.planned_qty AS 계획수량, p.actual_qty AS 실적수량,
                   p.start_date AS 시작일, p.end_date AS 완료예정,
                   p.status AS 상태,
                   w.wo_number, w.worker AS 작업자
            FROM production_plans p
            LEFT JOIN work_orders w ON p.id=w.plan_id
            WHERE p.start_date IS NOT NULL AND p.end_date IS NOT NULL
            ORDER BY p.start_date""", conn)
        conn.close()

        if df_g.empty:
            st.info("시작일/완료일이 입력된 생산계획 없음")
        else:
            # 기간 필터
            col_f1,col_f2,col_f3=st.columns(3)
            wcs_g=["전체"]+df_g['작업장'].dropna().unique().tolist()
            sts_g=["전체"]+df_g['상태'].unique().tolist()
            sel_wc=col_f1.selectbox("작업장",wcs_g,key="g_wc")
            sel_st=col_f2.selectbox("상태",sts_g,key="g_st")
            show_wos=col_f3.checkbox("작업지시(WO) 표시",value=True)

            df_gf=df_g.copy()
            if sel_wc!="전체": df_gf=df_gf[df_gf['작업장']==sel_wc]
            if sel_st!="전체": df_gf=df_gf[df_gf['상태']==sel_st]

            color_map={"계획":"#93c5fd","확정":"#3b82f6","진행중":"#f97316","완료":"#22c55e","취소":"#9ca3af","보류":"#eab308"}

            fig=go.Figure()
            today=datetime.now().strftime("%Y-%m-%d")
            seen=set()
            for _,r in df_gf.iterrows():
                key=r['plan_number']
                if key in seen: continue
                seen.add(key)
                color=color_map.get(r['상태'],"#6b7280")
                label=f"{r['품목']} ({r['계획수량']}개)"
                fig.add_trace(go.Bar(
                    x=[(pd.Timestamp(r['완료예정'])-pd.Timestamp(r['시작일'])).days],
                    y=[r['작업장'] or "미지정"],
                    base=[r['시작일']],
                    orientation='h',
                    name=r['상태'],
                    marker_color=color,
                    text=label,
                    textposition='inside',
                    hovertemplate=f"<b>{r['품목']}</b><br>계획: {r['시작일']} ~ {r['완료예정']}<br>수량: {r['계획수량']} / 실적: {r['실적수량']}<br>상태: {r['상태']}<extra></extra>",
                    showlegend=False
                ))
            # 오늘 기준선
            fig.add_vline(x=today, line_dash="dash", line_color="red", annotation_text="오늘")
            fig.update_xaxes(type='date')
            fig.update_layout(
                title="작업장별 생산 일정",
                height=max(300, len(df_gf['작업장'].unique())*60+100),
                margin=dict(l=0,r=0,t=40,b=0),
                xaxis_title="날짜", yaxis_title="작업장",
                plot_bgcolor="#f9fafb"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 달성률 요약
            st.subheader("달성률 현황")
            df_gf['달성률']=df_gf.apply(lambda r: round(r['실적수량']/r['계획수량']*100,1) if r['계획수량']>0 else 0, axis=1)
            st.dataframe(df_gf[['plan_number','품목','작업장','계획수량','실적수량','달성률','시작일','완료예정','상태']].rename(columns={'plan_number':'계획번호'}),
                        use_container_width=True, hide_index=True)


# ══ CRP 능력소요계획 ══════════════════════════════════════════
with tabs["crp"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        st.subheader("⚙️ CRP – 능력소요계획 (Capacity Requirements Planning)")
        st.caption("작업장별 부하 vs 가용능력 — 초과 구간 자동 탐지")
        conn=get_db()
        df_wc_cap=pd.read_sql_query("SELECT wc_name AS 작업장, capacity_per_day AS 일가용시간, machine_count AS 설비수 FROM work_centers WHERE status='가동'",conn)
        df_wo_load=pd.read_sql_query("""
            SELECT w.work_center AS 작업장, w.start_date, w.end_date,
                   w.planned_qty AS 수량, w.status,
                   COALESCE(r.standard_time,60) AS 표준시간_분
            FROM work_orders w
            LEFT JOIN routings r ON w.product_name=r.product_name
            WHERE w.status NOT IN ('취소','완료')
              AND w.start_date IS NOT NULL AND w.end_date IS NOT NULL""", conn)
        conn.close()

        if df_wc_cap.empty:
            st.info("등록된 작업장 없음")
        elif df_wo_load.empty:
            st.info("진행 중인 작업지시 없음")
        else:
            # 작업장별 일별 부하 계산
            rows_crp=[]
            for _,wo in df_wo_load.iterrows():
                try:
                    sd=pd.Timestamp(wo['start_date']); ed=pd.Timestamp(wo['end_date'])
                    days=max(1,(ed-sd).days+1)
                    daily_h=(wo['수량']*wo['표준시간_분']/60)/days
                    cap_row=df_wc_cap[df_wc_cap['작업장']==wo['작업장']]
                    cap_h=float(cap_row['일가용시간'].iloc[0]*cap_row['설비수'].iloc[0]) if not cap_row.empty else 8.0
                    for d in pd.date_range(sd,ed):
                        rows_crp.append({"날짜":d.strftime("%Y-%m-%d"),"작업장":wo['작업장'],"부하(h)":round(daily_h,2),"가용(h)":cap_h})
                except: pass

            if not rows_crp:
                st.info("CRP 계산 데이터 부족")
            else:
                df_crp=pd.DataFrame(rows_crp).groupby(['날짜','작업장','가용(h)']).sum().reset_index()
                df_crp['초과여부']=df_crp['부하(h)']>df_crp['가용(h)']
                df_crp['가동률%']=(df_crp['부하(h)']/df_crp['가용(h)']*100).round(1)

                wcs_crp=df_crp['작업장'].unique().tolist()
                sel_wc_c=st.selectbox("작업장 선택",["전체"]+wcs_crp,key="crp_wc")
                df_show=df_crp if sel_wc_c=="전체" else df_crp[df_crp['작업장']==sel_wc_c]

                # 작업장별 차트
                for wc in (wcs_crp if sel_wc_c=="전체" else [sel_wc_c]):
                    d=df_show[df_show['작업장']==wc]
                    if d.empty: continue
                    fig=go.Figure()
                    fig.add_trace(go.Bar(x=d['날짜'],y=d['부하(h)'],name='부하',
                                         marker_color=['#ef4444' if v else '#3b82f6' for v in d['초과여부']]))
                    fig.add_trace(go.Scatter(x=d['날짜'],y=d['가용(h)'],name='가용능력',
                                             mode='lines',line=dict(color='#22c55e',width=2,dash='dash')))
                    over_cnt=d['초과여부'].sum()
                    title=f"{wc} 부하 분석 {'⚠️ 초과 '+str(over_cnt)+'일' if over_cnt>0 else '✅ 정상'}"
                    fig.update_layout(title=title,height=260,margin=dict(l=0,r=0,t=40,b=0),
                                      legend=dict(orientation="h",y=1.1))
                    st.plotly_chart(fig,use_container_width=True)

                # 초과 작업장 경고
                over=df_crp[df_crp['초과여부']].groupby('작업장').agg(초과일수=('날짜','count'),최대가동률=('가동률%','max')).reset_index()
                if not over.empty:
                    st.error("⚠️ 능력 초과 작업장")
                    st.dataframe(over,use_container_width=True,hide_index=True)
                else:
                    st.success("✅ 모든 작업장 능력 범위 내")


# ══ OEE 설비효율 ══════════════════════════════════════════
with tabs["oee"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        st.subheader("🔩 OEE – 설비종합효율 (Overall Equipment Effectiveness)")
        st.caption("OEE = 가용률 × 성능률 × 품질률  |  세계 수준: 85% 이상")
        conn=get_db()
        df_wo_oee=pd.read_sql_query("""
            SELECT work_center AS 작업장, product_name AS 품목,
                   planned_qty, actual_qty, defect_qty,
                   actual_start, actual_end,
                   start_date, end_date
            FROM work_orders WHERE status='완료'
              AND actual_start IS NOT NULL AND actual_end IS NOT NULL""", conn)
        df_wc_oee=pd.read_sql_query("SELECT wc_name, capacity_per_day, machine_count FROM work_centers",conn)
        conn.close()

        if df_wo_oee.empty:
            st.info("완료된 작업지시 없음 (실제시작·완료 입력 필요)")
        else:
            rows_oee=[]
            for _,r in df_wo_oee.iterrows():
                try:
                    plan_h=(pd.Timestamp(r['end_date'])-pd.Timestamp(r['start_date'])).total_seconds()/3600
                    act_h=(pd.Timestamp(r['actual_end'])-pd.Timestamp(r['actual_start'])).total_seconds()/3600
                    if plan_h<=0 or act_h<=0: continue
                    avail=min(1.0,plan_h/max(plan_h,act_h))  # 가용률
                    perf=min(1.0,r['actual_qty']/max(r['planned_qty'],1))  # 성능률
                    qual=max(0,(r['actual_qty']-r['defect_qty'])/max(r['actual_qty'],1))  # 품질률
                    oee=round(avail*perf*qual*100,1)
                    rows_oee.append({"작업장":r['작업장'],"품목":r['품목'],
                                      "가용률%":round(avail*100,1),"성능률%":round(perf*100,1),
                                      "품질률%":round(qual*100,1),"OEE%":oee})
                except: pass

            if not rows_oee:
                st.info("OEE 계산 데이터 부족")
            else:
                df_oee=pd.DataFrame(rows_oee)
                # 작업장별 평균 OEE
                oee_avg=df_oee.groupby('작업장')[['가용률%','성능률%','품질률%','OEE%']].mean().round(1).reset_index()
                c1,c2,c3,c4=st.columns(4)
                c1.metric("평균 OEE",f"{df_oee['OEE%'].mean():.1f}%",
                          delta="세계수준" if df_oee['OEE%'].mean()>=85 else "개선필요",
                          delta_color="normal" if df_oee['OEE%'].mean()>=85 else "inverse")
                c2.metric("평균 가용률",f"{df_oee['가용률%'].mean():.1f}%")
                c3.metric("평균 성능률",f"{df_oee['성능률%'].mean():.1f}%")
                c4.metric("평균 품질률",f"{df_oee['품질률%'].mean():.1f}%")

                col_l,col_r=st.columns(2)
                with col_l:
                    fig=go.Figure()
                    for col,color in [('가용률%','#3b82f6'),('성능률%','#f97316'),('품질률%','#22c55e'),('OEE%','#8b5cf6')]:
                        fig.add_trace(go.Bar(x=oee_avg['작업장'],y=oee_avg[col],name=col,marker_color=color))
                    fig.add_hline(y=85,line_dash="dash",line_color="red",annotation_text="목표 85%")
                    fig.update_layout(barmode='group',title="작업장별 OEE",height=300,
                                      margin=dict(l=0,r=0,t=40,b=0),legend=dict(orientation="h",y=1.1))
                    st.plotly_chart(fig,use_container_width=True)
                with col_r:
                    fig2=px.scatter(df_oee,x='성능률%',y='품질률%',color='작업장',
                                    size='OEE%',text='품목',title="성능률 vs 품질률")
                    fig2.add_hline(y=85,line_dash="dot",line_color="gray")
                    fig2.add_vline(x=85,line_dash="dot",line_color="gray")
                    fig2.update_layout(height=300,margin=dict(l=0,r=0,t=40,b=0))
                    st.plotly_chart(fig2,use_container_width=True)
                st.dataframe(oee_avg,use_container_width=True,hide_index=True)

# ══ 외주 관리 ══════════════════════════════════════════
with tabs["subcon"]:
    def _ac_pp(t,c,ct="TEXT"):
        try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
        except: pass
    try:
        conn=get_db()
        conn.execute('''CREATE TABLE IF NOT EXISTS subcon_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sc_number TEXT UNIQUE NOT NULL,
            supplier TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_cost REAL DEFAULT 0,
            send_date TEXT, due_date TEXT, receive_date TEXT,
            send_qty INTEGER DEFAULT 0, receive_qty INTEGER DEFAULT 0,
            defect_qty INTEGER DEFAULT 0,
            status TEXT DEFAULT '발주',
            note TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
        conn.commit(); conn.close()
    except: pass

    col_form, col_list = st.columns([1,2])
    with col_form:
        st.subheader("🔧 외주 발주")
        conn=get_db()
        sups=[r[0] for r in conn.execute("SELECT name FROM suppliers WHERE status='활성' ORDER BY name").fetchall()]
        prods=[r[0] for r in conn.execute("SELECT DISTINCT product_name FROM bom ORDER BY product_name").fetchall()]
        conn.close()
        with st.form("sc_f", clear_on_submit=True):
            sup_sc=st.selectbox("외주 업체 *", sups if sups else ["직접입력"])
            if not sups: sup_sc=st.text_input("업체명 *")
            prod_sc=st.selectbox("외주 품목 *", prods if prods else ["직접입력"])
            if not prods: prod_sc=st.text_input("품목명 *")
            a,b=st.columns(2); qty_sc=a.number_input("발주수량",min_value=1,value=1); cost_sc=b.number_input("단가",min_value=0.0,format="%.2f")
            c,d=st.columns(2); send_sc=c.date_input("자재 발송일"); due_sc=d.date_input("납기일",value=date.today()+timedelta(days=14))
            note_sc=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 외주 발주",use_container_width=True):
                try:
                    conn=get_db()
                    conn.execute("""INSERT INTO subcon_orders(sc_number,supplier,product_name,quantity,unit_cost,send_date,due_date,status)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (gen_number("SC"),sup_sc,prod_sc,qty_sc,cost_sc,str(send_sc),str(due_sc),"발주"))
                    conn.commit(); conn.close(); st.success("외주 발주 등록!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")

        st.divider()
        st.subheader("📥 외주 입고 처리")
        conn=get_db()
        sc_open=[r for r in conn.execute("SELECT id,sc_number,supplier,product_name,quantity,receive_qty FROM subcon_orders WHERE status NOT IN ('입고완료','취소') ORDER BY due_date").fetchall()]
        conn.close()
        if sc_open:
            sc_map={f"{r['sc_number']} {r['supplier']}/{r['product_name']} ({r['quantity']-r['receive_qty']}잔량)":r for r in sc_open}
            sel_sc=st.selectbox("외주건 선택",list(sc_map.keys()))
            sc_d=sc_map[sel_sc]
            a,b=st.columns(2); recv_qty=a.number_input("입고수량",min_value=1,max_value=int(sc_d['quantity']-sc_d['receive_qty']),value=int(sc_d['quantity']-sc_d['receive_qty'])); defect_sc=b.number_input("불량수량",min_value=0,value=0)
            if st.button("✅ 입고 처리",use_container_width=True):
                try:
                    conn=get_db()
                    new_recv=sc_d['receive_qty']+recv_qty
                    new_st="입고완료" if new_recv>=sc_d['quantity'] else "일부입고"
                    conn.execute("UPDATE subcon_orders SET receive_qty=?,defect_qty=defect_qty+?,receive_date=date('now'),status=? WHERE id=?",
                        (new_recv,defect_sc,new_st,sc_d['id']))
                    # 재고 반영
                    inv=conn.execute("SELECT id FROM inventory WHERE item_name=?",(sc_d['product_name'],)).fetchone()
                    good_qty=recv_qty-defect_sc
                    if inv: conn.execute("UPDATE inventory SET stock_qty=stock_qty+? WHERE id=?",(good_qty,inv[0]))
                    else: conn.execute("INSERT INTO inventory(item_name,stock_qty) VALUES(?,?)",(sc_d['product_name'],good_qty))
                    conn.commit(); conn.close(); st.success(f"입고 처리! (양품:{good_qty} / 불량:{defect_sc})"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")

    with col_list:
        st.subheader("외주 현황")
        conn=get_db(); df_sc=pd.read_sql_query("""
            SELECT sc_number AS 외주번호, supplier AS 업체, product_name AS 품목,
                   quantity AS 발주수량, receive_qty AS 입고수량,
                   quantity-receive_qty AS 잔량,
                   unit_cost AS 단가, quantity*unit_cost AS 발주금액,
                   send_date AS 발송일, due_date AS 납기,
                   CAST(julianday(due_date)-julianday('now') AS INTEGER) AS 납기잔여,
                   defect_qty AS 불량수량, status AS 상태
            FROM subcon_orders ORDER BY due_date""", conn); conn.close()
        if df_sc.empty: st.info("외주 없음")
        else:
            overdue=df_sc[(df_sc['납기잔여']<0)&(~df_sc['상태'].isin(['입고완료','취소']))]
            if not overdue.empty: st.error(f"⚠️ 납기 초과 외주: {len(overdue)}건")
            def sc_c(r): return ['background-color:#fee2e2']*len(r) if r['납기잔여']<0 and r['상태'] not in ['입고완료','취소'] else ['']*len(r)
            st.dataframe(df_sc.style.apply(sc_c,axis=1), use_container_width=True, hide_index=True)
            c1,c2,c3=st.columns(3)
            c1.metric("진행중",len(df_sc[~df_sc['상태'].isin(['입고완료','취소'])]))
            c2.metric("납기초과",len(overdue))
            c3.metric("총 발주금액",f"₩{df_sc['발주금액'].sum():,.0f}")


# ══ S&OP (판매·운영 계획) ══════════════════════════════════════════
with tabs["sop"]:
    if not HAS_PL: st.warning("pip install plotly")
    else:
        def _ac_sop(t,c,ct="TEXT"):
            try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
            except: pass
        try:
            conn=get_db()
            conn.execute('''CREATE TABLE IF NOT EXISTS sop_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER, month INTEGER,
                product_name TEXT,
                sales_forecast INTEGER DEFAULT 0,
                production_plan INTEGER DEFAULT 0,
                inventory_target INTEGER DEFAULT 0,
                opening_stock INTEGER DEFAULT 0,
                closing_stock INTEGER DEFAULT 0,
                note TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')))''')
            conn.commit(); conn.close()
        except: pass

        st.subheader("🗓️ S&OP — 판매·운영 계획")
        st.caption("수요예측(판매) ↔ 생산계획 ↔ 재고 균형을 월별로 조정")

        col_form, col_bi = st.columns([1,2])
        with col_form:
            st.subheader("S&OP 등록")
            conn=get_db()
            prods_sop=[r[0] for r in conn.execute("SELECT DISTINCT product_name FROM production_plans ORDER BY product_name").fetchall()]
            conn.close()
            with st.form("sop_f", clear_on_submit=True):
                prod_sop=st.selectbox("품목",prods_sop if prods_sop else ["직접입력"])
                if not prods_sop: prod_sop=st.text_input("품목명 *")
                a,b=st.columns(2); yr_sop=a.number_input("연도",min_value=2020,max_value=2030,value=datetime.now().year); mo_sop=b.number_input("월",min_value=1,max_value=12,value=datetime.now().month)
                c,d=st.columns(2); fc_sop=c.number_input("수요예측",min_value=0,value=0); pp_sop=d.number_input("생산계획",min_value=0,value=0)
                e,f=st.columns(2); inv_tgt=e.number_input("목표재고",min_value=0,value=0); open_st=f.number_input("기초재고",min_value=0,value=0)
                close_st=open_st+pp_sop-fc_sop
                if close_st<0: st.error(f"⚠️ 기말재고 부족: {close_st}")
                else: st.info(f"기말재고 예상: {close_st}")
                note_sop=st.text_area("비고",height=40)
                if st.form_submit_button("✅ 저장",use_container_width=True):
                    try:
                        conn=get_db()
                        conn.execute("""INSERT OR REPLACE INTO sop_plans(year,month,product_name,sales_forecast,production_plan,inventory_target,opening_stock,closing_stock,note)
                            VALUES(?,?,?,?,?,?,?,?,?)""",
                            (yr_sop,mo_sop,prod_sop,fc_sop,pp_sop,inv_tgt,open_st,close_st,note_sop))
                        conn.commit(); conn.close(); st.success("저장!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")

        with col_bi:
            conn=get_db(); df_sop=pd.read_sql_query("""
                SELECT year AS 연도, month AS 월, product_name AS 품목,
                       sales_forecast AS 수요예측, production_plan AS 생산계획,
                       opening_stock AS 기초재고, closing_stock AS 기말재고,
                       inventory_target AS 목표재고
                FROM sop_plans ORDER BY year,month""", conn); conn.close()
            if df_sop.empty: st.info("S&OP 데이터 없음")
            else:
                prod_filter=st.selectbox("품목 필터",["전체"]+df_sop['품목'].unique().tolist(),key="sop_pf")
                df_sf=df_sop if prod_filter=="전체" else df_sop[df_sop['품목']==prod_filter]
                df_sf=df_sf.copy(); df_sf['월라벨']=df_sf['연도'].astype(str)+"-"+df_sf['월'].astype(str).str.zfill(2)

                fig=go.Figure()
                fig.add_trace(go.Bar(x=df_sf['월라벨'],y=df_sf['수요예측'],name='수요예측',marker_color='#93c5fd'))
                fig.add_trace(go.Bar(x=df_sf['월라벨'],y=df_sf['생산계획'],name='생산계획',marker_color='#6ee7b7'))
                fig.add_trace(go.Scatter(x=df_sf['월라벨'],y=df_sf['기말재고'],name='기말재고',mode='lines+markers',line=dict(color='#f97316',width=2),yaxis='y2'))
                fig.add_trace(go.Scatter(x=df_sf['월라벨'],y=df_sf['목표재고'],name='목표재고',mode='lines',line=dict(color='#ef4444',width=1,dash='dash'),yaxis='y2'))
                fig.update_layout(barmode='group',title="S&OP — 수요/생산/재고 균형",height=320,
                    margin=dict(l=0,r=0,t=40,b=0),legend=dict(orientation="h",y=1.1),
                    yaxis2=dict(overlaying='y',side='right',title='재고'))
                st.plotly_chart(fig,use_container_width=True)

                # 불균형 경고
                alerts=df_sf[df_sf['기말재고']<0]
                if not alerts.empty: st.error(f"⚠️ 재고 부족 예상 구간: {', '.join(alerts['월라벨'].tolist())}")
                st.dataframe(df_sf[['월라벨','품목','수요예측','생산계획','기초재고','기말재고','목표재고']].rename(columns={'월라벨':'월'}),
                             use_container_width=True,hide_index=True)
