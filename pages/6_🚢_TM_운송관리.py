import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db, gen_number, init_trade_db
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

tabs = st.tabs([
    "🔑 API 설정",
    "💱 환율 관리",
    "📦 HS Code",
    "🌐 FTA 관리",
    "📄 CI / B/L",
    "📥 수입신고",
    "📤 수출면장",
    "💳 L/C 신용장",
    "🔍 수입요건",
    "⚠️ 전략물자",
    "🚛 운송오더",
    "📊 현황",
])

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
                            ON CONFLICT(hs_code) DO UPDATE SET
                            description=excluded.description,
                            import_duty_rate=excluded.import_duty_rate,
                            vat_rate=excluded.vat_rate,
                            unit=excluded.unit, special_notes=excluded.special_notes""",
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
                            VALUES(?,?,?,?,?,?,?,?,?,datetime('now','localtime'),?)""",
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
