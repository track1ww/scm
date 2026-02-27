"""
외부 API 연동 모듈
- 한국은행 ECOS API        : 일별 환율 조회
- 관세청 UNI-PASS API      : 과세환율 / HS Code 세율 / 화물 통관진행 조회
- 전략물자관리원 YESTRADE  : 전략물자 해당 여부 판정 조회
- 관세청 FTA 포털          : FTA 협정세율 조회
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from utils.db import get_db

# ─────────────────────────────────────────────────────────
# API 키 DB 관리
# ─────────────────────────────────────────────────────────

def _ensure_api_settings_table():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS api_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_name TEXT UNIQUE NOT NULL,
        key_value TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    conn.commit()
    conn.close()

def get_api_keys() -> dict:
    _ensure_api_settings_table()
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT key_name, key_value FROM api_settings").fetchall()]
    conn.close()
    return {r['key_name']: r['key_value'] for r in rows}

def save_api_key(key_name: str, key_value: str):
    _ensure_api_settings_table()
    conn = get_db()
    conn.execute("""INSERT INTO api_settings(key_name, key_value)
        VALUES(?,?) ON CONFLICT(key_name) DO UPDATE SET
        key_value=excluded.key_value, updated_at=datetime('now','localtime')""",
        (key_name, key_value))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────
# ① 한국은행 ECOS API — 일별 환율
#    통계표코드: 036Y001
#    https://ecos.bok.or.kr
# ─────────────────────────────────────────────────────────

BOK_CURRENCY_CODES = {
    "USD": "0000001", "EUR": "0000002", "JPY": "0000003",
    "CNY": "0000053", "GBP": "0000004", "SGD": "0000034",
    "AUD": "0000005", "CAD": "0000007", "HKD": "0000013",
    "THB": "0000039",
}

def fetch_bok_exchange_rates(api_key: str, date: str = None) -> dict:
    """
    한국은행 ECOS API 환율 조회
    Returns: {"USD": 1350.5, ...}  실패 시 {"error": "..."}
    """
    if not date:
        date = datetime.now().strftime("%Y%m%d")

    results, errors = {}, []
    for currency, code in BOK_CURRENCY_CODES.items():
        url = (f"https://ecos.bok.or.kr/api/StatisticSearch"
               f"/{api_key}/json/kr/1/1/036Y001/DD/{date}/{date}/{code}")
        try:
            resp = requests.get(url, timeout=6)
            data = resp.json()
            if "StatisticSearch" in data:
                rows = data["StatisticSearch"].get("row", [])
                if rows:
                    val = rows[0].get("DATA_VALUE", "")
                    if val and val != "-":
                        rate = float(val.replace(",", ""))
                        results[currency] = round(rate / 100 if currency == "JPY" else rate, 2)
            elif "RESULT" in data:
                msg = data["RESULT"].get("MESSAGE", "오류")
                if data["RESULT"].get("CODE","") != "INFO-000":
                    errors.append(f"{currency}: {msg}")
        except Exception as e:
            errors.append(f"{currency}: {e}")

    if not results and errors:
        return {"error": " | ".join(errors)}
    if errors:
        results["_warnings"] = errors
    return results


# ─────────────────────────────────────────────────────────
# ② 관세청 UNI-PASS — 과세환율 (주간, 수출입 공식 환율)
#    공공데이터포털 서비스명: 관세청_관세환율정보(GW)
#    https://www.data.go.kr/data/15101230/openapi.do
# ─────────────────────────────────────────────────────────

UNIPASS_CURRENCY_CODES = {
    "USD": "US", "EUR": "EU", "JPY": "JP",
    "CNY": "CN", "GBP": "GB", "SGD": "SG",
    "AUD": "AU", "CAD": "CA", "HKD": "HK",
    "THB": "TH",
}

def fetch_unipass_customs_rate(api_key: str, import_export: str = "2") -> dict:
    """
    관세청 과세환율 조회 (주간 공식 환율)
    import_export: "1"=수출, "2"=수입
    Returns: {"USD": 1352.0, ...}
    """
    today = datetime.now().strftime("%Y%m%d")
    url = (
        f"https://unipass.customs.go.kr/csp/cstd/cstd/cstdGW/custExrtMrtChag"
        f"/retrieveCustExrtMrtChag.do"
        f"?crkyCn={api_key}&imexTp={import_export}&applBgnDt={today}"
    )
    try:
        resp = requests.get(url, timeout=8)
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.text)
        results = {}
        for item in root.findall(".//item"):
            curr_cd = item.findtext("currSgn") or item.findtext("currCd") or ""
            rate_val = item.findtext("aplExrt") or item.findtext("exrt") or ""
            unit_val = item.findtext("untQty") or "1"
            if curr_cd and rate_val:
                try:
                    rate = float(rate_val.replace(",", ""))
                    unit = int(unit_val) if unit_val.isdigit() else 1
                    results[curr_cd] = round(rate / unit, 4)
                except:
                    pass
        return results if results else {"error": "과세환율 데이터 없음 (당일 미고시일 수 있음)"}
    except ET.ParseError:
        return {"error": f"XML 파싱 오류. 응답: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────
# ③ 관세청 UNI-PASS — HS Code 세율 조회
#    관세율표 품목분류 + 기본세율 + FTA 세율
# ─────────────────────────────────────────────────────────

def fetch_unipass_tariff(api_key: str, hs_code: str) -> dict:
    """
    관세청 UNI-PASS API HS Code 세율 조회
    Returns: {"hs_code":..., "description":..., "import_duty_rate":...,
              "vat_rate":10.0, "unit":..., "fta_rates":[...]}
    """
    clean_code = hs_code.replace(".", "").replace(" ", "").ljust(10, "0")
    url = (
        f"https://unipass.customs.go.kr/csp/cstd/tariff/openCSWTRFTRRT001Q.do"
        f"?crkyCn={api_key}&hsSgn={clean_code}"
        f"&applBgnDt={datetime.now().strftime('%Y%m%d')}"
    )
    try:
        resp = requests.get(url, timeout=8)
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.text)

        result = {
            "hs_code": clean_code, "description": "",
            "import_duty_rate": 0.0, "vat_rate": 10.0,
            "unit": "KG", "fta_rates": []
        }
        for item in root.findall(".//item"):
            result["description"]       = item.findtext("hsSgnNm") or item.findtext("itemNmKr") or result["description"]
            basic = item.findtext("bscTrfRt") or item.findtext("applTrfRt") or ""
            if basic:
                try: result["import_duty_rate"] = float(basic.replace("%","").strip())
                except: pass
            unit = item.findtext("untNm") or ""
            if unit: result["unit"] = unit
            vat  = item.findtext("vatRt") or ""
            if vat:
                try: result["vat_rate"] = float(vat.replace("%","").strip())
                except: pass
            for fta in item.findall(".//ftaTrfRtList") + item.findall(".//ftaItem"):
                agr  = fta.findtext("ftaNm") or fta.findtext("agreementNm") or ""
                rate = fta.findtext("ftaTrfRt") or fta.findtext("trfRt") or ""
                if agr and rate:
                    try: result["fta_rates"].append({"agreement": agr, "rate": float(rate.replace("%","").strip())})
                    except: pass
        return result
    except ET.ParseError:
        return {"error": f"XML 파싱 오류"}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────
# ④ 관세청 UNI-PASS — 화물 통관진행 조회
#    화물관리번호 또는 B/L 번호로 실시간 통관 상태 확인
# ─────────────────────────────────────────────────────────

def fetch_unipass_cargo_status(api_key: str, bl_number: str = None, cargo_number: str = None) -> dict:
    """
    관세청 화물 통관진행정보 조회
    bl_number 또는 cargo_number 중 하나 필수
    """
    if not bl_number and not cargo_number:
        return {"error": "B/L 번호 또는 화물관리번호 필요"}

    params = f"crkyCn={api_key}"
    if bl_number:
        params += f"&mblNo={bl_number}"
    if cargo_number:
        params += f"&cargMtNo={cargo_number}"

    url = (f"https://unipass.customs.go.kr/csp/cstd/cstd/cstdGW/custCargPrgsInfoQry"
           f"/retrieveCustCargPrgsInfo.do?{params}")
    try:
        resp = requests.get(url, timeout=8)
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.text)

        result = {"bl_number": bl_number, "cargo_number": cargo_number, "status_list": []}
        for item in root.findall(".//item"):
            result["status_list"].append({
                "date":   item.findtext("prcsDttm") or item.findtext("prcsYmd") or "",
                "status": item.findtext("cargSttsCd") or item.findtext("prgsStts") or "",
                "desc":   item.findtext("cargSttsNm") or item.findtext("prgsSttsNm") or "",
                "place":  item.findtext("lodgNm") or item.findtext("plcNm") or "",
            })
        if not result["status_list"]:
            result["message"] = "조회된 통관 진행정보 없음"
        return result
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────
# ⑤ 전략물자관리원 YESTRADE — 전략물자 판정 조회
#    https://www.yestrade.go.kr
#    회원가입 → 마이페이지 → OpenAPI 신청
# ─────────────────────────────────────────────────────────

# 전략물자 통제 목록 (내장 DB - YESTRADE API 보완용)
# 출처: 대외무역법 별표2, 전략물자관리원 공개 목록
STRATEGIC_GOODS_LIST = {
    # HS코드 앞 6자리: (통제유형, 설명, 위험도)
    "847130": ("EAR/WA", "노트북/휴대용 컴퓨터 - 고성능 암호화 해당 시 통제", "주의"),
    "847141": ("WA",     "병렬처리 컴퓨터 - 성능에 따라 통제", "높음"),
    "854169": ("WA/NSG", "반도체 소자 - 특정 사양 통제", "주의"),
    "880240": ("MTCR",   "무인항공기(드론) - 탑재중량/사거리 초과 시 통제", "높음"),
    "880260": ("MTCR",   "우주발사체 관련 - 전면 통제", "매우높음"),
    "930190": ("WA",     "군용 총기류 - 전면 통제", "매우높음"),
    "930200": ("WA",     "권총/리볼버 - 전면 통제", "매우높음"),
    "284410": ("NSG",    "우라늄 광석 - 핵비확산 통제", "매우높음"),
    "284420": ("NSG",    "우라늄/토륨 화합물 - 핵비확산 통제", "매우높음"),
    "381400": ("CWC/AG", "유기용제 - 화학무기 전용가능 품목 확인 필요", "주의"),
    "292910": ("CWC/AG", "이소시아네이트류 - 화학무기 원료 해당 여부 확인", "주의"),
    "854390": ("WA/EAR", "전자장비 - 군용 전자전 장비 해당 시 통제", "주의"),
    "901380": ("WA",     "광학기기 - 군용 광학장비 해당 시 통제", "주의"),
    "732111": ("WA",     "특수합금/금속 - 군용 소재 해당 시 통제", "주의"),
}

# 금수/제재 국가 목록 (UN 안보리 제재 기준)
# ── 제재/수출통제 국가 분류 (한국 기준) ──────────────────────────────
# 출처: 대외무역법, 전략물자수출입고시, 외교부 제재 현황
# 주의: 상황은 수시로 변경됨 — 최신 정보는 전략물자관리원(yestrade.go.kr) 확인

# ① 전면 금수 (수출 불가) — UN 안보리 제재 + 한국 동참
SANCTIONED_COUNTRIES_FULL = {
    "KP": ("북한", "UN 안보리 결의 - 전면 금수, 모든 품목 수출 불가"),
}

# ② 상황허가 대상국 (특정 품목 수출 시 산업부 허가 필요, 비해당 품목은 수출 가능)
# 한국은 미국·EU처럼 전면 금수가 아닌 '품목별 상황허가' 방식 채택
SANCTIONED_COUNTRIES_PARTIAL = {
    "RU": ("러시아",   "한국 상황허가 대상 — 1,402개 품목 수출 시 산업통상자원부 허가 필요 (비해당 품목 수출 가능)"),
    "BY": ("벨라루스", "한국 상황허가 대상 — 러시아와 동일 품목군 통제"),
    "IR": ("이란",     "UN/미국 제재 동참 — 핵·미사일 관련 품목 통제, 전략물자관리원 확인 필요"),
    "SY": ("시리아",   "UN 제재 — 군수물자 및 이중용도 품목 통제"),
    "MM": ("미얀마",   "EU·미국 제재 — 군수물자 수출 금지, 한국 독자 제재는 없으나 주의 요망"),
    "CU": ("쿠바",     "미국 엠바고 — 한국 독자 제재 없으나 미국산 부품 포함 시 재수출 금지"),
    "VE": ("베네수엘라","미국 제재 — 한국 독자 제재 없으나 전략물자 포함 품목 주의"),
}

# 하위호환용 통합 dict (기존 코드 호환)
SANCTIONED_COUNTRIES = {
    **{k: v for k, v in SANCTIONED_COUNTRIES_FULL.items()},
    **{k: v for k, v in SANCTIONED_COUNTRIES_PARTIAL.items()},
}

def check_strategic_goods_local(hs_code: str, destination_country_code: str = "") -> dict:
    """
    내장 전략물자 목록으로 1차 스크리닝 (YESTRADE API 없이도 사용 가능)
    """
    clean_hs = hs_code.replace(".", "").replace(" ", "")[:6]
    result = {
        "hs_code": hs_code,
        "destination": destination_country_code.upper(),
        "strategic_match": False,
        "sanction_match": False,
        "control_type": "",
        "description": "",
        "risk_level": "없음",
        "sanction_info": "",
        "recommendation": "수출 가능 (추가 확인 권장)",
        "source": "내장 DB (YESTRADE API 미연동 시 참고용)"
    }

    # HS Code 전략물자 체크
    if clean_hs in STRATEGIC_GOODS_LIST:
        ctrl_type, desc, risk = STRATEGIC_GOODS_LIST[clean_hs]
        result.update({
            "strategic_match": True,
            "control_type": ctrl_type,
            "description": desc,
            "risk_level": risk,
            "recommendation": "⚠️ 전략물자관리원(yestrade.go.kr) 사전 판정 필수"
        })

    # 제재국 체크 (전면 금수 vs 상황허가 구분)
    country_upper = destination_country_code.upper()
    if country_upper in SANCTIONED_COUNTRIES_FULL:
        country_name, sanction_desc = SANCTIONED_COUNTRIES_FULL[country_upper]
        result.update({
            "sanction_match": True,
            "sanction_info": f"{country_name}: {sanction_desc}",
            "risk_level": "매우높음",
            "recommendation": "🚨 전면 금수 국가 — 수출 불가 (대외무역법)"
        })
    elif country_upper in SANCTIONED_COUNTRIES_PARTIAL:
        country_name, sanction_desc = SANCTIONED_COUNTRIES_PARTIAL[country_upper]
        result.update({
            "sanction_match": True,
            "sanction_info": f"{country_name}: {sanction_desc}",
            "risk_level": "높음",
            "recommendation": f"⚠️ 수출통제 대상국 — 해당 품목 여부 확인 후 산업통상자원부 상황허가 신청 필요 (전략물자관리원 02-6000-6496)"
        })

    return result


def fetch_yestrade_check(api_key: str, hs_code: str, destination: str, item_name: str = "") -> dict:
    """
    YESTRADE API 전략물자 판정 조회
    API 키 없으면 내장 DB로 fallback
    """
    if not api_key:
        return check_strategic_goods_local(hs_code, destination)

    clean_hs = hs_code.replace(".", "").replace(" ", "").ljust(10, "0")
    url = (
        f"https://www.yestrade.go.kr/api/goodsJdgmnt/goodsJdgmntSearch.do"
        f"?apiKey={api_key}&hsCode={clean_hs}&dstNatCd={destination}"
    )
    try:
        resp = requests.get(url, timeout=8)
        resp.encoding = "utf-8"

        # JSON 응답 시도
        try:
            data = resp.json()
            if isinstance(data, dict):
                return {
                    "hs_code": hs_code,
                    "destination": destination,
                    "strategic_match": data.get("isStrategic", False),
                    "control_type": data.get("controlType", ""),
                    "description": data.get("itemDesc", ""),
                    "risk_level": data.get("riskLevel", ""),
                    "recommendation": data.get("recommendation", ""),
                    "source": "YESTRADE API"
                }
        except:
            pass

        # XML 응답 시도
        root = ET.fromstring(resp.text)
        result_code = root.findtext(".//resultCode") or ""
        if result_code != "00":
            # API 실패 시 내장 DB로 fallback
            local = check_strategic_goods_local(hs_code, destination)
            local["source"] = "내장 DB (YESTRADE API 응답 오류 - fallback)"
            return local

        return {
            "hs_code": hs_code,
            "destination": destination,
            "strategic_match": root.findtext(".//isStrategic") == "Y",
            "control_type": root.findtext(".//ctrlTpNm") or "",
            "description": root.findtext(".//goodsNm") or "",
            "risk_level": root.findtext(".//riskLvl") or "",
            "recommendation": root.findtext(".//jdgmntCntn") or "",
            "source": "YESTRADE API"
        }
    except Exception as e:
        # 네트워크 오류 시 내장 DB로 fallback
        local = check_strategic_goods_local(hs_code, destination)
        local["source"] = f"내장 DB (YESTRADE 연결 실패: {str(e)[:50]})"
        return local


# ─────────────────────────────────────────────────────────
# ⑥ 관세청 FTA 포털 — FTA 협정세율 조회
#    UNI-PASS 키 동일 사용
# ─────────────────────────────────────────────────────────

# 내장 FTA 협정 목록 (API 없을 때 fallback)
FTA_AGREEMENTS_KR = [
    {"code": "KR-US",    "name": "한-미 FTA",      "countries": ["US"],
     "effective": "2012-03-15", "origin_criteria": "세번변경기준(CTH) 또는 부가가치기준(RVC 35% 이상)"},
    {"code": "KR-EU",    "name": "한-EU FTA",      "countries": ["DE","FR","IT","ES","NL","BE","PL","SE","AT","DK","FI","PT","IE","GR","CZ","RO","HU","BG","SK","HR","LT","LV","EE","SI","CY","LU","MT"],
     "effective": "2011-07-01", "origin_criteria": "부가가치기준(RVC 45% 이상) 또는 세번변경기준"},
    {"code": "KR-CN",    "name": "한-중 FTA",      "countries": ["CN"],
     "effective": "2015-12-20", "origin_criteria": "세번변경기준(CTH) 또는 부가가치기준(RVC 40% 이상)"},
    {"code": "KR-ASEAN", "name": "한-ASEAN FTA",   "countries": ["VN","TH","ID","MY","PH","SG","MM","KH","LA","BN"],
     "effective": "2007-06-01", "origin_criteria": "부가가치기준(RVC 40% 이상) 또는 세번변경기준"},
    {"code": "RCEP",     "name": "RCEP",            "countries": ["JP","CN","AU","NZ","VN","TH","ID","MY","PH","SG","MM","KH","LA","BN"],
     "effective": "2022-02-01", "origin_criteria": "부가가치기준(RVC 40% 이상) 또는 세번변경기준(CTH)"},
    {"code": "KR-GB",    "name": "한-영 FTA",      "countries": ["GB"],
     "effective": "2021-01-01", "origin_criteria": "한-EU FTA와 동일 기준 적용"},
    {"code": "KR-AU",    "name": "한-호주 FTA",    "countries": ["AU"],
     "effective": "2014-12-12", "origin_criteria": "부가가치기준(RVC 40% 이상)"},
    {"code": "KR-CA",    "name": "한-캐나다 FTA",  "countries": ["CA"],
     "effective": "2015-01-01", "origin_criteria": "세번변경기준 또는 부가가치기준(RVC 35%)"},
    {"code": "KR-NZ",    "name": "한-뉴질랜드 FTA","countries": ["NZ"],
     "effective": "2015-12-20", "origin_criteria": "부가가치기준(RVC 45% 이상)"},
    {"code": "KR-VN",    "name": "한-베트남 FTA",  "countries": ["VN"],
     "effective": "2015-12-20", "origin_criteria": "부가가치기준(RVC 40% 이상)"},
    {"code": "KR-IN",    "name": "한-인도 CEPA",   "countries": ["IN"],
     "effective": "2010-01-01", "origin_criteria": "부가가치기준(RVC 35% 이상)"},
    {"code": "KR-TR",    "name": "한-터키 FTA",    "countries": ["TR"],
     "effective": "2013-05-01", "origin_criteria": "세번변경기준 또는 부가가치기준"},
    {"code": "KR-CO",    "name": "한-콜롬비아 FTA","countries": ["CO"],
     "effective": "2016-07-15", "origin_criteria": "부가가치기준(RVC 35% 이상)"},
    {"code": "KR-PE",    "name": "한-페루 FTA",    "countries": ["PE"],
     "effective": "2011-08-01", "origin_criteria": "부가가치기준(RVC 40% 이상)"},
    {"code": "KR-SG",    "name": "한-싱가포르 FTA","countries": ["SG"],
     "effective": "2006-03-02", "origin_criteria": "세번변경기준 또는 부가가치기준(RVC 40%)"},
]

def get_applicable_fta(destination_country_code: str) -> list:
    """목적국 기준 적용 가능한 FTA 협정 목록 반환"""
    country = destination_country_code.upper()
    applicable = []
    for fta in FTA_AGREEMENTS_KR:
        if country in [c.upper() for c in fta["countries"]]:
            applicable.append(fta)
    return applicable

def fetch_unipass_fta_rate(api_key: str, hs_code: str, country_code: str) -> dict:
    """
    관세청 FTA 포털 협정세율 조회
    API 실패 시 내장 FTA 목록으로 fallback
    """
    clean_hs = hs_code.replace(".", "").replace(" ", "").ljust(10, "0")
    url = (
        f"https://unipass.customs.go.kr/csp/cstd/tariff/openCSWTRFTRFT001Q.do"
        f"?crkyCn={api_key}&hsSgn={clean_hs}&natCd={country_code.upper()}"
        f"&applBgnDt={datetime.now().strftime('%Y%m%d')}"
    )
    try:
        resp = requests.get(url, timeout=8)
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.text)
        fta_rates = []
        for item in root.findall(".//item"):
            agr  = item.findtext("ftaNm") or item.findtext("agreementNm") or ""
            rate = item.findtext("ftaTrfRt") or item.findtext("trfRt") or ""
            criteria = item.findtext("orgNatCrtNm") or ""
            if agr and rate:
                try:
                    fta_rates.append({
                        "agreement": agr,
                        "rate": float(rate.replace("%","").strip()),
                        "origin_criteria": criteria,
                        "source": "UNI-PASS API"
                    })
                except:
                    pass
        if fta_rates:
            return {"hs_code": hs_code, "country": country_code, "fta_rates": fta_rates}
    except:
        pass

    # Fallback: 내장 FTA 목록
    applicable = get_applicable_fta(country_code)
    return {
        "hs_code": hs_code,
        "country": country_code,
        "fta_rates": [{"agreement": f["name"], "rate": None,
                       "origin_criteria": f["origin_criteria"],
                       "source": "내장 DB (세율은 HS Code별 상이 - UNI-PASS 조회 필요)"}
                      for f in applicable],
        "note": "API 조회 실패 - 내장 FTA 협정 목록 표시 (세율은 별도 확인 필요)"
    }


# ─────────────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────────────

def save_exchange_rates_to_db(rates: dict, source: str = "API") -> int:
    """조회한 환율을 DB에 저장, 저장 건수 반환"""
    if "error" in rates:
        return 0
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    saved = 0
    for currency, rate in rates.items():
        if currency.startswith("_") or not isinstance(rate, (int, float)):
            continue
        conn.execute("""INSERT INTO exchange_rates(currency, rate_to_krw, rate_date, source)
            VALUES(?,?,?,?)""", (currency, rate, today, source))
        saved += 1
    conn.commit()
    conn.close()
    return saved

def save_tariff_to_db(hs_code: str, tariff_data: dict) -> bool:
    if "error" in tariff_data:
        return False
    conn = get_db()
    conn.execute("""INSERT INTO hs_codes
        (hs_code, description, import_duty_rate, vat_rate, unit)
        VALUES(?,?,?,?,?)
        ON CONFLICT(hs_code) DO UPDATE SET
        description=excluded.description, import_duty_rate=excluded.import_duty_rate,
        vat_rate=excluded.vat_rate, unit=excluded.unit""",
        (hs_code, tariff_data.get("description",""),
         tariff_data.get("import_duty_rate",0.0),
         tariff_data.get("vat_rate",10.0),
         tariff_data.get("unit","KG")))
    conn.commit()
    conn.close()
    return True

def get_latest_rates_from_db() -> dict:
    conn = get_db()
    rows = [dict(r) for r in conn.execute("""
        SELECT currency, rate_to_krw FROM exchange_rates
        WHERE id IN (SELECT MAX(id) FROM exchange_rates GROUP BY currency)
    """).fetchall()]
    conn.close()
    return {r['currency']: r['rate_to_krw'] for r in rows}

def convert_to_krw(amount: float, currency: str, rates: dict = None) -> float:
    if currency == "KRW":
        return amount
    if rates is None:
        rates = get_latest_rates_from_db()
    return amount * rates.get(currency, 0)
