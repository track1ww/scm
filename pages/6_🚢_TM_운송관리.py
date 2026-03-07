import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number, init_trade_db
from utils.design import inject_css, apply_plotly_theme
from datetime import datetime, timedelta, date
from utils.api_client import (
    get_api_keys, save_api_key,
    fetch_bok_exchange_rates, fetch_unipass_customs_rate,
    save_exchange_rates_to_db,
    fetch_unipass_tariff, save_tariff_to_db,
    fetch_unipass_cargo_status,
    fetch_yestrade_check, check_strategic_goods_local,
    fetch_unipass_fta_rate, get_applicable_fta,
    get_latest_rates_from_db, convert_to_krw,
    FTA_AGREEMENTS_KR, SANCTIONED_COUNTRIES
)

# 수출입 테이블 초기화
init_trade_db()

st.title("🚢 TM – Transportation & Trade Management (운송/수출입 관리)")
inject_css()
apply_plotly_theme()

main_tm = st.tabs(["🔧 기준·설정", "📦 수출입 업무", "🚛 운송·결제", "📊 무역 분석"])

with main_tm[0]:
    sub0 = st.tabs(["🔑 API 설정", "💱 환율 관리", "📦 HS Code", "🌐 FTA 관리", "🏢 포워더 관리"])
    tabs = {0: sub0[0], 1: sub0[1], 2: sub0[2], 3: sub0[3], "fwd": sub0[4]}

with main_tm[1]:
    sub1 = st.tabs(["📄 CI / B/L", "📥 수입신고", "📤 수출면장", "📦 수출 P/L", "🔍 수입요건", "⚠️ 전략물자", "📜 원산지(C/O)"])
    tabs.update({4: sub1[0], 5: sub1[1], 6: sub1[2], "epl": sub1[3], 8: sub1[4], 9: sub1[5], "co": sub1[6]})

with main_tm[2]:
    sub2 = st.tabs(["💳 L/C 신용장", "💸 무역결제(T/T·D/A)", "🚛 운송오더", "📦 컨테이너", "🗺️ 운송 추적", "💰 운임 계산", "🛡️ 무역보험"])
    tabs.update({7: sub2[0], "tpay": sub2[1], 10: sub2[2], "ctn": sub2[3], "track": sub2[4], "freight": sub2[5], "ins": sub2[6]})

with main_tm[3]:
    sub3 = st.tabs(["📊 수출입 현황", "💱 환율 영향 분석", "🌍 국가별 분석", "💴 관세 납부 관리", "🔄 수출 환급금"])
    tabs.update({11: sub3[0], "bi_fx": sub3[1], "bi_country": sub3[2], "duty_pay": sub3[3], "refund": sub3[4]})

# ── 0. API 설정 ──────────────────────────────────────
with tabs[0]:
    st.subheader("🔑 외부 API 연동 설정")

    keys = get_api_keys()

    col1, col2 = st.columns(2)

    # ── 한국은행 ECOS ──────────────────
    with col1:
        st.markdown("### 🏦 한국은행 ECOS API (환율)")
        st.markdown("""
        1. [ecos.bok.or.kr](https://ecos.bok.or.kr) → **회원가입** (무료)
        2. 로그인 → **OpenAPI → 인증키 신청**
        3. 발급된 인증키를 아래에 입력
        """)
        bok_key_in = st.text_input("한국은행 API 키", value=keys.get("BOK_API_KEY",""),
                                    type="password", key="bok_in")
        if st.button("💾 저장", key="save_bok"):
            if bok_key_in:
                save_api_key("BOK_API_KEY", bok_key_in)
                st.success("저장 완료!"); st.rerun()
            else:
                st.error("키 입력 필요")
        st.divider()
        st.markdown("#### 환율 불러오기")
        if keys.get("BOK_API_KEY"):
            col_a, col_b = st.columns(2)
            bok_date = col_a.date_input("조회일", key="bok_dt")
            if col_b.button("🔄 한국은행 환율", use_container_width=True):
                with st.spinner("조회 중..."):
                    rates = fetch_bok_exchange_rates(keys["BOK_API_KEY"], bok_date.strftime("%Y%m%d"))
                if "error" in rates:
                    st.error(f"실패: {rates['error']}")
                else:
                    n = save_exchange_rates_to_db(rates, f"한국은행({bok_date})")
                    disp = {k:v for k,v in rates.items() if not k.startswith("_")}
                    st.success(f"✅ {n}개 통화 저장!")
                    st.dataframe(pd.DataFrame(list(disp.items()), columns=["통화","원화"]),
                                 use_container_width=True, hide_index=True)
                    st.rerun()
        else:
            st.info("API 키 입력 후 저장하세요")

    # ── 관세청 UNI-PASS ──────────────────
    with col2:
        st.markdown("### 🛃 관세청 UNI-PASS API (세율/통관)")
        st.markdown("""
        1. [unipass.customs.go.kr](https://unipass.customs.go.kr) → **회원가입** (무료)
        2. 로그인 → **My메뉴 → 서비스관리 → OpenAPI 사용관리 → 신청**
        3. 발급된 인증키를 아래에 입력
        """)
        uni_key_in = st.text_input("UNI-PASS API 키", value=keys.get("UNIPASS_API_KEY",""),
                                    type="password", key="uni_in")
        if st.button("💾 저장", key="save_uni"):
            if uni_key_in:
                save_api_key("UNIPASS_API_KEY", uni_key_in)
                st.success("저장 완료!"); st.rerun()
            else:
                st.error("키 입력 필요")
        st.divider()
        st.markdown("#### 과세환율 불러오기 (수출입 전용 공식환율)")
        if keys.get("UNIPASS_API_KEY"):
            imp_exp = st.radio("구분", ["수입","수출"], horizontal=True, key="imp_exp_r")
            if st.button("🔄 관세청 과세환율", use_container_width=True):
                with st.spinner("조회 중..."):
                    ie_code = "2" if imp_exp == "수입" else "1"
                    rates2 = fetch_unipass_customs_rate(keys["UNIPASS_API_KEY"], ie_code)
                if "error" in rates2:
                    st.error(f"실패: {rates2['error']}")
                else:
                    n2 = save_exchange_rates_to_db(rates2, f"관세청 과세환율({imp_exp})")
                    st.success(f"✅ {n2}개 통화 저장!")
                    st.dataframe(pd.DataFrame(list(rates2.items()), columns=["통화","과세환율"]),
                                 use_container_width=True, hide_index=True)
                    st.rerun()
        else:
            st.info("API 키 입력 후 저장하세요")

    st.divider()
    col3, col4 = st.columns(2)

    # ── UNI-PASS HS Code 세율 조회 ──────────────────
    with col3:
        st.markdown("### 📦 HS Code 세율 조회")
        if keys.get("UNIPASS_API_KEY"):
            hs_api_in = st.text_input("HS Code 입력", placeholder="예: 8471.30", key="hs_api_in")
            if st.button("🔍 세율 조회 → DB 저장", use_container_width=True, key="hs_fetch"):
                if not hs_api_in:
                    st.error("HS Code 입력 필요")
                else:
                    with st.spinner("관세청 조회 중..."):
                        res = fetch_unipass_tariff(keys["UNIPASS_API_KEY"], hs_api_in)
                    if "error" in res:
                        st.error(f"실패: {res['error']}")
                    else:
                        save_tariff_to_db(hs_api_in.replace(".","").ljust(10,"0"), res)
                        col_x, col_y, col_z = st.columns(3)
                        col_x.metric("품목", res.get("description","")[:15])
                        col_y.metric("기본관세", f"{res.get('import_duty_rate',0)}%")
                        col_z.metric("부가세", f"{res.get('vat_rate',10)}%")
                        if res.get("fta_rates"):
                            fta_df = pd.DataFrame(res["fta_rates"])
                            fta_df.columns = ["협정","세율(%)"]
                            st.dataframe(fta_df, use_container_width=True, hide_index=True)
                        st.success("✅ DB 저장 완료!"); st.rerun()
        else:
            st.info("UNI-PASS API 키 필요")

    # ── 전략물자관리원 YESTRADE ──────────────────
    with col4:
        st.markdown("### ⚠️ 전략물자관리원 YESTRADE API")
        st.markdown("""
        1. [yestrade.go.kr](https://yestrade.go.kr) → **회원가입** (무료)
        2. 로그인 → **마이페이지 → OpenAPI 신청**
        3. 발급키 입력 (없어도 내장 DB로 1차 스크리닝 가능)
        """)
        yt_key_in = st.text_input("YESTRADE API 키 (선택)", value=keys.get("YESTRADE_API_KEY",""),
                                   type="password", key="yt_in")
        if st.button("💾 저장", key="save_yt"):
            if yt_key_in:
                save_api_key("YESTRADE_API_KEY", yt_key_in)
                st.success("저장 완료!"); st.rerun()

        st.markdown("#### 전략물자 즉시 스크리닝")
        col_a2, col_b2 = st.columns(2)
        sg_hs   = col_a2.text_input("HS Code", placeholder="예: 8471.30", key="sg_hs_api")
        sg_dest = col_b2.text_input("목적국 코드", placeholder="예: US, CN, KP", key="sg_dest_api")
        if st.button("🔍 전략물자 스크리닝", use_container_width=True, key="sg_check"):
            if not sg_hs or not sg_dest:
                st.error("HS Code, 목적국 필요")
            else:
                with st.spinner("검색 중..."):
                    sg_result = fetch_yestrade_check(
                        keys.get("YESTRADE_API_KEY",""), sg_hs, sg_dest)
                risk = sg_result.get("risk_level","")
                if sg_result.get("sanction_match"):
                    st.error(f"🚨 제재국 탐지! {sg_result.get('sanction_info','')}")
                elif sg_result.get("strategic_match"):
                    st.warning(f"⚠️ 전략물자 해당 가능: {sg_result.get('description','')}")
                    st.warning(f"통제유형: {sg_result.get('control_type','')} | 위험도: {risk}")
                else:
                    st.success(f"✅ 전략물자 해당 없음 ({sg_result.get('source','')})")
                st.info(f"권고사항: {sg_result.get('recommendation','')}")

    st.divider()
    st.markdown("### 📊 API 연동 현황")
    keys_now = get_api_keys()
    status_rows = [
        {"API서비스": "한국은행 ECOS", "용도": "일별 환율 조회",
         "상태": "✅ 등록됨" if keys_now.get("BOK_API_KEY") else "❌ 미등록",
         "발급": "ecos.bok.or.kr"},
        {"API서비스": "관세청 UNI-PASS", "용도": "과세환율 / HS Code 세율 / 통관진행 조회",
         "상태": "✅ 등록됨" if keys_now.get("UNIPASS_API_KEY") else "❌ 미등록",
         "발급": "unipass.customs.go.kr"},
        {"API서비스": "YESTRADE (선택)", "용도": "전략물자 판정 (미등록 시 내장DB 사용)",
         "상태": "✅ 등록됨" if keys_now.get("YESTRADE_API_KEY") else "⚡ 내장DB 사용중",
         "발급": "yestrade.go.kr"},
    ]
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)

# ── 1. 환율 관리 ──────────────────────────────────────
with tabs[1]:
    st.subheader("💱 환율 관리")
    st.caption("실시간 연동 없이 수동 입력 방식 — 정기적으로 업데이트 필요")

    col_form, col_list = st.columns([1, 2])
    with col_form:
        with st.form("fx_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            currency  = col_a.selectbox("통화", ["USD","EUR","JPY","CNY","GBP","SGD","AUD","CAD","HKD","THB"])
            rate      = col_b.number_input("원화 환율 (1단위당 ₩)", min_value=0.01, value=1350.0, format="%.2f")
            rate_date = st.date_input("기준일")
            source    = st.text_input("출처 (예: 하나은행, 한국은행)", value="수동입력")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                try:
                    conn = get_db()
                    conn.execute("""INSERT INTO exchange_rates(currency,rate_to_krw,rate_date,source)
                        VALUES(?,?,?,?)""", (currency, rate, str(rate_date), source))
                    conn.commit(); conn.close()
                    st.success(f"{currency} 환율 등록!"); st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

    with col_list:
        st.subheader("최신 환율 현황")
        conn = get_db()
        df_fx = pd.read_sql_query("""
            SELECT currency AS 통화, rate_to_krw AS 원화환율,
                   rate_date AS 기준일, source AS 출처,
                   created_at AS 등록일시
            FROM exchange_rates
            ORDER BY currency, id DESC""", conn)
        conn.close()
        if df_fx.empty:
            st.info("환율 없음")
        else:
            # 통화별 최신값만
            latest = df_fx.groupby('통화').first().reset_index()
            st.dataframe(latest, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("💡 주요 통화 환산 계산기")
            col_c, col_d, col_e = st.columns(3)
            calc_cur = col_c.selectbox("통화", latest['통화'].tolist())
            calc_amt = col_d.number_input("금액", min_value=0.0, value=1000.0, format="%.2f")
            rate_val = latest[latest['통화']==calc_cur]['원화환율'].values
            if len(rate_val) > 0:
                krw_result = calc_amt * rate_val[0]
                col_e.metric("원화 환산", f"₩{krw_result:,.0f}")

# ── 2. HS Code ──────────────────────────────────────
with tabs[2]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("HS Code 등록")
        with st.form("hs_form", clear_on_submit=True):
            hs_code   = st.text_input("HS Code * (예: 8471.30)")
            desc      = st.text_input("품목 설명 *")
            col_a, col_b = st.columns(2)
            duty_rate = col_a.number_input("기본 관세율(%)", min_value=0.0, max_value=100.0, format="%.1f")
            vat_rate  = col_b.number_input("부가세율(%)", min_value=0.0, value=10.0, format="%.1f")
            col_c, col_d = st.columns(2)
            unit      = col_c.selectbox("단위", ["KG","EA","L","M","SET","BOX","TON"])
            notes     = col_d.text_input("특이사항")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not hs_code or not desc:
                    st.error("HS Code, 설명 필수")
                else:
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO hs_codes
                            (hs_code,description,import_duty_rate,vat_rate,unit,special_notes)
                            VALUES(?,?,?,?,?,?)
                            ON DUPLICATE KEY UPDATE
                            description=VALUES(description),
                            import_duty_rate=VALUES(import_duty_rate),
                            vat_rate=VALUES(vat_rate),
                            unit=VALUES(unit), special_notes=VALUES(special_notes)""",
                            (hs_code, desc, duty_rate, vat_rate, unit, notes))
                        conn.commit(); conn.close()
                        st.success("HS Code 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("HS Code 목록")
        conn = get_db()
        df_hs = pd.read_sql_query("""
            SELECT hs_code AS HSCode, description AS 품목설명,
                   import_duty_rate AS 관세율, vat_rate AS 부가세율,
                   unit AS 단위, special_notes AS 특이사항
            FROM hs_codes ORDER BY hs_code""", conn)
        conn.close()
        if df_hs.empty:
            st.info("HS Code 없음")
        else:
            search_hs = st.text_input("🔍 HS Code / 품목 검색")
            if search_hs:
                df_hs = df_hs[df_hs['HSCode'].str.contains(search_hs, na=False) |
                              df_hs['품목설명'].str.contains(search_hs, na=False)]
            st.dataframe(df_hs, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("💡 관세 계산기")
        conn = get_db()
        hs_list = [dict(r) for r in conn.execute("SELECT hs_code, description, import_duty_rate, vat_rate FROM hs_codes").fetchall()]
        fx_list = [dict(r) for r in conn.execute("SELECT currency, rate_to_krw FROM exchange_rates ORDER BY id DESC").fetchall()]
        conn.close()
        hs_map  = {f"{h['hs_code']} - {h['description']}": h for h in hs_list}
        fx_map  = {}
        for f in fx_list:
            if f['currency'] not in fx_map:
                fx_map[f['currency']] = f['rate_to_krw']

        if hs_map:
            col_a, col_b, col_c = st.columns(3)
            sel_hs   = col_a.selectbox("HS Code 선택", list(hs_map.keys()))
            inv_val  = col_b.number_input("인보이스 금액", min_value=0.0, value=10000.0, format="%.2f")
            sel_cur  = col_c.selectbox("통화", list(fx_map.keys()) if fx_map else ["USD"])
            if sel_hs and sel_hs in hs_map:
                hs_data  = hs_map[sel_hs]
                rate_val = fx_map.get(sel_cur, 1350)
                krw_val  = inv_val * rate_val
                duty     = krw_val * hs_data['import_duty_rate'] / 100
                vat      = (krw_val + duty) * hs_data['vat_rate'] / 100
                total_tax= duty + vat
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("과세가격(₩)", f"₩{krw_val:,.0f}")
                col2.metric(f"관세({hs_data['import_duty_rate']}%)", f"₩{duty:,.0f}")
                col3.metric(f"부가세({hs_data['vat_rate']}%)", f"₩{vat:,.0f}")
                col4.metric("총 세금", f"₩{total_tax:,.0f}")

# ── 3. FTA 관리 ──────────────────────────────────────
with tabs[3]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("FTA 협정 등록")
        with st.form("fta_form", clear_on_submit=True):
            agreement = st.selectbox("협정명", ["한-미 FTA","한-EU FTA","한-중 FTA","한-ASEAN FTA",
                                                "한-일 FTA","RCEP","CPTPP","한-영 FTA","직접입력"])
            agr_input = st.text_input("협정명 직접입력 (위에서 직접입력 선택 시)")
            partner   = st.text_input("상대국 *")
            hs_input  = st.text_input("HS Code")
            col_a, col_b = st.columns(2)
            pref_rate = col_a.number_input("협정관세율(%)", min_value=0.0, max_value=100.0, format="%.1f")
            eff_date  = col_b.date_input("발효일")
            criteria  = st.text_area("원산지 기준", height=70,
                placeholder="예: 세번변경기준(CTH), 부가가치기준 45% 이상")
            status_fta= st.selectbox("상태", ["유효","협상중","종료"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not partner:
                    st.error("상대국 필수")
                else:
                    final_agr = agr_input if agreement == "직접입력" else agreement
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO fta_agreements
                            (agreement_name,partner_country,hs_code,preferential_rate,
                             origin_criteria,effective_date,status)
                            VALUES(?,?,?,?,?,?,?)""",
                            (final_agr,partner,hs_input,pref_rate,criteria,str(eff_date),status_fta))
                        conn.commit(); conn.close()
                        st.success("FTA 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("FTA 협정 목록")
        conn = get_db()
        df_fta = pd.read_sql_query("""
            SELECT agreement_name AS 협정명, partner_country AS 상대국,
                   hs_code AS HSCode, preferential_rate AS 협정관세율,
                   origin_criteria AS 원산지기준,
                   effective_date AS 발효일, status AS 상태
            FROM fta_agreements ORDER BY agreement_name""", conn)
        conn.close()
        if df_fta.empty:
            st.info("FTA 데이터 없음")
        else:
            st.dataframe(df_fta, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("💡 FTA 적용 시뮬레이션")
        conn = get_db()
        hs_list2 = [dict(r) for r in conn.execute("SELECT hs_code, description, import_duty_rate FROM hs_codes").fetchall()]
        fx_list2 = [dict(r) for r in conn.execute("SELECT currency, rate_to_krw FROM exchange_rates ORDER BY id DESC").fetchall()]
        fta_list = [dict(r) for r in conn.execute("SELECT * FROM fta_agreements WHERE status='유효'").fetchall()]
        conn.close()
        hs_map2 = {f"{h['hs_code']} - {h['description']}": h for h in hs_list2}
        fx_map2 = {}
        for f in fx_list2:
            if f['currency'] not in fx_map2:
                fx_map2[f['currency']] = f['rate_to_krw']

        if hs_map2 and fta_list:
            col_a, col_b = st.columns(2)
            sel_hs2  = col_a.selectbox("HS Code", list(hs_map2.keys()), key="fta_hs")
            inv_val2 = col_b.number_input("인보이스(USD)", min_value=0.0, value=10000.0, format="%.2f")
            if sel_hs2 in hs_map2:
                hs_d2    = hs_map2[sel_hs2]
                rate_usd = fx_map2.get('USD', 1350)
                krw_v2   = inv_val2 * rate_usd
                normal_duty = krw_v2 * hs_d2['import_duty_rate'] / 100

                applicable = [f for f in fta_list if f['hs_code'] == hs_d2['hs_code']]
                rows = [{"구분":"일반 관세", "관세율":f"{hs_d2['import_duty_rate']}%",
                         "관세액":f"₩{normal_duty:,.0f}", "절감액":"기준"}]
                for fta in applicable:
                    fta_duty = krw_v2 * fta['preferential_rate'] / 100
                    saving   = normal_duty - fta_duty
                    rows.append({"구분":fta['agreement_name'],
                                 "관세율":f"{fta['preferential_rate']}%",
                                 "관세액":f"₩{fta_duty:,.0f}",
                                 "절감액":f"₩{saving:,.0f}"})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── 4. CI / B/L ──────────────────────────────────────
with tabs[4]:
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("상업송장(CI) 등록")
        conn = get_db()
        pos = [dict(r) for r in conn.execute("SELECT id, po_number, item_name FROM purchase_orders").fetchall()]
        hs_codes = [dict(r) for r in conn.execute("SELECT hs_code, description FROM hs_codes").fetchall()]
        conn.close()
        po_opts = {f"{p['po_number']} - {p['item_name']}": p['id'] for p in pos}
        hs_ci_opts = {"선택안함": ""};  hs_ci_opts.update({f"{h['hs_code']} - {h['description']}": h['hs_code'] for h in hs_codes})

        with st.form("ci_form", clear_on_submit=True):
            po_sel    = st.selectbox("연결 발주서", list(po_opts.keys()) if po_opts else ["없음"])
            supplier  = st.text_input("공급사명 *")
            item_name = st.text_input("품목명 *")
            hs_sel_ci = st.selectbox("HS Code", list(hs_ci_opts.keys()))
            col_a, col_b = st.columns(2)
            qty       = col_a.number_input("수량", min_value=1, value=1)
            price     = col_b.number_input("단가", min_value=0.0, format="%.2f")
            col_c, col_d = st.columns(2)
            currency  = col_c.selectbox("통화", ["USD","EUR","JPY","CNY","KRW"])
            incoterms = col_d.selectbox("인코텀즈", ["FOB","CIF","EXW","CFR","DAP","DDP","FCA","CPT"])
            origin    = st.text_input("원산지")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not supplier or not item_name:
                    st.error("공급사, 품목명 필수")
                else:
                    try:
                        ci_num = gen_number("CI")
                        conn = get_db()
                        conn.execute("""INSERT INTO commercial_invoices
                            (ci_number,po_id,supplier,item_name,quantity,unit_price,currency,origin_country)
                            VALUES(?,?,?,?,?,?,?,?)""",
                            (ci_num, po_opts.get(po_sel), supplier, item_name, qty, price, currency, origin))
                        conn.commit(); conn.close()
                        st.success(f"CI {ci_num} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

        conn = get_db()
        df_ci = pd.read_sql_query("""
            SELECT ci_number AS CI번호, supplier AS 공급사,
                   item_name AS 품목, quantity AS 수량,
                   unit_price AS 단가, currency AS 통화,
                   ROUND(quantity*unit_price,2) AS 총액, origin_country AS 원산지
            FROM commercial_invoices ORDER BY id DESC""", conn)
        conn.close()
        if not df_ci.empty:
            st.dataframe(df_ci, use_container_width=True, hide_index=True)
        else:
            st.info("CI 없음")

    with col_r:
        st.subheader("선하증권(B/L) 등록")
        conn = get_db()
        cis = [dict(r) for r in conn.execute("SELECT id, ci_number FROM commercial_invoices").fetchall()]
        conn.close()
        ci_opts = {c['ci_number']: c['id'] for c in cis}

        with st.form("bl_form", clear_on_submit=True):
            ci_sel    = st.selectbox("연결 CI", list(ci_opts.keys()) if ci_opts else ["없음"])
            transport = st.selectbox("운송방식", ["해상","항공","육상","복합"])
            carrier   = st.text_input("운송사")
            col_a, col_b = st.columns(2)
            dep_date  = col_a.date_input("출발일")
            arr_date  = col_b.date_input("도착예정일")
            col_c, col_d = st.columns(2)
            port_load = col_c.text_input("선적항")
            port_disc = col_d.text_input("양하항")
            freight   = st.number_input("운임(USD)", min_value=0.0, format="%.2f")
            status    = st.selectbox("상태", ["운송중","입항","통관중","통관완료","배송완료"])
            cleared   = st.checkbox("통관완료")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                try:
                    bl_num = gen_number("BL")
                    conn = get_db()
                    conn.execute("""INSERT INTO logistics
                        (bl_number,ci_id,transport_type,carrier,departure_date,arrival_date,
                         freight_cost,status,customs_cleared)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (bl_num, ci_opts.get(ci_sel), transport, carrier,
                         str(dep_date), str(arr_date), freight, status, 1 if cleared else 0))
                    conn.commit(); conn.close()
                    st.success(f"B/L {bl_num} 등록!"); st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

        conn = get_db()
        df_bl = pd.read_sql_query("""
            SELECT bl_number AS BL번호, transport_type AS 운송방식,
                   carrier AS 운송사, departure_date AS 출발,
                   arrival_date AS 도착예정, freight_cost AS 운임,
                   status AS 상태,
                   CASE customs_cleared WHEN 1 THEN '✅완료' ELSE '🔄대기' END AS 통관
            FROM logistics ORDER BY id DESC""", conn)
        conn.close()
        if not df_bl.empty:
            st.dataframe(df_bl, use_container_width=True, hide_index=True)
        else:
            st.info("B/L 없음")

# ── 5. 수입신고 ──────────────────────────────────────
with tabs[5]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("수입신고서 등록")
        conn = get_db()
        bls     = [dict(r) for r in conn.execute("SELECT id, bl_number FROM logistics").fetchall()]
        cis2    = [dict(r) for r in conn.execute("SELECT id, ci_number, item_name, quantity, unit_price, currency, origin_country FROM commercial_invoices").fetchall()]
        hs_all  = [dict(r) for r in conn.execute("SELECT hs_code, description, import_duty_rate, vat_rate FROM hs_codes").fetchall()]
        fta_all = [dict(r) for r in conn.execute("SELECT agreement_name, partner_country, hs_code, preferential_rate FROM fta_agreements WHERE status='유효'").fetchall()]
        fx_all  = [dict(r) for r in conn.execute("SELECT currency, rate_to_krw FROM exchange_rates ORDER BY id DESC").fetchall()]
        conn.close()
        bl_opts  = {b['bl_number']: b['id'] for b in bls}
        ci2_opts = {f"{c['ci_number']} - {c['item_name']}": c for c in cis2}
        hs_all_map = {f"{h['hs_code']} - {h['description']}": h for h in hs_all}
        fx_all_map = {}
        for f in fx_all:
            if f['currency'] not in fx_all_map:
                fx_all_map[f['currency']] = f['rate_to_krw']

        with st.form("imp_form", clear_on_submit=True):
            bl_sel   = st.selectbox("연결 B/L", list(bl_opts.keys()) if bl_opts else ["없음"])
            ci2_sel  = st.selectbox("연결 CI", list(ci2_opts.keys()) if ci2_opts else ["없음"])

            # CI 선택 시 자동 채우기
            if ci2_opts and ci2_sel in ci2_opts:
                ci_d = ci2_opts[ci2_sel]
                auto_item = ci_d['item_name']
                auto_qty  = ci_d['quantity']
                auto_val  = ci_d['quantity'] * ci_d['unit_price']
                auto_cur  = ci_d['currency']
                auto_origin = ci_d['origin_country'] or ""
            else:
                auto_item, auto_qty, auto_val, auto_cur, auto_origin = "", 1, 0.0, "USD", ""

            item_imp = st.text_input("품목명", value=auto_item)
            hs_sel_imp = st.selectbox("HS Code *", list(hs_all_map.keys()) if hs_all_map else ["없음"])
            col_a, col_b, col_c = st.columns(3)
            qty_imp   = col_a.number_input("수량", min_value=0.0, value=float(auto_qty), format="%.2f")
            inv_val   = col_b.number_input("인보이스금액", min_value=0.0, value=float(auto_val), format="%.2f")
            cur_imp   = col_c.selectbox("통화", ["USD","EUR","JPY","CNY","KRW"],
                                         index=["USD","EUR","JPY","CNY","KRW"].index(auto_cur) if auto_cur in ["USD","EUR","JPY","CNY","KRW"] else 0)
            origin_imp = st.text_input("원산지", value=auto_origin)

            # 관세 자동 계산
            if hs_sel_imp in hs_all_map:
                hs_d_imp  = hs_all_map[hs_sel_imp]
                ex_rate   = fx_all_map.get(cur_imp, 1350)
                krw_val_imp = inv_val * ex_rate
                duty_imp  = krw_val_imp * hs_d_imp['import_duty_rate'] / 100
                vat_imp   = (krw_val_imp + duty_imp) * hs_d_imp['vat_rate'] / 100
                total_tax_imp = duty_imp + vat_imp
                st.info(f"과세가격: ₩{krw_val_imp:,.0f} | 관세: ₩{duty_imp:,.0f} | 부가세: ₩{vat_imp:,.0f} | **총세금: ₩{total_tax_imp:,.0f}**")
            else:
                ex_rate = krw_val_imp = duty_imp = vat_imp = total_tax_imp = 0

            # FTA 적용
            fta_applicable = [f for f in fta_all if hs_all_map.get(hs_sel_imp,{}).get('hs_code','') == f['hs_code']]
            fta_apply = st.checkbox("FTA 적용")
            fta_sel_imp = None
            if fta_apply and fta_applicable:
                fta_opts_imp = {f"{f['agreement_name']} ({f['partner_country']}) - {f['preferential_rate']}%": f for f in fta_applicable}
                fta_sel_key  = st.selectbox("적용 FTA", list(fta_opts_imp.keys()))
                fta_sel_imp  = fta_opts_imp.get(fta_sel_key)
                if fta_sel_imp:
                    fta_duty = krw_val_imp * fta_sel_imp['preferential_rate'] / 100
                    fta_vat  = (krw_val_imp + fta_duty) * (hs_all_map.get(hs_sel_imp,{}).get('vat_rate',10)) / 100
                    st.success(f"FTA 적용 시 → 관세: ₩{fta_duty:,.0f} | 절감: ₩{duty_imp-fta_duty:,.0f}")

            col_d2, col_e2 = st.columns(2)
            decl_date  = col_d2.date_input("신고일")
            clear_date = col_e2.date_input("수리(통관)일")
            customs_ref= st.text_input("관세청 신고번호")
            imp_req    = st.text_input("수입요건 (검역/인증 등)")
            status_imp = st.selectbox("상태", ["신고대기","심사중","수리완료","보류","반려"])

            if st.form_submit_button("✅ 수입신고 등록", use_container_width=True):
                if not item_imp:
                    st.error("품목명 필수")
                else:
                    try:
                        dnum = gen_number("IMP")
                        hs_code_val = hs_all_map.get(hs_sel_imp, {}).get('hs_code', '') if hs_sel_imp in hs_all_map else ''
                        final_duty = fta_sel_imp['preferential_rate']/100*krw_val_imp if (fta_apply and fta_sel_imp) else duty_imp
                        final_agr  = fta_sel_imp['agreement_name'] if (fta_apply and fta_sel_imp) else None
                        conn = get_db()
                        conn.execute("""INSERT INTO import_declarations
                            (decl_number,bl_id,ci_id,hs_code,item_name,quantity,invoice_value,
                             currency,exchange_rate,krw_value,customs_duty,vat_amount,total_tax,
                             fta_applied,fta_agreement,origin_country,import_requirement,
                             declaration_date,clearance_date,customs_ref,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (dnum,
                             bl_opts.get(bl_sel), ci2_opts[ci2_sel]['id'] if (ci2_opts and ci2_sel in ci2_opts) else None,
                             hs_code_val, item_imp, qty_imp, inv_val, cur_imp,
                             ex_rate, krw_val_imp, final_duty, vat_imp, final_duty+vat_imp,
                             1 if (fta_apply and fta_sel_imp) else 0, final_agr,
                             origin_imp, imp_req, str(decl_date), str(clear_date),
                             customs_ref, status_imp))
                        conn.commit(); conn.close()
                        st.success(f"수입신고 {dnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("수입신고 목록")
        conn = get_db()
        df_imp = pd.read_sql_query("""
            SELECT decl_number AS 신고번호, hs_code AS HSCode,
                   item_name AS 품목, quantity AS 수량,
                   invoice_value AS 인보이스,  currency AS 통화,
                   krw_value AS 과세가격,
                   customs_duty AS 관세, vat_amount AS 부가세,
                   total_tax AS 총세금,
                   CASE fta_applied WHEN 1 THEN '✅적용' ELSE '-' END AS FTA,
                   fta_agreement AS FTA협정,
                   origin_country AS 원산지,
                   customs_ref AS 신고번호관세청,
                   status AS 상태
            FROM import_declarations ORDER BY id DESC""", conn)
        conn.close()
        if df_imp.empty:
            st.info("수입신고 없음")
        else:
            st.dataframe(df_imp, use_container_width=True, hide_index=True)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("총 관세", f"₩{df_imp['관세'].sum():,.0f}")
            col_m2.metric("총 부가세", f"₩{df_imp['부가세'].sum():,.0f}")
            col_m3.metric("총 세금합계", f"₩{df_imp['총세금'].sum():,.0f}")

# ── 6. 수출면장 ──────────────────────────────────────
with tabs[6]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("수출신고서(수출면장) 등록")
        conn = get_db()
        hs_exp = [dict(r) for r in conn.execute("SELECT hs_code, description FROM hs_codes").fetchall()]
        conn.close()
        hs_exp_map = {"선택안함": ""}
        hs_exp_map.update({f"{h['hs_code']} - {h['description']}": h['hs_code'] for h in hs_exp})

        with st.form("exp_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            exporter   = col_a.text_input("수출자 *")
            consignee  = col_b.text_input("수하인(해외) *")
            dest_country = st.text_input("목적국 *")
            hs_sel_exp = st.selectbox("HS Code", list(hs_exp_map.keys()))
            item_exp   = st.text_input("품목명 *")
            col_c, col_d, col_e = st.columns(3)
            qty_exp    = col_c.number_input("수량", min_value=0.0, value=1.0, format="%.2f")
            inv_exp    = col_d.number_input("인보이스금액", min_value=0.0, format="%.2f")
            cur_exp    = col_e.selectbox("통화", ["USD","EUR","JPY","CNY","KRW"])
            col_f, col_g = st.columns(2)
            incoterms_exp = col_f.selectbox("인코텀즈", ["FOB","CIF","EXW","CFR","DAP","DDP","FCA"])
            port_load_exp = col_g.text_input("선적항")
            port_disc_exp = st.text_input("양하항(목적항)")
            exp_license   = st.text_input("수출허가번호 (해당 시)")
            col_h, col_i = st.columns(2)
            decl_date_exp  = col_h.date_input("신고일")
            clear_date_exp = col_i.date_input("수리일")
            customs_ref_exp= st.text_input("관세청 신고번호")
            status_exp     = st.selectbox("상태", ["신고대기","심사중","수리완료","선적완료","반려"])

            if st.form_submit_button("✅ 수출신고 등록", use_container_width=True):
                if not exporter or not consignee or not dest_country or not item_exp:
                    st.error("수출자, 수하인, 목적국, 품목명 필수")
                else:
                    try:
                        exp_num = gen_number("EXP")
                        conn = get_db()
                        conn.execute("""INSERT INTO export_declarations
                            (decl_number,exporter,consignee,destination_country,hs_code,
                             item_name,quantity,invoice_value,currency,incoterms,
                             port_of_loading,port_of_discharge,export_license,
                             declaration_date,clearance_date,customs_ref,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (exp_num,exporter,consignee,dest_country,
                             hs_exp_map.get(hs_sel_exp,""),
                             item_exp,qty_exp,inv_exp,cur_exp,incoterms_exp,
                             port_load_exp,port_disc_exp,exp_license,
                             str(decl_date_exp),str(clear_date_exp),
                             customs_ref_exp,status_exp))
                        conn.commit(); conn.close()
                        st.success(f"수출신고 {exp_num} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("수출신고 목록")
        conn = get_db()
        df_exp = pd.read_sql_query("""
            SELECT decl_number AS 신고번호, exporter AS 수출자,
                   consignee AS 수하인, destination_country AS 목적국,
                   hs_code AS HSCode, item_name AS 품목,
                   quantity AS 수량, invoice_value AS 금액,
                   currency AS 통화, incoterms AS 인코텀즈,
                   port_of_loading AS 선적항,
                   customs_ref AS 관세청번호, status AS 상태
            FROM export_declarations ORDER BY id DESC""", conn)
        conn.close()
        if df_exp.empty:
            st.info("수출신고 없음")
        else:
            st.dataframe(df_exp, use_container_width=True, hide_index=True)
            st.metric("총 수출건수", len(df_exp))

# ── 7. L/C 신용장 ──────────────────────────────────────
with tabs[7]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("L/C (신용장) 등록")
        with st.form("lc_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            lc_type    = col_a.selectbox("신용장 유형", ["취소불능","취소가능","확인","양도가능","회전","기타"])
            currency_lc= col_b.selectbox("통화", ["USD","EUR","JPY","CNY"])
            col_c, col_d = st.columns(2)
            issuing_bank = col_c.text_input("개설은행 *")
            advising_bank= col_d.text_input("통지은행")
            col_e, col_f = st.columns(2)
            applicant  = col_e.text_input("개설의뢰인(수입자) *")
            beneficiary= col_f.text_input("수익자(수출자) *")
            amount_lc  = st.number_input("L/C 금액 *", min_value=0.0, format="%.2f")
            col_g, col_h = st.columns(2)
            expiry     = col_g.date_input("유효기간")
            ship_date  = col_h.date_input("선적기한")
            col_i, col_j = st.columns(2)
            incoterms_lc  = col_i.selectbox("인코텀즈", ["FOB","CIF","EXW","CFR","DAP"])
            port_load_lc  = col_j.text_input("선적항")
            port_disc_lc  = st.text_input("양하항")
            col_k, col_l2 = st.columns(2)
            partial    = col_k.selectbox("분할선적", ["불허","허용"])
            transship  = col_l2.selectbox("환적", ["불허","허용"])
            docs_req   = st.text_area("요구서류", height=70,
                placeholder="예: 상업송장 3부, 포장명세서, 선하증권 전통, 원산지증명서")
            status_lc  = st.selectbox("상태", ["개설","통지","선적","네고","결제완료","만료"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not issuing_bank or not applicant or not beneficiary or amount_lc == 0:
                    st.error("개설은행, 개설의뢰인, 수익자, 금액 필수")
                else:
                    try:
                        lc_num = gen_number("LC")
                        conn = get_db()
                        conn.execute("""INSERT INTO letters_of_credit
                            (lc_number,lc_type,issuing_bank,advising_bank,applicant,beneficiary,
                             currency,amount,expiry_date,shipment_date,incoterms,
                             port_of_loading,port_of_discharge,partial_shipment,transhipment,
                             documents_required,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (lc_num,lc_type,issuing_bank,advising_bank,applicant,beneficiary,
                             currency_lc,amount_lc,str(expiry),str(ship_date),incoterms_lc,
                             port_load_lc,port_disc_lc,partial,transship,docs_req,status_lc))
                        conn.commit(); conn.close()
                        st.success(f"L/C {lc_num} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("L/C 목록")
        conn = get_db()
        df_lc = pd.read_sql_query("""
            SELECT lc_number AS LC번호, lc_type AS 유형,
                   issuing_bank AS 개설은행, applicant AS 개설의뢰인,
                   beneficiary AS 수익자, currency AS 통화,
                   amount AS 금액, expiry_date AS 유효기간,
                   shipment_date AS 선적기한, incoterms AS 인코텀즈,
                   status AS 상태
            FROM letters_of_credit ORDER BY id DESC""", conn)
        conn.close()
        if df_lc.empty:
            st.info("L/C 없음")
        else:
            st.dataframe(df_lc, use_container_width=True, hide_index=True)
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("총 L/C 건수", len(df_lc))
            col_m2.metric("총 L/C 금액", f"${df_lc['금액'].sum():,.0f}")

        st.divider()
        st.subheader("L/C 상태 변경")
        conn = get_db()
        lcs = [dict(r) for r in conn.execute("SELECT id, lc_number, beneficiary, status FROM letters_of_credit WHERE status NOT IN ('결제완료','만료')").fetchall()]
        conn.close()
        if lcs:
            lc_map = {f"{l['lc_number']} - {l['beneficiary']} ({l['status']})": l['id'] for l in lcs}
            sel_lc = st.selectbox("L/C 선택", list(lc_map.keys()))
            new_lc_st = st.selectbox("변경 상태", ["개설","통지","선적","네고","결제완료","만료"])
            if st.button("🔄 상태 변경", use_container_width=True):
                conn = get_db()
                conn.execute("UPDATE letters_of_credit SET status=? WHERE id=?", (new_lc_st, lc_map[sel_lc]))
                conn.commit(); conn.close()
                st.success("변경 완료!"); st.rerun()

# ── 8. 수입요건 ──────────────────────────────────────
with tabs[8]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("수입요건 확인 등록")
        conn = get_db()
        hs_req = [dict(r) for r in conn.execute("SELECT hs_code, description FROM hs_codes").fetchall()]
        conn.close()
        hs_req_map = {"선택안함": ""}
        hs_req_map.update({f"{h['hs_code']} - {h['description']}": h['hs_code'] for h in hs_req})

        with st.form("req_form", clear_on_submit=True):
            item_req  = st.text_input("품목명 *")
            hs_sel_req= st.selectbox("HS Code", list(hs_req_map.keys()))
            req_type  = st.selectbox("요건 유형", [
                "검역(동물)","검역(식물)","식품위생","전파인증(KC)","안전인증(KC)",
                "환경부 허가","화학물질 신고","의약품 허가","기타"])
            agency    = st.text_input("담당기관", placeholder="예: 농림축산검역본부, 국립전파연구원")
            desc_req  = st.text_area("요건 내용", height=70)
            docs_req2 = st.text_area("필요서류", height=60)
            col_a, col_b = st.columns(2)
            status_req= col_a.selectbox("확인상태", ["확인필요","확인완료","면제","해당없음"])
            checked_dt= col_b.date_input("확인일")
            note_req  = st.text_input("비고")
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not item_req:
                    st.error("품목명 필수")
                else:
                    try:
                        conn = get_db()
                        conn.execute("""INSERT INTO import_requirements
                            (hs_code,item_name,requirement_type,agency,description,
                             required_docs,status,checked_at,note)
                            VALUES(?,?,?,?,?,?,?,?,?)""",
                            (hs_req_map.get(hs_sel_req,""), item_req, req_type,
                             agency, desc_req, docs_req2, status_req,
                             str(checked_dt), note_req))
                        conn.commit(); conn.close()
                        st.success("수입요건 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("수입요건 목록")
        conn = get_db()
        df_req = pd.read_sql_query("""
            SELECT hs_code AS HSCode, item_name AS 품목,
                   requirement_type AS 요건유형, agency AS 담당기관,
                   description AS 내용, required_docs AS 필요서류,
                   status AS 상태, checked_at AS 확인일
            FROM import_requirements ORDER BY id DESC""", conn)
        conn.close()
        if df_req.empty:
            st.info("수입요건 없음")
        else:
            def req_color(val):
                if val == "확인필요": return "background-color:#fef3c7"
                if val == "확인완료": return "background-color:#d1fae5"
                return ""
            st.dataframe(df_req.style.map(req_color, subset=['상태']),
                         use_container_width=True, hide_index=True)
            pending = len(df_req[df_req['상태']=='확인필요'])
            if pending > 0:
                st.warning(f"⚠️ 확인 필요 항목: {pending}건")

# ── 9. 전략물자 체크 ──────────────────────────────────────
with tabs[9]:
    st.subheader("⚠️ 전략물자 해당 여부 확인")
    st.warning("전략물자 수출 시 허가 없이 반출하면 **대외무역법 위반**으로 형사처벌 대상입니다.")

    col_form, col_list = st.columns([1, 2])
    with col_form:
        conn = get_db()
        hs_strat = [dict(r) for r in conn.execute("SELECT hs_code, description, special_notes FROM hs_codes").fetchall()]
        conn.close()
        hs_strat_map = {"선택안함": None}
        hs_strat_map.update({f"{h['hs_code']} - {h['description']}": h for h in hs_strat})

        with st.form("strat_form", clear_on_submit=True):
            item_st   = st.text_input("품목명 *")
            hs_sel_st = st.selectbox("HS Code", list(hs_strat_map.keys()))

            # HS Code 선택 시 자동 경고
            if hs_sel_st != "선택안함" and hs_strat_map.get(hs_sel_st):
                hs_st_data = hs_strat_map[hs_sel_st]
                if hs_st_data['special_notes'] and '전략물자' in str(hs_st_data['special_notes']):
                    st.error(f"🚨 '{hs_sel_st}' — 전략물자 해당 가능 품목! 반드시 사전 확인 필요")

            dest_st   = st.text_input("수출 목적국 *")
            end_user  = st.text_input("최종 사용자")
            check_type= st.selectbox("체크 유형", ["수출","수입","재수출","중개"])
            col_a, col_b = st.columns(2)
            result_st = col_a.selectbox("체크 결과", ["미확인","해당없음","요허가","수출금지"])
            restrict  = col_b.selectbox("제한수준", ["없음","EAR99","통제품목","금지"])
            checker   = st.text_input("확인자")
            note_st   = st.text_area("비고", height=60)
            # API 즉시 스크리닝 버튼
            col_sg1, col_sg2 = st.columns(2)
            do_api_check = col_sg1.form_submit_button("🔍 API 스크리닝 후 등록", use_container_width=True)
            do_manual    = col_sg2.form_submit_button("✅ 수동 등록", use_container_width=True)

            if do_api_check or do_manual:
                if not item_st or not dest_st:
                    st.error("품목명, 목적국 필수")
                else:
                    try:
                        cnum = gen_number("SGC")
                        hs_code_st  = hs_strat_map.get(hs_sel_st) or {}
                        hs_code_val = hs_code_st.get('hs_code', '')
                        final_result   = result_st
                        final_restrict = restrict

                        if do_api_check:
                            # YESTRADE API (또는 내장DB) 자동 스크리닝
                            keys_sg = get_api_keys()
                            sg_api = fetch_yestrade_check(
                                keys_sg.get("YESTRADE_API_KEY",""),
                                hs_code_val or hs_sel_st, dest_st)
                            if sg_api.get("sanction_match"):
                                final_result   = "수출금지"
                                final_restrict = "금지"
                                st.error(f"🚨 제재국 탐지: {sg_api.get('sanction_info','')}")
                            elif sg_api.get("strategic_match"):
                                final_result   = "요허가"
                                final_restrict = "통제품목"
                                st.warning(f"⚠️ 전략물자 해당: {sg_api.get('description','')}")
                            else:
                                final_result   = "해당없음"
                                final_restrict = "없음"
                                st.success(f"✅ {sg_api.get('source','')} 기준 해당 없음")

                        conn = get_db()
                        conn.execute("""INSERT INTO strategic_goods_checks
                            (check_number,item_name,hs_code,destination_country,end_user,
                             check_type,result,restriction_level,checker,
                             checked_at,note)
                            VALUES(?,?,?,?,?,?,?,?,?,NOW(),?)""",
                            (cnum,item_st,hs_code_val,dest_st,end_user,
                             check_type,final_result,final_restrict,checker,note_st))
                        conn.commit(); conn.close()
                        st.success(f"전략물자 체크 {cnum} 등록!"); st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with col_list:
        st.subheader("전략물자 체크 이력")
        conn = get_db()
        df_sg = pd.read_sql_query("""
            SELECT check_number AS 체크번호, item_name AS 품목,
                   hs_code AS HSCode, destination_country AS 목적국,
                   end_user AS 최종사용자, check_type AS 유형,
                   result AS 결과, restriction_level AS 제한수준,
                   checker AS 확인자, checked_at AS 확인일시
            FROM strategic_goods_checks ORDER BY id DESC""", conn)
        conn.close()
        if df_sg.empty:
            st.info("전략물자 체크 이력 없음")
        else:
            def sg_color(val):
                if val in ["수출금지","요허가"]: return "background-color:#fee2e2;font-weight:bold"
                if val == "해당없음": return "background-color:#d1fae5"
                return ""
            st.dataframe(df_sg.style.map(sg_color, subset=['결과']),
                         use_container_width=True, hide_index=True)
            danger = len(df_sg[df_sg['결과'].isin(['수출금지','요허가'])])
            if danger > 0:
                st.error(f"🚨 주의 필요 항목: {danger}건")

# ── 10. 운송오더 ──────────────────────────────────────
with tabs[10]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("운송오더(FO) 등록")
        with st.form("fo_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            t_mode    = col_a.selectbox("운송방식", ["육상","해상","항공","철도"])
            carrier   = col_b.text_input("운송사")
            vehicle   = st.text_input("차량/편명번호")
            col_c, col_d = st.columns(2)
            origin_fo = col_c.text_input("출발지")
            dest_fo   = col_d.text_input("도착지")
            col_e, col_f = st.columns(2)
            p_dep     = col_e.date_input("계획 출발일")
            p_arr     = col_f.date_input("계획 도착일")
            freight   = st.number_input("운임", min_value=0.0, format="%.2f")
            status    = st.selectbox("상태", ["계획","확정","운송중","완료","취소"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                try:
                    fnum = gen_number("FO")
                    conn = get_db()
                    conn.execute("""INSERT INTO freight_orders
                        (freight_number,transport_mode,carrier,vehicle_number,
                         origin,destination,planned_departure,planned_arrival,
                         freight_cost,status)
                        VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (fnum,t_mode,carrier,vehicle,origin_fo,dest_fo,
                         str(p_dep),str(p_arr),freight,status))
                    conn.commit(); conn.close()
                    st.success(f"운송오더 {fnum} 등록!"); st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")

    with col_list:
        st.subheader("운송오더 목록")
        conn = get_db()
        df_fo = pd.read_sql_query("""
            SELECT freight_number AS FO번호, transport_mode AS 방식,
                   carrier AS 운송사, vehicle_number AS 차량번호,
                   origin AS 출발지, destination AS 도착지,
                   planned_departure AS 계획출발, planned_arrival AS 계획도착,
                   freight_cost AS 운임, status AS 상태
            FROM freight_orders ORDER BY id DESC""", conn)
        conn.close()
        if df_fo.empty:
            st.info("운송오더 없음")
        else:
            st.dataframe(df_fo, use_container_width=True, hide_index=True)
            st.metric("총 운임비용", f"₩{df_fo['운임'].sum():,.0f}")

# ── 11. 현황 대시보드 ──────────────────────────────────────
with tabs[11]:
    st.subheader("📊 수출입 / 운송 종합 현황")
    conn = get_db()
    df_bl_s  = pd.read_sql_query("SELECT status, transport_type, freight_cost FROM logistics", conn)
    df_fo_s  = pd.read_sql_query("SELECT status, transport_mode, freight_cost FROM freight_orders", conn)
    df_imp_s = pd.read_sql_query("SELECT status, customs_duty, vat_amount, total_tax FROM import_declarations", conn)
    df_exp_s = pd.read_sql_query("SELECT status, destination_country FROM export_declarations", conn)
    df_lc_s  = pd.read_sql_query("SELECT status, amount FROM letters_of_credit", conn)
    df_sg_s  = pd.read_sql_query("SELECT result FROM strategic_goods_checks", conn)
    conn.close()

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("🚢 운송중(해외)", len(df_bl_s[df_bl_s['status']=='운송중']) if not df_bl_s.empty else 0)
    col2.metric("🛃 통관중", len(df_bl_s[df_bl_s['status']=='통관중']) if not df_bl_s.empty else 0)
    col3.metric("📥 수입신고", len(df_imp_s) if not df_imp_s.empty else 0)
    col4.metric("📤 수출신고", len(df_exp_s) if not df_exp_s.empty else 0)
    col5.metric("💳 L/C 진행중", len(df_lc_s[df_lc_s['status'].isin(['개설','통지','선적','네고'])]) if not df_lc_s.empty else 0)
    col6.metric("⚠️ 전략물자 주의",
                len(df_sg_s[df_sg_s['result'].isin(['수출금지','요허가'])]) if not df_sg_s.empty else 0,
                delta_color="inverse")

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        if not df_imp_s.empty:
            st.subheader("수입 세금 현황")
            tax_data = {"관세": df_imp_s['customs_duty'].sum(),
                        "부가세": df_imp_s['vat_amount'].sum()}
            st.bar_chart(pd.DataFrame.from_dict(tax_data, orient='index', columns=['금액']))
    with col_r:
        if not df_exp_s.empty:
            st.subheader("수출 목적국별")
            dest_cnt = df_exp_s['destination_country'].value_counts().reset_index()
            dest_cnt.columns = ['국가','건수']
            st.bar_chart(dest_cnt.set_index('국가'))

# ── C/O 원산지 증명서 ─────────────────────────────────
with tabs["co"]:
    def _ac_tm(t,c,ct="TEXT"):
        try: conn=get_db(); conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}"); conn.commit(); conn.close()
        except: pass
    # MySQL: origin_certificates 테이블은 db.py init_db()에서 이미 생성됨

    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("📜 원산지 증명서 발급")
        conn=get_db()
        exps=[r[0] for r in conn.execute("SELECT decl_number FROM export_declarations ORDER BY id DESC LIMIT 30").fetchall()]
        conn.close()
        with st.form("co_f", clear_on_submit=True):
            exp_sel = st.selectbox("수출면장", ["직접입력"]+exps)
            a,b = st.columns(2); exp_nm=a.text_input("수출자(회사명) *"); imp_nm=b.text_input("수입자")
            c,d = st.columns(2); hs=c.text_input("HS Code"); item_co=d.text_input("품목명 *")
            e,f,g = st.columns(3); qty_co=e.number_input("수량",min_value=0.0,format="%.2f"); unit_co=f.selectbox("단위",["EA","KG","MT","L","M","SET"]); fob=g.number_input("FOB금액",min_value=0.0,format="%.2f")
            h,i = st.columns(2); cur_co=h.selectbox("통화",["USD","EUR","JPY","CNY","KRW"]); origin=i.text_input("원산지",value="KR")
            j,k = st.columns(2); dest_co=j.text_input("목적국"); co_type=k.selectbox("C/O유형",["FTA","일반(비FTA)","GSP","특혜"])
            fta_ag = st.selectbox("FTA 협정",["한-미","한-EU","한-중","한-ASEAN","한-일","RCEP","기타"])
            l,m = st.columns(2); iss_co=l.date_input("발급일"); vt_co=m.date_input("유효기간",value=date.today()+timedelta(days=365))
            st_co = st.selectbox("상태",["발급신청","검토중","발급완료","반려"])
            if st.form_submit_button("✅ 등록", use_container_width=True):
                if not exp_nm or not item_co: st.error("필수 누락")
                else:
                    try:
                        conn=get_db(); conn.execute("""INSERT INTO origin_certificates(co_number,exporter_name,importer_name,hs_code,item_name,quantity,unit,fob_value,currency,origin_country,dest_country,co_type,fta_agreement,issue_date,valid_to,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(gen_number("CO"),exp_nm,imp_nm,hs,item_co,qty_co,unit_co,fob,cur_co,origin,dest_co,co_type,fta_ag,str(iss_co),str(vt_co),st_co))
                        conn.commit(); conn.close(); st.success("C/O 등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("C/O 목록")
        conn=get_db(); df_co=pd.read_sql_query("""SELECT co_number AS "C/O번호",exporter_name AS 수출자,item_name AS 품목,hs_code AS HS,origin_country AS 원산지,dest_country AS 목적국,co_type AS 유형,fta_agreement AS FTA협정,issue_date AS 발급일,valid_to AS 유효기간,status AS 상태 FROM origin_certificates ORDER BY id DESC""",conn); conn.close()
        if df_co.empty: st.info("없음")
        else:
            today_s=datetime.now().strftime("%Y-%m-%d")
            def co_c(r): return ['background-color:#fee2e2']*len(r) if str(r['유효기간'])<today_s else ['']*len(r)
            st.dataframe(df_co.style.apply(co_c,axis=1), use_container_width=True, hide_index=True)


# ── 운임 계산 ─────────────────────────────────────────
with tabs["freight"]:
    # MySQL: freight_quotes 테이블은 db.py init_db()에서 이미 생성됨

    st.subheader("💰 운임 계산기")
    col_l, col_r = st.columns([1,1])
    with col_l:
        st.markdown("#### 운임 견적 등록")
        with st.form("fq_f", clear_on_submit=True):
            a,b=st.columns(2); tm=a.selectbox("운송방식",["해상FCL","해상LCL","항공","육상","복합"]); car=b.text_input("운송사/포워더")
            c,d=st.columns(2); orig=c.text_input("출발지"); dest=d.text_input("도착지")
            e,f,g=st.columns(3); wt=e.number_input("중량(kg)",min_value=0.0,format="%.1f"); cbm=f.number_input("CBM(㎥)",min_value=0.0,format="%.3f"); cur_fr=g.selectbox("통화",["USD","EUR","KRW"])
            fr_cost=st.number_input("기본운임",min_value=0.0,format="%.2f")
            st.caption("할증료 (BAF, CAF, THC, 보험료 등)")
            h,i,j=st.columns(3); baf=h.number_input("BAF",min_value=0.0,format="%.0f"); caf=i.number_input("CAF",min_value=0.0,format="%.0f"); thc=j.number_input("THC",min_value=0.0,format="%.0f")
            exr=st.number_input("적용환율(₩/외화)",min_value=0.0,value=1300.0,format="%.1f")
            total_usd=fr_cost+baf+caf+thc; total_krw=total_usd*exr if cur_fr!='KRW' else total_usd
            st.info(f"총 운임: {cur_fr} {total_usd:,.2f}  ≈  ₩{total_krw:,.0f}")
            vu=st.date_input("유효기간"); fnote=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 저장", use_container_width=True):
                try:
                    surj=f"BAF:{baf},CAF:{caf},THC:{thc}"
                    conn=get_db(); conn.execute("""INSERT INTO freight_quotes(fq_number,transport_mode,origin,destination,weight_kg,cbm,carrier,freight_cost,currency,surcharges,total_cost_krw,valid_until,note)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(gen_number("FQ"),tm,orig,dest,wt,cbm,car,fr_cost,cur_fr,surj,total_krw,str(vu),fnote))
                    conn.commit(); conn.close(); st.success("저장!"); st.rerun()
                except Exception as e: st.error(f"오류:{e}")
    with col_r:
        st.markdown("#### 운임 비교표")
        conn=get_db(); df_fq=pd.read_sql_query("""SELECT fq_number AS 견적번호,transport_mode AS 방식,carrier AS 운송사,origin AS 출발,destination AS 도착,weight_kg AS 중량,cbm AS CBM,freight_cost AS 운임,currency AS 통화,total_cost_krw AS 원화환산,valid_until AS 유효기간 FROM freight_quotes ORDER BY total_cost_krw""",conn); conn.close()
        if df_fq.empty: st.info("없음")
        else:
            st.dataframe(df_fq, use_container_width=True, hide_index=True)
            if len(df_fq)>=2:
                cheapest=df_fq.iloc[0]
                st.success(f"💡 최저 운임: {cheapest['운송사']} — ₩{cheapest['원화환산']:,.0f}")


# ── 환율 영향 분석 BI ──────────────────────────────────
with tabs["bi_fx"]:
    try:
        import plotly.express as px; import plotly.graph_objects as go
        from plotly.subplots import make_subplots; HAS_PL2=True
    except: HAS_PL2=False
    if not HAS_PL2: st.warning("pip install plotly")
    else:
        from datetime import datetime, timedelta
        conn=get_db()
        st.subheader("💱 환율 영향 분석")
        # 환율 데이터
        df_fx=pd.read_sql_query("SELECT currency,rate_to_krw AS rate,rate_date AS created_at FROM exchange_rates ORDER BY rate_date DESC LIMIT 200",conn)
        if not df_fx.empty:
            df_fx['날짜']=df_fx['created_at'].astype(str).str[:10]
            c1,c2,c3=st.columns(3)
            for i,(cur2,label) in enumerate(zip(['USD','EUR','CNY'],['달러','유로','위안'])):
                cur_df=df_fx[df_fx['currency']==cur2]
                if not cur_df.empty:
                    latest=cur_df.iloc[0]['rate']
                    prev=cur_df.iloc[1]['rate'] if len(cur_df)>1 else latest
                    [c1,c2,c3][i].metric(f"{label}({cur2})",f"₩{latest:,.2f}",f"{latest-prev:+.2f}")
            # 환율 추이 차트
            curs=df_fx['currency'].unique().tolist()
            sel_cur=st.multiselect("통화 선택",curs,default=curs[:3] if len(curs)>=3 else curs)
            fig=go.Figure()
            for c3x in sel_cur:
                cd=df_fx[df_fx['currency']==c3x].sort_values('날짜')
                if not cd.empty: fig.add_trace(go.Scatter(x=cd['날짜'],y=cd['rate'],name=c3x,mode='lines+markers'))
            fig.update_layout(title="통화별 환율 추이",height=300,margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig,use_container_width=True)

        # 수입 환율 영향 분석
        st.subheader("📥 수입 원가 환율 영향")
        df_imp=pd.read_sql_query("SELECT currency,invoice_value,customs_duty,total_tax,created_at FROM import_declarations ORDER BY created_at",conn)
        if not df_imp.empty:
            col_l,col_r=st.columns(2)
            with col_l:
                df_cur_imp=df_imp.groupby('currency').agg(건수=('invoice_value','count'),CIF합계=('invoice_value','sum'),관세합계=('customs_duty','sum')).reset_index()
                st.plotly_chart(px.bar(df_cur_imp,x='currency',y='CIF합계',color='currency',title="통화별 수입 CIF금액").update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
            with col_r:
                st.plotly_chart(px.pie(df_cur_imp,names='currency',values='건수',title="수입 통화 비중",hole=0.4).update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()


# ── 국가별 분석 BI ────────────────────────────────────
with tabs["bi_country"]:
    try:
        import plotly.express as px; import plotly.graph_objects as go; HAS_PL3=True
    except: HAS_PL3=False
    if not HAS_PL3: st.warning("pip install plotly")
    else:
        conn=get_db()
        st.subheader("🌍 국가별 수출입 분석")

        # KPI
        exp_cnt=conn.execute("SELECT COUNT(*) FROM export_declarations").fetchone()[0]
        imp_cnt=conn.execute("SELECT COUNT(*) FROM import_declarations").fetchone()[0]
        exp_fob=conn.execute("SELECT COALESCE(SUM(invoice_value),0) FROM export_declarations").fetchone()[0]
        imp_cif=conn.execute("SELECT COALESCE(SUM(invoice_value),0) FROM import_declarations").fetchone()[0]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("수출 건수",f"{exp_cnt}건"); c2.metric("수출 FOB합계",f"${exp_fob:,.0f}")
        c3.metric("수입 건수",f"{imp_cnt}건"); c4.metric("수입 CIF합계",f"${imp_cif:,.0f}")
        st.divider()

        col_l,col_r=st.columns(2)
        with col_l:
            df_exp_c=pd.read_sql_query("SELECT destination_country AS 국가,COUNT(*) AS 건수,ROUND(SUM(invoice_value),0) AS FOB합계 FROM export_declarations GROUP BY destination_country ORDER BY FOB합계 DESC LIMIT 12",conn)
            if not df_exp_c.empty:
                st.plotly_chart(px.bar(df_exp_c,y='국가',x='FOB합계',orientation='h',color='FOB합계',color_continuous_scale='Blues',title="수출 국가별 FOB금액 TOP12").update_layout(height=320,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)
        with col_r:
            df_imp_c=pd.read_sql_query("SELECT origin_country AS 국가,COUNT(*) AS 건수,ROUND(SUM(invoice_value),0) AS CIF합계 FROM import_declarations GROUP BY origin_country ORDER BY CIF합계 DESC LIMIT 12",conn)
            if not df_imp_c.empty:
                st.plotly_chart(px.bar(df_imp_c,y='국가',x='CIF합계',orientation='h',color='CIF합계',color_continuous_scale='Oranges',title="수입 국가별 CIF금액 TOP12").update_layout(height=320,margin=dict(l=0,r=0,t=40,b=0),showlegend=False),use_container_width=True)

        # 전략물자 고위험 국가
        st.subheader("⚠️ 전략물자 국가별 위험 현황")
        df_sg=pd.read_sql_query("SELECT destination_country AS 국가,result AS 결과,COUNT(*) AS 건수 FROM strategic_goods_checks GROUP BY destination_country,result ORDER BY 건수 DESC",conn)
        if not df_sg.empty:
            clr={'이상없음':'#22c55e','저위험':'#3b82f6','고위험':'#f97316','통제대상':'#ef4444'}
            st.plotly_chart(px.bar(df_sg,x='국가',y='건수',color='결과',color_discrete_map=clr,title="국가별 전략물자 결과").update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)

        # 월별 수출입 추이
        st.subheader("📈 월별 수출입 추이")
        df_exp_m=pd.read_sql_query("SELECT DATE_FORMAT(created_at,'%%Y-%%m') AS 월,COUNT(*) AS 수출건수,ROUND(SUM(invoice_value),0) AS FOB FROM export_declarations GROUP BY DATE_FORMAT(created_at,'%%Y-%%m') ORDER BY 월",conn)
        df_imp_m=pd.read_sql_query("SELECT DATE_FORMAT(created_at,'%%Y-%%m') AS 월,COUNT(*) AS 수입건수,ROUND(SUM(invoice_value),0) AS CIF FROM import_declarations GROUP BY DATE_FORMAT(created_at,'%%Y-%%m') ORDER BY 월",conn)
        if not df_exp_m.empty or not df_imp_m.empty:
            col_l2,col_r2=st.columns(2)
            with col_l2:
                if not df_exp_m.empty: st.plotly_chart(px.area(df_exp_m,x='월',y='FOB',title="수출 FOB 추이",color_discrete_sequence=['#3b82f6']).update_layout(height=240,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
            with col_r2:
                if not df_imp_m.empty: st.plotly_chart(px.area(df_imp_m,x='월',y='CIF',title="수입 CIF 추이",color_discrete_sequence=['#f97316']).update_layout(height=240,margin=dict(l=0,r=0,t=40,b=0)),use_container_width=True)
        conn.close()

# ══════════════════════════════════════════════════════
# 포워더 관리
# ══════════════════════════════════════════════════════
with tabs["fwd"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("🏢 포워더 등록")
        with st.form("fwd_f", clear_on_submit=True):
            a,b = st.columns(2); fc=a.text_input("포워더코드 *"); fn=b.text_input("포워더명 *")
            c,d = st.columns(2); ctt=c.text_input("담당자"); phn=d.text_input("전화")
            eml=st.text_input("이메일")
            e,f = st.columns(2); cntry=e.text_input("국가"); rgn=f.text_input("지역")
            modes=st.multiselect("취급 운송방식",["해상FCL","해상LCL","항공","육상","복합"])
            rat=st.slider("평점",0.0,5.0,3.0,0.5); fst=st.selectbox("상태",["활성","휴면","거래중지"])
            fnote=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not fc or not fn: st.error("코드·이름 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO forwarders(forwarder_code,forwarder_name,contact,phone,email,country,region,transport_modes,rating,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE
                            forwarder_name=VALUES(forwarder_name),contact=VALUES(contact),phone=VALUES(phone),
                            email=VALUES(email),country=VALUES(country),region=VALUES(region),
                            transport_modes=VALUES(transport_modes),rating=VALUES(rating),status=VALUES(status)""",(
                            fc,fn,ctt,phn,eml,cntry,rgn,",".join(modes),rat,fst,fnote))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("포워더 목록")
        conn=get_db(); df_fwd=pd.read_sql_query("""
            SELECT forwarder_code AS 코드, forwarder_name AS 포워더명, contact AS 담당자,
                   country AS 국가, transport_modes AS 운송방식, rating AS 평점, status AS 상태
            FROM forwarders ORDER BY rating DESC""", conn); conn.close()
        if df_fwd.empty: st.info("없음")
        else: st.dataframe(df_fwd, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📊 포워더 실적 분석")
        conn=get_db()
        df_fwd_perf=pd.read_sql_query("""
            SELECT f.forwarder_name AS 포워더, fo.transport_mode AS 방식,
                   COUNT(fo.id) AS 운송건수,
                   ROUND(AVG(fo.freight_cost),0) AS 평균운임,
                   SUM(fo.freight_cost) AS 총운임
            FROM freight_orders fo
            JOIN forwarders f ON fo.carrier=f.forwarder_name
            GROUP BY f.forwarder_name, fo.transport_mode
            ORDER BY 총운임 DESC""", conn); conn.close()
        if df_fwd_perf.empty: st.info("운송 실적 없음")
        else:
            try:
                import plotly.express as px
                st.plotly_chart(px.bar(df_fwd_perf,x='포워더',y='총운임',color='방식',
                    title="포워더별 운임 실적").update_layout(height=280,margin=dict(l=0,r=0,t=40,b=0)),
                    use_container_width=True)
            except: pass
            st.dataframe(df_fwd_perf, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════
# 수출용 포장명세서 (Export Packing List)
# ══════════════════════════════════════════════════════
with tabs["epl"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("📦 수출 포장명세서 등록")
        conn=get_db()
        exps_epl=[r for r in conn.execute("SELECT id,decl_number,item_name FROM export_declarations ORDER BY id DESC LIMIT 30").fetchall()]
        cis_epl=[r for r in conn.execute("SELECT id,ci_number,item_name FROM commercial_invoices ORDER BY id DESC LIMIT 30").fetchall()]
        conn.close()
        emap={f"{r['decl_number']}-{r['item_name']}":r['id'] for r in exps_epl}
        cmap={f"{r['ci_number']}-{r['item_name']}":r['id'] for r in cis_epl}
        with st.form("epl_f", clear_on_submit=True):
            exp_sel=st.selectbox("수출면장",["없음"]+list(emap.keys()))
            ci_sel_epl=st.selectbox("상업송장(CI)",["없음"]+list(cmap.keys()))
            a,b=st.columns(2); shpr=a.text_input("송하인(Shipper) *"); csgn=b.text_input("수하인(Consignee) *")
            item_epl=st.text_input("품목명 *")
            c,d,e=st.columns(3); tbox=c.number_input("총 박스수",min_value=1,value=1); qpb=d.number_input("박스당 수량",min_value=1,value=1); ubox=e.selectbox("단위",["EA","KG","MT","L","SET"])
            f2,g2=st.columns(2); gw=f2.number_input("총중량 G.W(kg)",min_value=0.0,format="%.2f"); nw=g2.number_input("순중량 N.W(kg)",min_value=0.0,format="%.2f")
            dims=st.text_input("박스 치수 (L×W×H cm)")
            marks=st.text_area("화인 (Shipping Marks)",height=60)
            h2,i2=st.columns(2); pol=h2.text_input("선적항(POL)"); pod=i2.text_input("목적항(POD)")
            j2,k2=st.columns(2); vessel=j2.text_input("선박명"); bln=k2.text_input("B/L 번호")
            note_epl=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not shpr or not item_epl: st.error("송하인·품목 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO export_packing_lists
                            (epl_number,export_decl_id,ci_id,shipper,consignee,item_name,
                             total_boxes,qty_per_box,total_qty,gross_weight,net_weight,
                             dimensions,marks,port_of_loading,port_of_discharge,vessel_name,bl_number,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                            gen_number("EPL"),emap.get(exp_sel),cmap.get(ci_sel_epl),
                            shpr,csgn,item_epl,tbox,qpb,tbox*qpb,gw,nw,dims,marks,pol,pod,vessel,bln,note_epl))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("수출 포장명세서 목록")
        conn=get_db(); df_epl=pd.read_sql_query("""
            SELECT e.epl_number AS EPL번호, e.shipper AS 송하인, e.consignee AS 수하인,
                   e.item_name AS 품목, e.total_boxes AS 박스수,
                   e.total_qty AS 총수량,
                   e.gross_weight AS 총중량, e.net_weight AS 순중량,
                   e.port_of_loading AS 선적항, e.vessel_name AS 선박,
                   e.bl_number AS BL번호, e.created_at AS 등록일
            FROM export_packing_lists e ORDER BY e.id DESC""", conn); conn.close()
        if df_epl.empty: st.info("없음")
        else:
            st.dataframe(df_epl, use_container_width=True, hide_index=True)
            # 출력 뷰
            st.divider(); st.subheader("📄 포장명세서 출력")
            sel_epl=st.selectbox("EPL 선택",df_epl['EPL번호'].tolist())
            r=df_epl[df_epl['EPL번호']==sel_epl].iloc[0]
            st.markdown(f"""
| 항목 | 내용 | 항목 | 내용 |
|---|---|---|---|
| **EPL번호** | {r['EPL번호']} | **B/L번호** | {r['BL번호'] or '-'} |
| **송하인** | {r['송하인']} | **수하인** | {r['수하인']} |
| **품목** | {r['품목']} | **선박** | {r['선박'] or '-'} |
| **박스수** | {r['박스수']} boxes | **총수량** | {r['총수량']} EA |
| **총중량** | {r['총중량']} kg | **순중량** | {r['순중량']} kg |
| **선적항** | {r['선적항'] or '-'} | **등록일** | {str(r['등록일'])[:10] if r['등록일'] else '-'} |
""")


# ══════════════════════════════════════════════════════
# 무역 결제 (T/T · D/A · D/P)
# ══════════════════════════════════════════════════════
with tabs["tpay"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("💸 무역 결제 등록")
        conn=get_db()
        cis_tp=[r for r in conn.execute("SELECT id,ci_number,item_name FROM commercial_invoices ORDER BY id DESC LIMIT 30").fetchall()]
        conn.close()
        ci_tp_map={f"{r['ci_number']}-{r['item_name']}":r['id'] for r in cis_tp}
        with st.form("tpay_f", clear_on_submit=True):
            a,b=st.columns(2); ptype=a.selectbox("결제방식",["T/T 선불","T/T 후불","D/A","D/P","O/A","기타"]); pdir=b.selectbox("방향",["수입결제","수출수금"])
            ci_tp_sel=st.selectbox("연결 CI",["없음"]+list(ci_tp_map.keys()))
            cpart=st.text_input("거래처 *")
            c,d=st.columns(2); cur_tp=c.selectbox("통화",["USD","EUR","JPY","CNY","KRW"]); amt_tp=d.number_input("금액",min_value=0.0,format="%.2f")
            exr_tp=st.number_input("적용환율",min_value=0.0,value=1300.0,format="%.2f")
            krw_tp=amt_tp*exr_tp if cur_tp!='KRW' else amt_tp
            st.info(f"원화환산: ₩{krw_tp:,.0f}")
            e2,f2=st.columns(2); due_tp=e2.date_input("결제기한"); bank_tp=f2.text_input("은행명")
            ref_tp=st.text_input("은행 참조번호"); paid_tp=st.date_input("실제결제일")
            st_tp=st.selectbox("상태",["미결제","결제완료","연체","부분결제"])
            note_tp=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not cpart: st.error("거래처 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO trade_payments
                            (payment_number,payment_type,direction,ci_id,counterpart,currency,
                             amount,exchange_rate,krw_amount,due_date,paid_date,bank_ref,bank_name,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                            gen_number("TPY"),ptype,pdir,ci_tp_map.get(ci_tp_sel),cpart,
                            cur_tp,amt_tp,exr_tp,krw_tp,str(due_tp),str(paid_tp),ref_tp,bank_tp,st_tp,note_tp))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("무역 결제 현황")
        conn=get_db(); df_tp=pd.read_sql_query("""
            SELECT payment_number AS 결제번호, payment_type AS 방식, direction AS 방향,
                   counterpart AS 거래처, currency AS 통화, amount AS 금액,
                   krw_amount AS 원화, due_date AS 기한, paid_date AS 결제일,
                   bank_name AS 은행, status AS 상태
            FROM trade_payments ORDER BY id DESC""", conn); conn.close()
        if df_tp.empty: st.info("없음")
        else:
            today_s=pd.Timestamp.now().strftime("%Y-%m-%d")
            def tp_c(r): return ['background-color:#fee2e2']*len(r) if r['상태']=='연체' else (['background-color:#d1fae5']*len(r) if r['상태']=='결제완료' else ['']*len(r))
            st.dataframe(df_tp.style.apply(tp_c,axis=1), use_container_width=True, hide_index=True)
            c1,c2,c3=st.columns(3)
            unpaid=df_tp[df_tp['상태'].isin(['미결제','연체'])]
            c1.metric("미결제",f"₩{unpaid['원화'].sum():,.0f}",delta_color="inverse")
            c2.metric("연체",f"{len(df_tp[df_tp['상태']=='연체'])}건",delta_color="inverse")
            c3.metric("결제완료",f"{len(df_tp[df_tp['상태']=='결제완료'])}건")


# ══════════════════════════════════════════════════════
# 컨테이너 관리
# ══════════════════════════════════════════════════════
with tabs["ctn"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("📦 컨테이너 등록")
        conn=get_db()
        bls_ctn=[r for r in conn.execute("SELECT id,bl_number FROM logistics ORDER BY id DESC LIMIT 30").fetchall()]
        fwds_ctn=[r for r in conn.execute("SELECT id,forwarder_name FROM forwarders WHERE status='활성'").fetchall()]
        conn.close()
        bl_ctn_map={r['bl_number']:r['id'] for r in bls_ctn}
        fwd_ctn_map={r['forwarder_name']:r['id'] for r in fwds_ctn}
        with st.form("ctn_f", clear_on_submit=True):
            cnum=st.text_input("컨테이너번호 * (예: MSCU1234567)")
            a,b=st.columns(2); ctype=a.selectbox("컨테이너 타입",["20GP","40GP","40HC","20RF","40RF","20OT","45HC"]); seal=b.text_input("봉인번호")
            bl_sel_c=st.selectbox("연결 B/L",["없음"]+list(bl_ctn_map.keys()))
            fwd_sel_c=st.selectbox("포워더",["없음"]+list(fwd_ctn_map.keys()))
            c,d=st.columns(2); orig_p=c.text_input("출발항"); dest_p=d.text_input("도착항")
            e,f=st.columns(2); etd_c=e.date_input("ETD(출항예정)"); eta_c=f.date_input("ETA(입항예정)")
            g,h=st.columns(2); free_d=g.number_input("Free Days",min_value=0,value=14); dem_r=h.number_input("Demurrage($/일)",min_value=0.0,format="%.2f")
            ret_dl=st.date_input("컨테이너 반납기한",value=pd.Timestamp.now()+pd.Timedelta(days=21))
            cst=st.selectbox("상태",["예약","선적","운송중","입항","통관중","반납완료","지연"])
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not cnum: st.error("컨테이너번호 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO containers
                            (container_number,container_type,bl_id,forwarder_id,seal_number,
                             origin_port,dest_port,etd,eta,free_days,demurrage_rate,return_deadline,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON DUPLICATE KEY UPDATE
                            container_type=VALUES(container_type),status=VALUES(status),
                            return_deadline=VALUES(return_deadline)""",(
                            cnum,ctype,bl_ctn_map.get(bl_sel_c),fwd_ctn_map.get(fwd_sel_c),seal,
                            orig_p,dest_p,str(etd_c),str(eta_c),free_d,dem_r,str(ret_dl),cst))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("컨테이너 현황")
        conn=get_db(); df_ctn=pd.read_sql_query("""
            SELECT container_number AS 컨테이너번호, container_type AS 타입,
                   origin_port AS 출발항, dest_port AS 도착항,
                   etd AS ETD, eta AS ETA,
                   free_days AS FreeDays,
                   demurrage_rate AS 데머리지율,
                   return_deadline AS 반납기한,
                   CAST(DATEDIFF(return_deadline, CURDATE()) AS SIGNED) AS 반납잔여일,
                   status AS 상태
            FROM containers ORDER BY eta""", conn); conn.close()
        if df_ctn.empty: st.info("없음")
        else:
            today_s=pd.Timestamp.now().strftime("%Y-%m-%d")
            overdue=df_ctn[(df_ctn['반납잔여일']<0)&(~df_ctn['상태'].isin(['반납완료']))]
            soon=df_ctn[(df_ctn['반납잔여일']>=0)&(df_ctn['반납잔여일']<=7)&(~df_ctn['상태'].isin(['반납완료']))]
            if not overdue.empty:
                st.error(f"⚠️ 반납 기한 초과 — {len(overdue)}개 (데머리지 발생 중)")
                st.dataframe(overdue[['컨테이너번호','타입','반납기한','반납잔여일','데머리지율','상태']],use_container_width=True,hide_index=True)
            if not soon.empty:
                st.warning(f"🟡 7일 내 반납 예정 — {len(soon)}개")
            st.dataframe(df_ctn, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════
# 운송 실시간 추적 (타임라인)
# ══════════════════════════════════════════════════════
with tabs["track"]:
    st.subheader("🗺️ 운송 진행 추적")
    conn=get_db()
    bls_t=[r for r in conn.execute("SELECT id,bl_number,transport_type,carrier,status FROM logistics ORDER BY id DESC").fetchall()]
    conn.close()
    if not bls_t:
        st.info("B/L 없음")
    else:
        bl_t_map={f"{r['bl_number']} [{r['transport_type']}] — {r['status']}":r for r in bls_t}
        sel_bl_t=st.selectbox("B/L 선택",list(bl_t_map.keys()))
        bl_data=bl_t_map[sel_bl_t]

        col_l,col_r=st.columns([2,1])
        with col_l:
            st.subheader("이벤트 등록")
            with st.form("sev_f",clear_on_submit=True):
                a,b=st.columns(2)
                ev_type=a.selectbox("이벤트",["선적완료","출항","중간항 경유","입항","안벽접안","하역완료","통관신고","통관완료","창고입고","배송출발","배송완료","지연발생","기타"])
                ev_date=b.date_input("일자")
                ev_loc=st.text_input("위치/항구")
                ev_desc=st.text_area("상세내용",height=50)
                # 컨테이너 연결
                conn=get_db(); ctns=[r[0] for r in conn.execute("SELECT container_number FROM containers WHERE bl_id=?",(bl_data['id'],)).fetchall()]; conn.close()
                ctn_sel=st.selectbox("컨테이너",["없음"]+ctns)
                conn=get_db(); ctn_id=conn.execute("SELECT id FROM containers WHERE container_number=?",(ctn_sel,)).fetchone(); conn.close()
                if st.form_submit_button("✅ 이벤트 추가",use_container_width=True):
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO shipment_events(bl_id,container_id,event_type,event_date,location,description)
                            VALUES(?,?,?,?,?,?)""",(bl_data['id'],ctn_id[0] if ctn_id else None,ev_type,str(ev_date),ev_loc,ev_desc))
                        conn.commit(); conn.close(); st.success("추가!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
        with col_r:
            # BL 기본 정보
            conn=get_db(); bl_info=conn.execute("SELECT * FROM logistics WHERE id=?",(bl_data['id'],)).fetchone(); conn.close()
            if bl_info:
                st.metric("운송사",bl_info['carrier'] or '-')
                st.metric("출발",bl_info['departure_date'] or '-')
                st.metric("도착예정",bl_info['arrival_date'] or '-')
                st.metric("상태",bl_info['status'])

        # 타임라인 표시
        st.divider()
        st.subheader("📍 운송 타임라인")
        conn=get_db(); df_ev=pd.read_sql_query("""
            SELECT event_type AS 이벤트, event_date AS 일자, location AS 위치,
                   description AS 내용, source AS 출처, created_at AS 등록일시
            FROM shipment_events WHERE bl_id=?
            ORDER BY event_date,id""",(bl_data['id'],),conn); conn.close()
        if df_ev.empty:
            st.info("등록된 이벤트 없음")
        else:
            # 타임라인 시각화
            status_icons={"선적완료":"🚢","출항":"⛵","중간항 경유":"🔄","입항":"⚓","안벽접안":"🏗️",
                          "하역완료":"📦","통관신고":"📋","통관완료":"✅","창고입고":"🏭",
                          "배송출발":"🚚","배송완료":"🎉","지연발생":"⚠️","기타":"📌"}
            for _,ev in df_ev.iterrows():
                icon=status_icons.get(ev['이벤트'],"📌")
                with st.container():
                    c1,c2=st.columns([1,4])
                    c1.markdown(f"**{ev['일자']}**")
                    c2.markdown(f"{icon} **{ev['이벤트']}** — {ev['위치'] or ''} {ev['내용'] or ''}")
            st.divider()
            st.dataframe(df_ev,use_container_width=True,hide_index=True)


# ══════════════════════════════════════════════════════
# 무역보험
# ══════════════════════════════════════════════════════
with tabs["ins"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("🛡️ 무역보험 등록")
        with st.form("ins_f", clear_on_submit=True):
            a,b=st.columns(2); ins_num=a.text_input("증권번호"); ins_type=b.selectbox("보험유형",["수출보험","수입보험","적하보험","신용보험","환변동보험"])
            insurer=st.selectbox("보험자",["한국무역보험공사(K-SURE)","삼성화재","현대해상","DB손해보험","기타"])
            insured=st.text_input("피보험자(수출자/수입자) *")
            c,d=st.columns(2); cov_amt=c.number_input("보험금액",min_value=0.0,format="%.2f"); cur_ins=d.selectbox("통화",["USD","EUR","KRW"])
            prem=st.number_input("보험료",min_value=0.0,format="%.2f")
            e,f=st.columns(2); sd_ins=e.date_input("보험시작일"); ed_ins=f.date_input("보험만료일",value=pd.Timestamp.now()+pd.Timedelta(days=365))
            claim=st.number_input("보상청구금액",min_value=0.0,format="%.2f"); ins_st=st.selectbox("상태",["유효","만료","청구중","보상완료","취소"])
            note_ins=st.text_area("비고",height=40)
            if st.form_submit_button("✅ 등록",use_container_width=True):
                if not insured: st.error("피보험자 필수")
                else:
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO trade_insurance
                            (insurance_number,insurance_type,insurer,insured,coverage_amount,currency,premium,start_date,end_date,claim_amount,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(
                            ins_num or gen_number("INS"),ins_type,insurer,insured,cov_amt,cur_ins,prem,str(sd_ins),str(ed_ins),claim,ins_st,note_ins))
                        conn.commit(); conn.close(); st.success("등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("보험 목록")
        conn=get_db(); df_ins2=pd.read_sql_query("""
            SELECT insurance_number AS 증권번호, insurance_type AS 유형, insurer AS 보험자,
                   insured AS 피보험자, coverage_amount AS 보험금액, currency AS 통화,
                   premium AS 보험료,
                   CAST(julianday(end_date)-julianday('now') AS INTEGER) AS 잔여일,
                   end_date AS 만료일, status AS 상태
            FROM trade_insurance ORDER BY end_date""", conn); conn.close()
        if df_ins2.empty: st.info("없음")
        else:
            exp_soon=df_ins2[(df_ins2['잔여일']<=30)&(df_ins2['상태']=='유효')]
            if not exp_soon.empty: st.warning(f"⚠️ 30일 내 만료 보험: {len(exp_soon)}건")
            def ins_c(r): return ['background-color:#fee2e2']*len(r) if r['잔여일']<0 and r['상태']=='유효' else ['']*len(r)
            st.dataframe(df_ins2.style.apply(ins_c,axis=1), use_container_width=True, hide_index=True)
            c1,c2=st.columns(2)
            c1.metric("유효 보험건수",len(df_ins2[df_ins2['상태']=='유효']))
            c2.metric("총 보험료",f"${df_ins2['보험료'].sum():,.0f}")


# ══════════════════════════════════════════════════════
# 관세 납부 관리
# ══════════════════════════════════════════════════════
with tabs["duty_pay"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("💴 관세 납부 등록")
        conn=get_db()
        imps_dp=[r for r in conn.execute("SELECT id,decl_number,item_name,customs_duty,vat_amount,total_tax FROM import_declarations WHERE status='수리완료' ORDER BY id DESC").fetchall()]
        conn.close()
        imp_dp_map={f"{r['decl_number']}-{r['item_name']} (총:{r['total_tax']:,.0f}원)":r for r in imps_dp}
        with st.form("dp_f", clear_on_submit=True):
            if not imp_dp_map: st.info("수리완료 수입신고 없음"); st.form_submit_button("등록",disabled=True)
            else:
                dp_sel=st.selectbox("수입신고 *",list(imp_dp_map.keys()))
                dp_d=imp_dp_map[dp_sel]
                a,b=st.columns(2); duty_dp=a.number_input("관세",min_value=0.0,value=float(dp_d['customs_duty']),format="%.0f"); vat_dp=b.number_input("부가세",min_value=0.0,value=float(dp_d['vat_amount']),format="%.0f")
                other_dp=st.number_input("기타세금(교통세 등)",min_value=0.0,format="%.0f")
                total_dp=duty_dp+vat_dp+other_dp; st.info(f"납부총액: ₩{total_dp:,.0f}")
                c,d=st.columns(2); due_dp=c.date_input("납부기한"); paid_dp=d.date_input("실납부일")
                e,f=st.columns(2); pmeth=e.selectbox("납부방법",["계좌이체","관세청고지","분납","카드"]); inst=f.checkbox("분납")
                inst_seq=st.number_input("분납 회차",min_value=1,value=1) if inst else 1
                bref_dp=st.text_input("납부 참조번호"); dpst=st.selectbox("상태",["미납","납부완료","연체","분납중"])
                if st.form_submit_button("✅ 등록",use_container_width=True):
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO customs_payments
                            (payment_number,import_decl_id,decl_number,item_name,duty_amount,vat_amount,other_tax,total_amount,due_date,paid_date,payment_method,bank_ref,installment,installment_seq,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                            gen_number("DPY"),dp_d['id'],dp_d['decl_number'],dp_d['item_name'],
                            duty_dp,vat_dp,other_dp,total_dp,str(due_dp),str(paid_dp),pmeth,bref_dp,
                            1 if inst else 0,inst_seq,dpst))
                        conn.commit(); conn.close(); st.success("납부 등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("관세 납부 현황")
        conn=get_db(); df_dp=pd.read_sql_query("""
            SELECT payment_number AS 납부번호, decl_number AS 신고번호, item_name AS 품목,
                   duty_amount AS 관세, vat_amount AS 부가세, other_tax AS 기타,
                   total_amount AS 납부총액,
                   due_date AS 납부기한,
                   CAST(julianday('now')-julianday(due_date) AS INTEGER) AS 경과일,
                   paid_date AS 납부일, payment_method AS 방법, status AS 상태
            FROM customs_payments ORDER BY due_date""", conn); conn.close()
        if df_dp.empty: st.info("없음")
        else:
            unpaid=df_dp[df_dp['상태'].isin(['미납','연체'])]
            if not unpaid.empty:
                st.error(f"⚠️ 미납·연체: {len(unpaid)}건  |  합계: ₩{unpaid['납부총액'].sum():,.0f}")
            c1,c2,c3=st.columns(3)
            c1.metric("총 관세",f"₩{df_dp['관세'].sum():,.0f}")
            c2.metric("총 부가세",f"₩{df_dp['부가세'].sum():,.0f}")
            c3.metric("납부완료",f"{len(df_dp[df_dp['상태']=='납부완료'])}건")
            def dp_c(r): return ['background-color:#fee2e2']*len(r) if r['상태']=='연체' else (['background-color:#fef9c3']*len(r) if r['상태']=='미납' and r['경과일']>0 else ['']*len(r))
            st.dataframe(df_dp.style.apply(dp_c,axis=1), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════
# 수출 환급금 관리
# ══════════════════════════════════════════════════════
with tabs["refund"]:
    col_form, col_list = st.columns([1, 2])
    with col_form:
        st.subheader("🔄 수출 환급금 신청")
        st.caption("수출에 소요된 원재료 수입 시 납부한 관세를 환급받는 제도")
        conn=get_db()
        exps_rf=[r for r in conn.execute("SELECT id,decl_number,item_name,quantity FROM export_declarations WHERE status IN ('수리완료','선적완료') ORDER BY id DESC").fetchall()]
        conn.close()
        exp_rf_map={f"{r['decl_number']}-{r['item_name']}":r for r in exps_rf}
        with st.form("ref_f", clear_on_submit=True):
            if not exp_rf_map: st.info("수리완료 수출신고 없음"); st.form_submit_button("등록",disabled=True)
            else:
                rf_sel=st.selectbox("수출신고 *",list(exp_rf_map.keys()))
                rf_d=exp_rf_map[rf_sel]
                a,b=st.columns(2); item_rf=a.text_input("품목명",value=rf_d['item_name']); hs_rf=b.text_input("HS Code")
                c,d=st.columns(2); qty_rf=c.number_input("수출수량",min_value=0.0,value=float(rf_d['quantity']),format="%.2f"); paid_duty=d.number_input("납부관세",min_value=0.0,format="%.0f")
                rate_rf=st.slider("환급율(%)",0,100,100)
                refund_amt=round(paid_duty*rate_rf/100,0)
                st.success(f"환급예상액: ₩{refund_amt:,.0f}")
                e2,f2=st.columns(2); appl_d=e2.date_input("신청일"); recv_d=f2.date_input("수령예정일",value=pd.Timestamp.now()+pd.Timedelta(days=30))
                cref_rf=st.text_input("관세청 신고번호"); rf_st=st.selectbox("상태",["신청예정","신청완료","심사중","환급완료","반려"])
                note_rf=st.text_area("비고",height=40)
                if st.form_submit_button("✅ 등록",use_container_width=True):
                    try:
                        conn=get_db()
                        conn.execute("""INSERT INTO export_refunds
                            (refund_number,export_decl_id,decl_number,item_name,hs_code,export_qty,paid_duty,refund_rate,refund_amount,apply_date,receive_date,customs_ref,status,note)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                            gen_number("RFD"),rf_d['id'],rf_d['decl_number'],item_rf,hs_rf,
                            qty_rf,paid_duty,rate_rf,refund_amt,str(appl_d),str(recv_d),cref_rf,rf_st,note_rf))
                        conn.commit(); conn.close(); st.success("신청 등록!"); st.rerun()
                    except Exception as e: st.error(f"오류:{e}")
    with col_list:
        st.subheader("환급금 현황")
        conn=get_db(); df_rf=pd.read_sql_query("""
            SELECT refund_number AS 환급번호, decl_number AS 수출신고번호,
                   item_name AS 품목, paid_duty AS 납부관세,
                   refund_rate AS 환급율, refund_amount AS 환급예정액,
                   apply_date AS 신청일, receive_date AS 수령예정,
                   status AS 상태
            FROM export_refunds ORDER BY id DESC""", conn); conn.close()
        if df_rf.empty: st.info("없음")
        else:
            c1,c2,c3=st.columns(3)
            c1.metric("총 환급신청",f"₩{df_rf['환급예정액'].sum():,.0f}")
            c2.metric("환급완료",f"₩{df_rf[df_rf['상태']=='환급완료']['환급예정액'].sum():,.0f}")
            c3.metric("심사중",f"{len(df_rf[df_rf['상태']=='심사중'])}건")
            def rf_c(v): return "background-color:#d1fae5" if v=="환급완료" else ("background-color:#fef3c7" if v=="심사중" else "")
            st.dataframe(df_rf.style.map(rf_c,subset=['상태']), use_container_width=True, hide_index=True)

            try:
                import plotly.express as px
                fig=px.bar(df_rf.groupby('상태')['환급예정액'].sum().reset_index(),
                           x='상태',y='환급예정액',color='상태',title="환급금 상태별 현황",
                           color_discrete_map={"신청예정":"#94a3b8","신청완료":"#3b82f6","심사중":"#f97316","환급완료":"#22c55e","반려":"#ef4444"})
                fig.update_layout(height=260,margin=dict(l=0,r=0,t=40,b=0),showlegend=False)
                st.plotly_chart(fig,use_container_width=True)
            except: pass
