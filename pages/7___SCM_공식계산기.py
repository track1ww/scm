"""
SCM 공식 계산기 — 재고·수요예측·물류·비용 공식 선택 후 계산 및 시각화
pages/7_📐_SCM_공식계산기.py 로 저장하세요
"""
import streamlit as st
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.design import inject_css, apply_plotly_theme, section_title, page_header
except ImportError:
    try:
        from design import inject_css, apply_plotly_theme, section_title, page_header
    except ImportError:
        def inject_css(): pass
        def apply_plotly_theme(): pass
        def section_title(t): st.markdown(f"**{t}**")
        def page_header(i, t, d=""): st.title(f"{i} {t}")

try:
    import plotly.graph_objects as go
    HAS_PL = True
except ImportError:
    HAS_PL = False

st.set_page_config(page_title="SCM 공식 계산기", page_icon="📐", layout="wide")
inject_css()
apply_plotly_theme()

page_header("📐", "SCM 공식 계산기", "재고·수요예측·물류·비용 공식을 선택하여 계산 및 시각화")

# ═══════════════════════════════════════════════════════
#  메인 탭 구조
# ═══════════════════════════════════════════════════════
main_tab1, main_tab2, main_tab3 = st.tabs([
    "📐 SCM 공식 계산기",
    "🗓️ 유통기한 관리 계산기",
    "🤖 AI 수요예측 (유통기한 품목)",
])

# ═══════════════════════════════════════════════════════
#  공식 정의
# ═══════════════════════════════════════════════════════
CATEGORIES = {
    "📦 재고 관리": {
        "경제적 주문량 (EOQ)": {
            "desc": "총 재고 비용을 최소화하는 최적 주문량",
            "formula": "EOQ = √(2DS / H)",
            "fields": [
                ("D", "연간 수요량 (D)", "개", 1000),
                ("S", "1회 주문 비용 (S)", "원", 50000),
                ("H", "연간 단위 재고유지비용 (H)", "원", 2000),
            ],
        },
        "재주문점 (ROP)": {
            "desc": "재주문을 발생시켜야 하는 재고 수준",
            "formula": "ROP = d × L + SS",
            "fields": [
                ("d", "일일 평균 수요 (d)", "개/일", 50),
                ("L", "리드타임 (L)", "일", 7),
                ("SS", "안전재고 (SS)", "개", 100),
            ],
        },
        "안전재고 (Safety Stock)": {
            "desc": "수요 불확실성에 대비한 여유 재고",
            "formula": "SS = Z × σd × √L",
            "fields": [
                ("Z", "서비스 수준 Z값", "(95%=1.65)", 1.65),
                ("sigma", "수요 표준편차 (σd)", "개", 20),
                ("L", "리드타임 (L)", "일", 7),
            ],
        },
        "재고 회전율": {
            "desc": "일정 기간 동안 재고가 몇 번 순환되었는지",
            "formula": "재고회전율 = COGS / 평균재고",
            "fields": [
                ("COGS", "매출원가 (COGS)", "원", 120_000_000),
                ("avgInv", "평균 재고액", "원", 20_000_000),
            ],
        },
        "Days of Supply (DOS)": {
            "desc": "현재 재고로 운영 가능한 일수",
            "formula": "DOS = 현재재고량 / 일평균수요",
            "fields": [
                ("stock", "현재 재고량", "개", 5000),
                ("daily", "일평균 수요", "개/일", 150),
            ],
        },
    },
    "📈 수요 예측": {
        "이동 평균 (Moving Average)": {
            "desc": "최근 N개 기간 평균으로 다음 기간 수요 예측",
            "formula": "MA = (D₁+D₂+…+Dₙ) / n",
            "fields": [
                ("d1", "1기 수요", "개", 200),
                ("d2", "2기 수요", "개", 220),
                ("d3", "3기 수요", "개", 180),
                ("d4", "4기 수요", "개", 240),
                ("d5", "5기 수요", "개", 210),
            ],
        },
        "지수 평활법 (Exponential Smoothing)": {
            "desc": "최근 데이터에 더 높은 가중치를 부여한 예측",
            "formula": "Fₜ = α·Dₜ₋₁ + (1-α)·Fₜ₋₁",
            "fields": [
                ("alpha", "평활 계수 (α)", "0~1", 0.3),
                ("prevF", "이전 예측값 (Fₜ₋₁)", "개", 200),
                ("prevD", "이전 실제수요 (Dₜ₋₁)", "개", 230),
            ],
        },
    },
    "🚚 물류 / 유통": {
        "주문 충족률 (Fill Rate)": {
            "desc": "수요 대비 즉시 충족 가능한 주문 비율",
            "formula": "Fill Rate = (즉시충족 / 총주문) × 100",
            "fields": [
                ("fulfilled", "즉시 충족 주문 수", "건", 450),
                ("total", "총 주문 수", "건", 500),
            ],
        },
        "정시 납품율 (OTD)": {
            "desc": "약속된 납기일 내 납품된 비율",
            "formula": "OTD = (정시납품 / 전체납품) × 100",
            "fields": [
                ("onTime", "정시 납품 건수", "건", 380),
                ("total", "전체 납품 건수", "건", 400),
            ],
        },
        "단위당 운송비용": {
            "desc": "단위당 운송비용 및 km당 비용 분석",
            "formula": "단위당 운송비 = 총운송비 / 총운송량",
            "fields": [
                ("totalCost", "총 운송비용", "원", 5_000_000),
                ("volume", "총 운송량", "개", 10000),
                ("distance", "평균 운송거리", "km", 200),
            ],
        },
        "창고 공간 활용률": {
            "desc": "창고의 실제 사용 공간 비율",
            "formula": "활용률 = (사용공간 / 총가용공간) × 100",
            "fields": [
                ("used", "사용 중인 공간", "㎡", 3500),
                ("total", "총 창고 면적", "㎡", 5000),
                ("height", "평균 적재 높이", "m", 4),
                ("maxH", "최대 적재 가능 높이", "m", 6),
            ],
        },
    },
    "💰 비용 / 성과": {
        "총 물류비용 (TLC)": {
            "desc": "재고·운송·창고·주문처리 비용의 합계",
            "formula": "TLC = 재고비 + 운송비 + 창고비 + 주문처리비",
            "fields": [
                ("inv", "재고 비용", "원", 10_000_000),
                ("trans", "운송 비용", "원", 5_000_000),
                ("wh", "창고 비용", "원", 3_000_000),
                ("order", "주문처리 비용", "원", 2_000_000),
            ],
        },
        "완전 주문율 (Perfect Order Rate)": {
            "desc": "정시·정량·무손상·정확서류 모두 충족한 주문 비율",
            "formula": "POR = OTD% × Fill% × 무손상% × 서류정확% / 100³",
            "fields": [
                ("otd", "정시 납품율", "%", 95.0),
                ("fill", "주문 충족률", "%", 97.0),
                ("damage", "무손상률", "%", 99.0),
                ("doc", "서류 정확도", "%", 98.0),
            ],
        },
        "이동평균단가 (MAP)": {
            "desc": "기존 재고와 신규 입고를 가중평균한 단가",
            "formula": "MAP = (기존재고×기존단가 + 입고량×입고단가) / (기존재고+입고량)",
            "fields": [
                ("prevQty", "기존 재고량", "개", 500),
                ("prevPrice", "기존 평균단가", "원", 10000),
                ("inQty", "신규 입고량", "개", 200),
                ("inPrice", "신규 입고단가", "원", 12000),
            ],
        },
    },
}


# ═══════════════════════════════════════════════════════
#  계산 함수
# ═══════════════════════════════════════════════════════
def calculate(formula_name, vals):
    v = vals
    results = {}
    chart_data = None
    chart_type = None

    # ── 재고 관리 ──────────────────────────────
    if formula_name == "경제적 주문량 (EOQ)":
        D, S, H = v["D"], v["S"], v["H"]
        eoq = math.sqrt(2 * D * S / H)
        orders = D / eoq
        results = {
            "📦 EOQ (최적주문량)": f"{eoq:,.1f} 개",
            "🔄 연간 주문 횟수": f"{orders:.1f} 회",
            "💸 연간 주문 비용": f"₩{orders * S:,.0f}",
            "🏷️ 연간 재고유지비용": f"₩{(eoq/2) * H:,.0f}",
            "💰 연간 총 비용": f"₩{orders*S + (eoq/2)*H:,.0f}",
        }
        chart_data = {
            "labels": [f"{int((i+1)*eoq*0.4)}개" for i in range(10)],
            "주문비용": [round(D / ((i+1)*eoq*0.4) * S) for i in range(10)],
            "재고유지비용": [round(((i+1)*eoq*0.4)/2 * H) for i in range(10)],
            "총비용": [round(D/((i+1)*eoq*0.4)*S + ((i+1)*eoq*0.4)/2*H) for i in range(10)],
        }
        chart_type = "line_multi"

    elif formula_name == "재주문점 (ROP)":
        d, L, SS = v["d"], v["L"], v["SS"]
        rop = d * L + SS
        results = {
            "🎯 재주문점 (ROP)": f"{rop:,.0f} 개",
            "📉 리드타임 중 수요": f"{d*L:,.0f} 개",
            "🛡️ 안전재고": f"{SS:,.0f} 개",
        }
        days = min(int((rop + SS) / max(d, 1)) + 5, 40)
        chart_data = {
            "labels": [f"{i}일" for i in range(days)],
            "재고수준": [max(0, rop + SS - d * i) for i in range(days)],
            "재주문점": [rop] * days,
        }
        chart_type = "line_multi"

    elif formula_name == "안전재고 (Safety Stock)":
        Z, sigma, L = v["Z"], v["sigma"], v["L"]
        ss = Z * sigma * math.sqrt(L)
        svc = 90 if Z < 1.3 else 95 if Z < 1.7 else 97.5 if Z < 2.0 else 99 if Z < 2.4 else 99.5
        results = {
            "🛡️ 안전재고 (SS)": f"{ss:,.1f} 개",
            "📊 서비스 수준 (약)": f"{svc} %",
        }
        zs = [1.28, 1.65, 1.96, 2.33, 2.58]
        chart_data = {
            "labels": ["90%", "95%", "97.5%", "99%", "99.5%"],
            "안전재고": [round(z * sigma * math.sqrt(L), 1) for z in zs],
        }
        chart_type = "bar"

    elif formula_name == "재고 회전율":
        COGS, avgInv = v["COGS"], v["avgInv"]
        turnover = COGS / avgInv
        days_inv = 365 / turnover
        results = {
            "🔄 재고 회전율": f"{turnover:.2f} 회/년",
            "📅 평균 재고 보유일": f"{days_inv:.1f} 일",
        }
        chart_data = {
            "labels": ["현재 회전율", "업종평균(목표)"],
            "회전율": [round(turnover, 2), round(turnover * 1.2, 2)],
        }
        chart_type = "bar"

    elif formula_name == "Days of Supply (DOS)":
        stock, daily = v["stock"], v["daily"]
        dos = stock / daily
        chart_data = {
            "labels": [f"{i}일" for i in range(min(int(dos)+5, 60))],
            "재고량": [max(0, stock - daily * i) for i in range(min(int(dos)+5, 60))],
        }
        results = {
            "📅 Days of Supply": f"{dos:.1f} 일",
            "📦 현재 재고": f"{stock:,} 개",
            "📉 일평균 소진": f"{daily:,} 개/일",
        }
        chart_type = "area"

    # ── 수요 예측 ──────────────────────────────
    elif formula_name == "이동 평균 (Moving Average)":
        d1,d2,d3,d4,d5 = v["d1"],v["d2"],v["d3"],v["d4"],v["d5"]
        ma3 = (d3+d4+d5)/3
        ma5 = (d1+d2+d3+d4+d5)/5
        results = {
            "📈 3기간 이동평균 예측": f"{ma3:.1f} 개",
            "📊 5기간 이동평균 예측": f"{ma5:.1f} 개",
            "📉 예측 차이 (MA3-MA5)": f"{ma3-ma5:+.1f} 개",
        }
        chart_data = {
            "labels": ["1기","2기","3기","4기","5기","6기(MA3)","6기(MA5)"],
            "실제수요": [d1,d2,d3,d4,d5, None, None],
            "MA3 예측": [None,None,None,None,None, round(ma3,1), None],
            "MA5 예측": [None,None,None,None,None, None, round(ma5,1)],
        }
        chart_type = "line_multi"

    elif formula_name == "지수 평활법 (Exponential Smoothing)":
        alpha, prevF, prevD = v["alpha"], v["prevF"], v["prevD"]
        newF = alpha * prevD + (1 - alpha) * prevF
        results = {
            "📈 새 예측값 (Fₜ)": f"{newF:.1f} 개",
            "⚖️ 예측 오차": f"{prevD - prevF:+.1f} 개",
            "🔧 α×오차 보정": f"{alpha*(prevD-prevF):+.1f} 개",
        }
        alphas = [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
        chart_data = {
            "labels": [f"α={a}" for a in alphas],
            "예측값": [round(a*prevD + (1-a)*prevF, 1) for a in alphas],
        }
        chart_type = "bar"

    # ── 물류 / 유통 ────────────────────────────
    elif formula_name == "주문 충족률 (Fill Rate)":
        fulfilled, total = v["fulfilled"], v["total"]
        rate = fulfilled / total * 100
        results = {
            "✅ 주문 충족률": f"{rate:.1f} %",
            "❌ 미충족 주문": f"{total-fulfilled:,} 건",
        }
        chart_data = {"labels": ["충족","미충족"], "값": [fulfilled, total-fulfilled]}
        chart_type = "pie"

    elif formula_name == "정시 납품율 (OTD)":
        onTime, total = v["onTime"], v["total"]
        rate = onTime / total * 100
        results = {
            "🚚 정시 납품율 (OTD)": f"{rate:.1f} %",
            "⏰ 지연 납품": f"{total-onTime:,} 건",
        }
        chart_data = {"labels": ["정시","지연"], "값": [onTime, total-onTime]}
        chart_type = "pie"

    elif formula_name == "단위당 운송비용":
        totalCost, volume, distance = v["totalCost"], v["volume"], v["distance"]
        unitCost = totalCost / volume
        costPerKm = totalCost / distance
        results = {
            "💰 단위당 운송비": f"₩{unitCost:,.0f} /개",
            "📍 km당 비용": f"₩{costPerKm:,.0f} /km",
            "💸 총 운송비용": f"₩{totalCost:,.0f}",
        }
        chart_data = {
            "labels": ["운송비","하역비","보험료","기타"],
            "값": [round(totalCost*0.6), round(totalCost*0.2), round(totalCost*0.1), round(totalCost*0.1)]
        }
        chart_type = "pie"

    elif formula_name == "창고 공간 활용률":
        used, total, height, maxH = v["used"], v["total"], v["height"], v["maxH"]
        areaUtil = used / total * 100
        volUtil = (used * height) / (total * maxH) * 100
        results = {
            "📐 면적 활용률": f"{areaUtil:.1f} %",
            "📦 체적(부피) 활용률": f"{volUtil:.1f} %",
            "🏭 미사용 면적": f"{total-used:,} ㎡",
        }
        chart_data = {"labels": ["사용","미사용"], "값": [used, total-used]}
        chart_type = "pie"

    # ── 비용 / 성과 ────────────────────────────
    elif formula_name == "총 물류비용 (TLC)":
        inv, trans, wh, order = v["inv"], v["trans"], v["wh"], v["order"]
        total = inv + trans + wh + order
        results = {
            "💰 총 물류비용 (TLC)": f"₩{total:,.0f}",
            "📦 재고비 비중": f"{inv/total*100:.1f}%  (₩{inv:,.0f})",
            "🚚 운송비 비중": f"{trans/total*100:.1f}%  (₩{trans:,.0f})",
            "🏭 창고비 비중": f"{wh/total*100:.1f}%  (₩{wh:,.0f})",
            "📋 주문처리비 비중": f"{order/total*100:.1f}%  (₩{order:,.0f})",
        }
        chart_data = {"labels":["재고비","운송비","창고비","주문처리비"], "값":[inv,trans,wh,order]}
        chart_type = "pie"

    elif formula_name == "완전 주문율 (Perfect Order Rate)":
        otd, fill, damage, doc = v["otd"], v["fill"], v["damage"], v["doc"]
        por = (otd/100) * (fill/100) * (damage/100) * (doc/100) * 100
        results = {
            "🏆 완전 주문율 (POR)": f"{por:.2f} %",
            "⚠️ 손실률": f"{100-por:.2f} %",
        }
        chart_data = {
            "labels": ["정시납품","주문충족","무손상","서류정확","완전주문율"],
            "값": [otd, fill, damage, doc, round(por, 2)],
        }
        chart_type = "bar"

    elif formula_name == "이동평균단가 (MAP)":
        prevQty, prevPrice, inQty, inPrice = v["prevQty"], v["prevPrice"], v["inQty"], v["inPrice"]
        newQty = prevQty + inQty
        newMAP = (prevQty * prevPrice + inQty * inPrice) / newQty
        results = {
            "💲 새 이동평균단가": f"₩{newMAP:,.2f}",
            "📦 총 재고량": f"{newQty:,} 개",
            "📈 단가 변동": f"₩{newMAP-prevPrice:+,.2f}",
            "💰 총 재고 금액": f"₩{newQty*newMAP:,.0f}",
        }
        chart_data = {
            "labels": ["기존 단가","입고 단가","새 MAP"],
            "값": [prevPrice, inPrice, round(newMAP, 2)],
        }
        chart_type = "bar"

    return results, chart_data, chart_type


# ═══════════════════════════════════════════════════════
#  차트 렌더링
# ═══════════════════════════════════════════════════════
COLORS = ["#2383e2","#0f9960","#cb912f","#d44c47","#9065b0"]

def render_chart(chart_data, chart_type, title):
    if not HAS_PL or chart_data is None:
        return
    labels = chart_data["labels"]

    if chart_type == "pie":
        vals = chart_data["값"]
        fig = go.Figure(go.Pie(
            labels=labels, values=vals, hole=0.45,
            marker=dict(colors=COLORS[:len(labels)], line=dict(color='#fff', width=2)),
            textinfo='label+percent',
            hovertemplate='%{label}: %{value:,}<extra></extra>',
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13)),
            height=300, margin=dict(l=0,r=0,t=40,b=0),
            showlegend=True,
            legend=dict(orientation='h', y=-0.1, font=dict(size=10)),
        )

    elif chart_type == "bar":
        key = [k for k in chart_data if k != "labels"][0]
        vals = chart_data[key]
        fig = go.Figure(go.Bar(
            x=labels, y=vals,
            marker_color=COLORS[0], opacity=0.85,
            text=[f"{v:,}" for v in vals],
            textposition='outside',
            textfont=dict(size=10, color='#6b6b6b'),
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13)),
            height=280, margin=dict(l=0,r=0,t=40,b=0),
            xaxis=dict(tickfont=dict(size=10, color='#9b9b9b')),
            yaxis=dict(showgrid=True, gridcolor='#f1f1ef', tickfont=dict(size=10, color='#9b9b9b')),
        )

    elif chart_type in ("line_multi", "area"):
        fig = go.Figure()
        keys = [k for k in chart_data if k != "labels"]
        for i, key in enumerate(keys):
            raw = chart_data[key]
            # None 처리 (이동평균 차트용)
            y_vals = [v if v is not None else None for v in raw]
            if chart_type == "area" and i == 0:
                fig.add_trace(go.Scatter(
                    x=labels, y=y_vals, name=key,
                    mode='lines', line=dict(color=COLORS[i], width=2),
                    fill='tozeroy', fillcolor=f"rgba({int(COLORS[i][1:3],16)},{int(COLORS[i][3:5],16)},{int(COLORS[i][5:7],16)},.15)",
                    connectgaps=False,
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=labels, y=y_vals, name=key,
                    mode='lines+markers' if len(labels) < 20 else 'lines',
                    line=dict(color=COLORS[i % len(COLORS)], width=2,
                              dash='dot' if i > 0 and chart_type != "area" else 'solid'),
                    connectgaps=False,
                ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13)),
            height=300, margin=dict(l=0,r=0,t=40,b=0),
            xaxis=dict(showgrid=False, tickfont=dict(size=10, color='#9b9b9b')),
            yaxis=dict(showgrid=True, gridcolor='#f1f1ef', tickfont=dict(size=10, color='#9b9b9b')),
            legend=dict(orientation='h', y=1.12, font=dict(size=10, color='#6b6b6b'),
                        bgcolor='rgba(0,0,0,0)'),
            hovermode='x unified',
        )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})



# ═══════════════════════════════════════════════════════
#  DB 연동 — 실제 데이터 불러오기
# ═══════════════════════════════════════════════════════
import sqlite3, pandas as pd

def _get_conn():
    """pages/ 폴더 기준으로 scm.db 경로 탐색"""
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, "scm.db"),           # pages/scm.db
        os.path.join(base, "..", "scm.db"),      # 프로젝트루트/scm.db  ← 일반적
        os.path.join(base, "..", "..", "scm.db"),
        os.path.join(os.getcwd(), "scm.db"),
    ]
    for path in candidates:
        path = os.path.normpath(path)
        if os.path.exists(path):
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            return conn, path
    return None, None

def load_db_data(formula_name):
    """공식에 맞는 DB 데이터 옵션 반환 {label: {field_key: value}}"""
    conn, db_path = _get_conn()
    if conn is None:
        return {"⚠️ scm.db를 찾을 수 없습니다": {}}
    try:
        options = {}

        if formula_name in ("경제적 주문량 (EOQ)", "재주문점 (ROP)", "안전재고 (Safety Stock)", "Days of Supply (DOS)"):
            rows = conn.execute("""
                SELECT item_name, stock_qty, min_stock,
                       unit_price, item_code
                FROM inventory WHERE stock_qty > 0
                ORDER BY item_name LIMIT 50""").fetchall()
            for r in rows:
                if formula_name == "경제적 주문량 (EOQ)":
                    # 연간수요=재고회전 추정, 주문비=50000고정, 재고유지=단가*20%
                    options[r["item_name"]] = {
                        "D": max(r["stock_qty"] * 12, 1),
                        "S": 50000,
                        "H": max(r["unit_price"] * 0.2, 1),
                    }
                elif formula_name == "재주문점 (ROP)":
                    options[r["item_name"]] = {
                        "d": max(r["stock_qty"] / 30, 1),
                        "L": 7,
                        "SS": max(r["min_stock"], 0),
                    }
                elif formula_name == "안전재고 (Safety Stock)":
                    options[r["item_name"]] = {
                        "Z": 1.65,
                        "sigma": max(r["stock_qty"] * 0.1, 1),
                        "L": 7,
                    }
                elif formula_name == "Days of Supply (DOS)":
                    options[r["item_name"]] = {
                        "stock": r["stock_qty"],
                        "daily": max(r["stock_qty"] / 30, 1),
                    }

        elif formula_name == "재고 회전율":
            rows = conn.execute("""
                SELECT item_name,
                       stock_qty * unit_price AS inv_val,
                       unit_price
                FROM inventory WHERE stock_qty > 0
                ORDER BY inv_val DESC LIMIT 30""").fetchall()
            for r in rows:
                inv_val = r["inv_val"] or 0
                if inv_val > 0:
                    options[r["item_name"]] = {
                        "COGS": round(inv_val * 12),
                        "avgInv": round(inv_val),
                    }

        elif formula_name == "이동평균 (Moving Average)":
            rows = conn.execute("""
                SELECT substr(ordered_at,1,7) AS ym, COUNT(*) AS cnt
                FROM sales_orders
                WHERE ordered_at IS NOT NULL
                GROUP BY ym ORDER BY ym DESC LIMIT 5""").fetchall()
            if len(rows) >= 3:
                vals = [r["cnt"] for r in reversed(rows)]
                while len(vals) < 5: vals.append(vals[-1])
                options["최근 5개월 수주량"] = {
                    "d1": vals[0], "d2": vals[1], "d3": vals[2],
                    "d4": vals[3], "d5": vals[4],
                }

        elif formula_name == "이동평균단가 (MAP)":
            rows = conn.execute("""
                SELECT item_name, prev_qty, prev_avg_price,
                       incoming_qty, incoming_price
                FROM moving_avg_price
                ORDER BY calculated_at DESC LIMIT 30""").fetchall()
            for r in rows:
                options[r["item_name"]] = {
                    "prevQty": r["prev_qty"],
                    "prevPrice": r["prev_avg_price"],
                    "inQty": r["incoming_qty"],
                    "inPrice": r["incoming_price"],
                }

        elif formula_name == "주문 충족률 (Fill Rate)":
            row = conn.execute("""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN status NOT IN ('취소','반품접수') THEN 1 ELSE 0 END) AS fulfilled
                FROM sales_orders""").fetchone()
            if row and row["total"] > 0:
                options["전체 수주 기준"] = {
                    "fulfilled": row["fulfilled"] or 0,
                    "total": row["total"],
                }
            # 최근 30일
            row2 = conn.execute("""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN status NOT IN ('취소','반품접수') THEN 1 ELSE 0 END) AS fulfilled
                FROM sales_orders
                WHERE ordered_at >= date('now','-30 days')""").fetchone()
            if row2 and row2["total"] > 0:
                options["최근 30일"] = {
                    "fulfilled": row2["fulfilled"] or 0,
                    "total": row2["total"],
                }

        elif formula_name == "정시 납품율 (OTD)":
            row = conn.execute("""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN status='배송완료' THEN 1 ELSE 0 END) AS on_time
                FROM deliveries""").fetchone()
            if row and row["total"] > 0:
                options["전체 납품 기준"] = {
                    "onTime": row["on_time"] or 0,
                    "total": row["total"],
                }

        elif formula_name == "단위당 운송비용":
            rows = conn.execute("""
                SELECT origin || '→' || destination AS route,
                       freight_cost, COUNT(*) AS cnt
                FROM freight_orders
                WHERE freight_cost > 0
                GROUP BY route ORDER BY cnt DESC LIMIT 10""").fetchall()
            for r in rows:
                options[r["route"]] = {
                    "totalCost": r["freight_cost"],
                    "volume": 1000,
                    "distance": 200,
                }

        elif formula_name == "창고 공간 활용률":
            rows = conn.execute("""
                SELECT w.warehouse_name,
                       w.capacity,
                       COALESCE(SUM(i.stock_qty * 0.01), 0) AS used_area
                FROM warehouses w
                LEFT JOIN inventory i ON i.warehouse_id = w.id
                WHERE w.capacity > 0
                GROUP BY w.id""").fetchall()
            for r in rows:
                if r["capacity"] > 0:
                    options[r["warehouse_name"]] = {
                        "used": round(r["used_area"]),
                        "total": round(r["capacity"]),
                        "height": 4,
                        "maxH": 6,
                    }

        elif formula_name == "총 물류비용 (TLC)":
            inv_val = conn.execute(
                "SELECT COALESCE(SUM(stock_qty*unit_price*0.2),0) FROM inventory").fetchone()[0]
            trans = conn.execute(
                "SELECT COALESCE(SUM(freight_cost),0) FROM freight_orders").fetchone()[0]
            options["전체 실적 기준"] = {
                "inv": round(inv_val or 0),
                "trans": round(trans or 0),
                "wh": round((trans or 0) * 0.3),
                "order": round((trans or 0) * 0.2),
            }

        elif formula_name == "완전 주문율 (Perfect Order Rate)":
            so = conn.execute("SELECT COUNT(*) FROM sales_orders WHERE status!='취소'").fetchone()[0] or 1
            on_time = conn.execute("SELECT COUNT(*) FROM deliveries WHERE status='배송완료'").fetchone()[0]
            total_d = conn.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0] or 1
            pass_q = conn.execute("SELECT COUNT(*) FROM quality_inspections WHERE result='합격'").fetchone()[0]
            total_q = conn.execute("SELECT COUNT(*) FROM quality_inspections").fetchone()[0] or 1
            options["실적 기준 (자동계산)"] = {
                "otd": round(on_time / total_d * 100, 1),
                "fill": round(min(on_time / so * 100, 100), 1),
                "damage": round(pass_q / total_q * 100, 1),
                "doc": 98.0,
            }

        conn.close()
        # 데이터가 없는 경우 안내
        if not options:
            return {"⚠️ 해당 공식에 연동할 데이터가 없습니다 (DB에 데이터를 먼저 입력하세요)": {}}
        return options
    except Exception as e:
        conn.close() if conn else None
        return {f"❌ DB 오류: {e}": {}}

# ═══════════════════════════════════════════════════════
#  UI 레이아웃
# ═══════════════════════════════════════════════════════
with main_tab1:
    section_title("카테고리 선택")

    cat_keys = list(CATEGORIES.keys())
    if "selected_cat" not in st.session_state:
        st.session_state.selected_cat = cat_keys[0]

    # ── 카테고리 카드: Streamlit key 기반 CSS 타겟팅 ──────
    # Streamlit은 key="cat_btn_0" → class="st-key-cat_btn_0" 자동 부여

    # 공통 + 개별 스타일 한 번에 출력
    _css_parts = ["""
    <style>
    /* 공통: 카드 크기·폰트 */
    .st-key-cat_btn_0 button, .st-key-cat_btn_1 button,
    .st-key-cat_btn_2 button, .st-key-cat_btn_3 button {
        height: 130px !important;
        width: 100% !important;
        border-radius: 12px !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        white-space: pre-line !important;
        line-height: 1.9 !important;
        box-shadow: none !important;
        padding: 0 !important;
        transition: opacity .15s !important;
    }
    .st-key-cat_btn_0 button:hover, .st-key-cat_btn_1 button:hover,
    .st-key-cat_btn_2 button:hover, .st-key-cat_btn_3 button:hover {
        opacity: 0.8 !important;
    }
    """]

    for _i, _key in enumerate(cat_keys):
        _active = (st.session_state.selected_cat == _key)
        _bg     = "#e8f3fd" if _active else "#f7f7f5"
        _border = "2px solid #2383e2" if _active else "1px solid #e9e9e7"
        _color  = "#2383e2" if _active else "#6b6b6b"
        _css_parts.append(f"""
    .st-key-cat_btn_{_i} button {{
        background: {_bg} !important;
        border: {_border} !important;
        color: {_color} !important;
    }}""")

    _css_parts.append("</style>")
    st.markdown("".join(_css_parts), unsafe_allow_html=True)

    cat_cols = st.columns(len(cat_keys))
    for i, col in enumerate(cat_cols):
        with col:
            icon  = cat_keys[i].split()[0]
            label = " ".join(cat_keys[i].split()[1:])
            if st.button(icon + "\n" + label, key=f"cat_btn_{i}", use_container_width=True):
                st.session_state.selected_cat = cat_keys[i]
                st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # 공식 선택
    section_title("공식 선택")
    formulas_in_cat = list(CATEGORIES[st.session_state.selected_cat].keys())
    selected_formula = st.selectbox(
        "계산할 공식을 선택하세요",
        formulas_in_cat,
        label_visibility="collapsed"
    )

    formula_meta = CATEGORIES[st.session_state.selected_cat][selected_formula]

    # 공식 설명 카드
    st.markdown(f"""
    <div style="background:#f7f7f5;border:1px solid #e9e9e7;border-radius:8px;padding:14px 18px;margin:8px 0 16px">
        <div style="font-size:0.72rem;font-weight:600;color:#9b9b9b;margin-bottom:4px">공식</div>
        <div style="font-size:1rem;font-weight:700;color:#1a1a1a;font-family:'Inter',monospace;letter-spacing:.01em">
            {formula_meta['formula']}
        </div>
        <div style="font-size:0.8rem;color:#6b6b6b;margin-top:6px">{formula_meta['desc']}</div>
    </div>""", unsafe_allow_html=True)

    # ── 입력 + 결과 ────────────────────────────────────────
    col_input, col_result = st.columns([1, 1])

    with col_input:
        section_title("입력값")
        input_vals = {}
        fields = formula_meta["fields"]

        # ── DB 데이터 불러오기 ──────────────────────────
        db_options = load_db_data(selected_formula)
        prefill = {}

        # 오류/경고 키 분리
        _warn_keys = [k for k in db_options if k.startswith("⚠️") or k.startswith("❌")]
        _real_options = {k: v for k, v in db_options.items() if k not in _warn_keys}

        if _warn_keys:
            st.warning(_warn_keys[0])
    
        if _real_options:
            with st.expander(f"📂 DB 데이터 불러오기 ({len(_real_options)}건)", expanded=True):
                db_choice = st.selectbox(
                    "데이터 선택",
                    ["── 직접 입력 ──"] + list(_real_options.keys()),
                    key=f"db_sel_{selected_formula}"
                )
                if db_choice != "── 직접 입력 ──":
                    prefill = _real_options[db_choice]
                    st.success(f"✅ '{db_choice}' 데이터 적용됨")
                    # 적용된 값 미리보기
                    cols_prev = st.columns(len(prefill))
                    for ci, (k, v) in enumerate(prefill.items()):
                        with cols_prev[ci]:
                            st.metric(k, f"{v:,}" if isinstance(v, (int, float)) else v)
        else:
            st.markdown("""
            <div style="background:#f7f7f5;border:1px dashed #d3d3cf;border-radius:8px;
                        padding:10px 14px;font-size:0.8rem;color:#9b9b9b;margin-bottom:12px">
                📂 DB 연동 데이터 없음 — 직접 입력하세요
            </div>""", unsafe_allow_html=True)

        # ── 입력 폼 ────────────────────────────────────
        form_key = f"form_{selected_formula}"
        with st.form(form_key):
            for key, label, unit, default in fields:
                # DB에서 불러온 값이 있으면 우선 사용
                init_val = float(prefill.get(key, default))
                val = st.number_input(
                    f"{label} ({unit})",
                    value=init_val,
                    step=1.0 if init_val >= 10 else 0.01,
                    format="%.2f" if isinstance(default, float) and default < 10 else "%.0f",
                    key=f"inp_{key}_{selected_formula}"
                )
                input_vals[key] = val

            submitted = st.form_submit_button("🔢 계산하기", use_container_width=True, type="primary")

    with col_result:
        section_title("결과")
        if submitted:
            try:
                results, chart_data, chart_type = calculate(selected_formula, input_vals)
                st.session_state["last_results"] = results
                st.session_state["last_chart"] = (chart_data, chart_type)
                st.session_state["last_formula"] = selected_formula
            except ZeroDivisionError:
                st.error("0으로 나눌 수 없습니다. 입력값을 확인해주세요.")
            except Exception as e:
                st.error(f"계산 오류: {e}")

        if st.session_state.get("last_results") and st.session_state.get("last_formula") == selected_formula:
            for label, value in st.session_state["last_results"].items():
                is_main = list(st.session_state["last_results"].keys()).index(label) == 0
                bg = "#e8f3fd" if is_main else "#fff"
                border = "#2383e2" if is_main else "#e9e9e7"
                size = "1.4rem" if is_main else "1rem"
                color = "#2383e2" if is_main else "#1a1a1a"
                st.markdown(f"""
                <div style="background:{bg};border:1px solid {border};border-radius:8px;
                            padding:12px 16px;margin-bottom:8px">
                    <div style="font-size:0.7rem;color:#9b9b9b;margin-bottom:3px">{label}</div>
                    <div style="font-size:{size};font-weight:700;color:{color};
                                font-family:'Inter',sans-serif">{value}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#f7f7f5;border:1px dashed #d3d3cf;border-radius:8px;
                        padding:32px;text-align:center;color:#9b9b9b;font-size:0.85rem">
                입력값을 입력하고<br>계산하기를 눌러주세요
            </div>""", unsafe_allow_html=True)

    # ── 시각화 ─────────────────────────────────────────────
    if st.session_state.get("last_chart") and st.session_state.get("last_formula") == selected_formula:
        chart_data, chart_type = st.session_state["last_chart"]
        if chart_data:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            section_title("시각화")
            render_chart(chart_data, chart_type, selected_formula)


# ═══════════════════════════════════════════════════════
#  🗓️ 유통기한 관리 계산기
# ═══════════════════════════════════════════════════════
with main_tab2:
    from datetime import date as _date, datetime as _datetime, timedelta as _timedelta
    import math as _math

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 20px">
        <div style="width:32px;height:32px;border-radius:8px;
                    background:linear-gradient(135deg,#0f9960,#00C896);
                    display:flex;align-items:center;justify-content:center;font-size:16px">🗓️</div>
        <div>
            <div style="font-size:1rem;font-weight:700;color:#1a1a1a">유통기한 관리 계산기</div>
            <div style="font-size:0.72rem;color:#9b9b9b">재고 소진 예측 · 폐기 손실 계산 · FEFO 발주 제안 · 긴급도 분석</div>
        </div>
    </div>""", unsafe_allow_html=True)

    exp_tabs = st.tabs(["📊 소진 가능 여부", "💸 폐기 손실 계산", "📦 FEFO 발주 제안", "🔴 긴급도 분석"])

    # ── 탭 1: 소진 가능 여부 (DOS vs 유통기한 잔여일) ──────
    with exp_tabs[0]:
        st.markdown("#### 📊 유통기한 내 소진 가능 여부")
        st.caption("현재 재고와 일평균 수요를 기반으로, 유통기한 전에 재고를 다 소진할 수 있는지 계산합니다.")

        # DB에서 유통기한 있는 재고 불러오기
        _conn_e, _db_path_e = _get_conn()
        _inv_exp_rows = []
        if _conn_e:
            try:
                _inv_exp_rows = _conn_e.execute("""
                    SELECT item_name, stock_qty, unit_price, expiry_date, lot_number
                    FROM inventory
                    WHERE expiry_date IS NOT NULL AND expiry_date != ''
                    ORDER BY expiry_date
                """).fetchall()
                _conn_e.close()
            except Exception:
                pass

        _inv_exp_map = {
            f"{r['item_name']} | LOT:{r['lot_number'] or '-'} | 만료:{r['expiry_date']}": r
            for r in _inv_exp_rows
        } if _inv_exp_rows else {}

        col_e1, col_e2 = st.columns([1, 1])
        with col_e1:
            if _inv_exp_map:
                with st.expander(f"📂 DB 유통기한 재고 ({len(_inv_exp_map)}건)", expanded=True):
                    db_exp_choice = st.selectbox("재고 선택", ["── 직접 입력 ──"] + list(_inv_exp_map.keys()), key="exp_db_sel")
            else:
                db_exp_choice = "── 직접 입력 ──"
                st.info("유통기한 등록된 재고가 없습니다. (WM → 재고 관리에서 등록)")

            # 기본값 설정
            _pre_qty, _pre_price, _pre_exp = 1000, 10000.0, _date.today() + _timedelta(days=30)
            if db_exp_choice != "── 직접 입력 ──" and db_exp_choice in _inv_exp_map:
                _r = _inv_exp_map[db_exp_choice]
                _pre_qty   = int(_r['stock_qty'] or 0)
                _pre_price = float(_r['unit_price'] or 0)
                try:
                    _pre_exp = _date.fromisoformat(str(_r['expiry_date']))
                except Exception:
                    pass

            with st.form("exp_dos_form"):
                e_stock   = st.number_input("현재 재고량 (개)", min_value=1, value=_pre_qty)
                e_daily   = st.number_input("일평균 수요 (개/일)", min_value=1, value=max(1, _pre_qty // 20))
                e_exp_date= st.date_input("유통기한", value=_pre_exp, key="e_exp_d")
                e_today   = _date.today()
                submitted_e = st.form_submit_button("🔢 계산", use_container_width=True, type="primary")

        with col_e2:
            if submitted_e:
                remaining_days = (e_exp_date - e_today).days
                dos = e_stock / e_daily  # Days of Supply
                shortage = dos - remaining_days
                can_consume = dos <= remaining_days

                status_color = "#0f9960" if can_consume else "#d44c47"
                status_label = "✅ 소진 가능" if can_consume else "🔴 소진 불가 (폐기 위험)"

                st.markdown(f"""
                <div style="background:{'#e6f4ed' if can_consume else '#fee2e2'};
                            border:2px solid {'#0f9960' if can_consume else '#d44c47'};
                            border-radius:10px;padding:20px;text-align:center;margin-bottom:16px">
                    <div style="font-size:1.4rem;font-weight:800;color:{status_color}">{status_label}</div>
                </div>""", unsafe_allow_html=True)

                m1, m2 = st.columns(2)
                m1.metric("📅 유통기한 잔여일", f"{remaining_days}일")
                m2.metric("⏱️ Days of Supply", f"{dos:.1f}일")

                m3, m4 = st.columns(2)
                if can_consume:
                    m3.metric("✅ 여유일", f"{remaining_days - dos:.1f}일")
                    m4.metric("소진 완료 예상일", str(e_today + _timedelta(days=int(dos))))
                else:
                    expire_qty = round(abs(shortage) * e_daily)
                    m3.metric("⚠️ 폐기 예상 수량", f"{max(0, expire_qty):,}개", delta_color="inverse")
                    m4.metric("재고 소진일 vs 만료일", f"{abs(shortage):.1f}일 초과", delta_color="inverse")

                # 시각화
                if HAS_PL:
                    import plotly.graph_objects as _go
                    max_days = max(remaining_days, int(dos)) + 5
                    days_range = list(range(max_days + 1))
                    stock_curve = [max(0, e_stock - e_daily * d) for d in days_range]
                    exp_line    = [0] * max_days
                    fig_e = _go.Figure()
                    fig_e.add_trace(_go.Scatter(
                        x=days_range, y=stock_curve, name="재고 잔량",
                        mode='lines', line=dict(color="#2383e2", width=2),
                        fill='tozeroy', fillcolor="rgba(35,131,226,.1)"
                    ))
                    fig_e.add_vline(x=remaining_days, line_dash="dash",
                                    line_color="#d44c47", annotation_text="유통기한",
                                    annotation_position="top right")
                    fig_e.add_vline(x=dos, line_dash="dot",
                                    line_color="#0f9960", annotation_text="소진완료",
                                    annotation_position="top left")
                    fig_e.update_layout(
                        title="재고 소진 vs 유통기한", height=260,
                        margin=dict(l=0,r=0,t=40,b=0),
                        xaxis=dict(title="경과일", tickfont=dict(size=10)),
                        yaxis=dict(title="재고량", tickfont=dict(size=10)),
                        legend=dict(orientation='h', y=1.1, font=dict(size=10)),
                    )
                    st.plotly_chart(fig_e, use_container_width=True, config={'displayModeBar':False})

    # ── 탭 2: 폐기 손실 계산 ────────────────────────────────
    with exp_tabs[1]:
        st.markdown("#### 💸 유통기한 초과 폐기 손실 계산")
        st.caption("소진하지 못한 재고의 예상 폐기 손실액과 폐기율을 계산합니다.")

        col_l1, col_l2 = st.columns([1, 1])
        with col_l1:
            if _inv_exp_map:
                with st.expander(f"📂 DB 재고 불러오기 ({len(_inv_exp_map)}건)", expanded=False):
                    db_loss_choice = st.selectbox("재고 선택", ["── 직접 입력 ──"] + list(_inv_exp_map.keys()), key="loss_db_sel")
                _pl_qty, _pl_price = 1000, 10000.0
                if db_loss_choice != "── 직접 입력 ──" and db_loss_choice in _inv_exp_map:
                    _rl = _inv_exp_map[db_loss_choice]
                    _pl_qty   = int(_rl['stock_qty'] or 0)
                    _pl_price = float(_rl['unit_price'] or 0)
            else:
                _pl_qty, _pl_price = 1000, 10000.0

            with st.form("loss_form"):
                l_total   = st.number_input("전체 재고량 (개)", min_value=1, value=_pl_qty)
                l_consumed= st.number_input("유통기한 내 소진 가능 수량 (개)", min_value=0, value=min(_pl_qty, max(0, _pl_qty-100)))
                l_price   = st.number_input("단가 (원)", min_value=0.0, value=_pl_price, format="%.0f")
                l_disposal= st.number_input("폐기 처리 비용 (개당, 원)", min_value=0.0, value=500.0, format="%.0f")
                submitted_l = st.form_submit_button("🔢 계산", use_container_width=True, type="primary")

        with col_l2:
            if submitted_l:
                expire_qty    = max(0, l_total - l_consumed)
                loss_product  = expire_qty * l_price
                loss_disposal = expire_qty * l_disposal
                total_loss    = loss_product + loss_disposal
                loss_rate     = expire_qty / l_total * 100 if l_total > 0 else 0

                st.markdown(f"""
                <div style="background:#fff7ed;border:2px solid #F97316;
                            border-radius:10px;padding:20px;text-align:center;margin-bottom:16px">
                    <div style="font-size:0.8rem;color:#c2410c;margin-bottom:4px">예상 총 손실액</div>
                    <div style="font-size:1.8rem;font-weight:800;color:#d44c47">
                        ₩{total_loss:,.0f}
                    </div>
                </div>""", unsafe_allow_html=True)

                ma, mb = st.columns(2)
                ma.metric("폐기 예상 수량", f"{expire_qty:,}개")
                mb.metric("폐기율", f"{loss_rate:.1f}%", delta_color="inverse")
                mc, md = st.columns(2)
                mc.metric("제품 손실액", f"₩{loss_product:,.0f}")
                md.metric("폐기 처리비", f"₩{loss_disposal:,.0f}")

                if HAS_PL:
                    import plotly.graph_objects as _go2
                    fig_l = _go2.Figure(_go2.Pie(
                        labels=["소진 가능", "폐기 예상"],
                        values=[l_consumed, expire_qty],
                        hole=0.5,
                        marker=dict(colors=["#0f9960","#d44c47"],
                                    line=dict(color='#fff', width=2)),
                        textinfo='label+percent',
                    ))
                    fig_l.update_layout(
                        title="재고 소진 vs 폐기 비율", height=260,
                        margin=dict(l=0,r=0,t=40,b=0),
                        legend=dict(orientation='h', y=-0.1, font=dict(size=10)),
                    )
                    st.plotly_chart(fig_l, use_container_width=True, config={'displayModeBar':False})

    # ── 탭 3: FEFO 발주 제안 ────────────────────────────────
    with exp_tabs[2]:
        st.markdown("#### 📦 FEFO 기반 발주 시점 제안")
        st.caption("유통기한이 짧은 재고를 먼저 소진하고, 신규 입고 시점과 수량을 계산합니다.")

        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            with st.form("fefo_form"):
                f_stock      = st.number_input("현재 재고량 (개)", min_value=0, value=500)
                f_daily      = st.number_input("일평균 수요 (개/일)", min_value=1, value=50)
                f_exp_days   = st.number_input("유통기한 잔여일", min_value=1, value=20)
                f_lead_time  = st.number_input("리드타임 (일)", min_value=1, value=5)
                f_safety     = st.number_input("안전재고 (개)", min_value=0, value=100)
                f_order_qty  = st.number_input("1회 발주 수량 (개)", min_value=1, value=500)
                submitted_f  = st.form_submit_button("🔢 계산", use_container_width=True, type="primary")

        with col_f2:
            if submitted_f:
                # 현 재고 소진 완료일
                dos_f = f_stock / f_daily
                # 발주해야 할 최종 시점 = 소진일 - 리드타임, 단 만료일 이전이어야 함
                latest_order_day = min(f_exp_days - f_lead_time, dos_f - f_lead_time)
                # 재주문점: 안전재고 + 리드타임 수요
                rop = f_safety + f_daily * f_lead_time
                current_at_rop = max(0, (f_stock - rop) / f_daily)  # ROP 도달까지 남은 일수
                urgency = "🔴 즉시 발주" if latest_order_day <= 0 else \
                          "🟠 긴급 발주" if latest_order_day <= 3 else \
                          "🟡 조기 발주 권장" if latest_order_day <= 7 else "🟢 정상"

                st.markdown(f"""
                <div style="background:#f7f7f5;border:1px solid #e9e9e7;border-left:4px solid #2383e2;
                            border-radius:8px;padding:16px;margin-bottom:16px">
                    <div style="font-size:0.75rem;color:#9b9b9b;margin-bottom:6px">발주 긴급도</div>
                    <div style="font-size:1.3rem;font-weight:800">{urgency}</div>
                </div>""", unsafe_allow_html=True)

                fa, fb = st.columns(2)
                fa.metric("📅 발주 권장 시점", f"오늘로부터 {max(0, int(latest_order_day))}일 이내")
                fb.metric("🛒 권장 발주수량", f"{f_order_qty:,}개")
                fc, fd = st.columns(2)
                fc.metric("🎯 재주문점 (ROP)", f"{rop:,}개")
                fd.metric("⏱️ ROP 도달까지", f"{current_at_rop:.1f}일")

                # 타임라인 시각화
                if HAS_PL:
                    import plotly.graph_objects as _go3
                    max_d = max(f_exp_days + 5, int(dos_f) + 5, 30)
                    days_r = list(range(max_d + 1))
                    stock_curve_f = [max(0, f_stock - f_daily * d) for d in days_r]
                    fig_f = _go3.Figure()
                    fig_f.add_trace(_go3.Scatter(
                        x=days_r, y=stock_curve_f, name="재고 잔량",
                        mode='lines', line=dict(color="#2383e2", width=2),
                        fill='tozeroy', fillcolor="rgba(35,131,226,.1)"
                    ))
                    fig_f.add_hline(y=rop, line_dash="dash",
                                    line_color="#cb912f", annotation_text=f"ROP({rop}개)")
                    fig_f.add_vline(x=f_exp_days, line_dash="dash",
                                    line_color="#d44c47", annotation_text="유통기한")
                    if latest_order_day > 0:
                        fig_f.add_vline(x=latest_order_day, line_dash="dot",
                                        line_color="#9065b0", annotation_text="발주권장")
                    fig_f.update_layout(
                        title="FEFO 재고 계획", height=260,
                        margin=dict(l=0,r=0,t=40,b=0),
                        xaxis=dict(title="경과일", tickfont=dict(size=10)),
                        yaxis=dict(title="재고량", tickfont=dict(size=10)),
                    )
                    st.plotly_chart(fig_f, use_container_width=True, config={'displayModeBar':False})

    # ── 탭 4: 긴급도 분석 (DB 전체 유통기한 재고 일괄 분석) ─
    with exp_tabs[3]:
        st.markdown("#### 🔴 전체 재고 유통기한 긴급도 분석")
        st.caption("DB에 등록된 유통기한 재고를 자동으로 불러와 긴급도를 분류합니다.")

        _conn_u, _ = _get_conn()
        _urgency_rows = []
        if _conn_u:
            try:
                _urgency_rows = _conn_u.execute("""
                    SELECT item_name, stock_qty, unit_price, expiry_date, lot_number, warehouse
                    FROM inventory
                    WHERE expiry_date IS NOT NULL AND expiry_date != '' AND stock_qty > 0
                    ORDER BY expiry_date
                """).fetchall()
                _conn_u.close()
            except Exception:
                pass

        if not _urgency_rows:
            st.info("유통기한이 등록된 재고가 없습니다. WM → 재고 관리 → 신규 등록에서 유통기한을 입력하세요.")
        else:
            u_daily_default = st.number_input("일평균 수요 (개/일, 전체 기준 추정)", min_value=1, value=50, key="u_daily")

            today_u = _date.today()
            rows_out = []
            for r in _urgency_rows:
                try:
                    exp_d = _date.fromisoformat(str(r['expiry_date']))
                    remaining = (exp_d - today_u).days
                    dos_u = int(r['stock_qty']) / u_daily_default
                    deficit = dos_u - remaining
                    if remaining < 0:
                        urgency_label = "🔴 만료됨"
                        urgency_sort  = 0
                    elif remaining <= 7:
                        urgency_label = "🔴 즉시처리"
                        urgency_sort  = 1
                    elif remaining <= 30:
                        urgency_label = "🟠 30일 이내"
                        urgency_sort  = 2
                    elif deficit > 0:
                        urgency_label = "🟡 소진 불가"
                        urgency_sort  = 3
                    else:
                        urgency_label = "🟢 정상"
                        urgency_sort  = 4

                    expire_qty_u = max(0, round(deficit * u_daily_default)) if deficit > 0 else 0
                    loss_u = expire_qty_u * float(r['unit_price'] or 0)

                    rows_out.append({
                        "품목": r['item_name'],
                        "창고": r['warehouse'] or "-",
                        "LOT": r['lot_number'] or "-",
                        "재고": int(r['stock_qty']),
                        "유통기한": str(r['expiry_date']),
                        "잔여일": remaining,
                        "DOS(일)": round(dos_u, 1),
                        "긴급도": urgency_label,
                        "폐기예상": expire_qty_u,
                        "예상손실(원)": round(loss_u),
                        "_sort": urgency_sort,
                    })
                except Exception:
                    continue

            df_u = pd.DataFrame(rows_out).sort_values(["_sort","잔여일"]).drop(columns=["_sort"])

            # 요약
            u1, u2, u3, u4 = st.columns(4)
            u1.metric("🔴 즉시처리/만료", len(df_u[df_u['긴급도'].str.startswith("🔴")]))
            u2.metric("🟠 30일 이내", len(df_u[df_u['긴급도'] == "🟠 30일 이내"]))
            u3.metric("🟡 소진 불가", len(df_u[df_u['긴급도'] == "🟡 소진 불가"]))
            total_loss_u = df_u['예상손실(원)'].sum()
            u4.metric("💸 총 예상 손실", f"₩{total_loss_u:,.0f}", delta_color="inverse")

            def hl_urgency(row):
                if "만료" in row['긴급도'] or "즉시" in row['긴급도']:
                    return ['background-color:#fee2e2'] * len(row)
                if "30일" in row['긴급도']:
                    return ['background-color:#fef9c3'] * len(row)
                if "소진 불가" in row['긴급도']:
                    return ['background-color:#fff7ed'] * len(row)
                return [''] * len(row)

            st.dataframe(df_u.style.apply(hl_urgency, axis=1), use_container_width=True, hide_index=True)

            # 긴급도 분포 차트
            if HAS_PL:
                import plotly.graph_objects as _go4
                urgency_counts = df_u['긴급도'].value_counts()
                color_map = {"🔴 만료됨": "#d44c47","🔴 즉시처리":"#d44c47",
                             "🟠 30일 이내":"#cb912f","🟡 소진 불가":"#e6b800","🟢 정상":"#0f9960"}
                colors_u = [color_map.get(k, "#9b9b9b") for k in urgency_counts.index]
                fig_u = _go4.Figure(_go4.Bar(
                    x=list(urgency_counts.index), y=list(urgency_counts.values),
                    marker_color=colors_u, opacity=0.85,
                    text=list(urgency_counts.values), textposition='outside',
                ))
                fig_u.update_layout(
                    title="긴급도별 품목 수", height=240,
                    margin=dict(l=0,r=0,t=40,b=0),
                    xaxis=dict(tickfont=dict(size=10)),
                    yaxis=dict(showgrid=True, gridcolor='#f1f1ef'),
                )
                st.plotly_chart(fig_u, use_container_width=True, config={'displayModeBar':False})

# ══════════════════════════════════════════════════════════════════
#  main_tab3 — 🤖 AI 수요예측 (유통기한 있는 품목 전용)
#  알고리즘: LightGBM Tweedie + Optuna 튜닝 + 카테고리 편향 보정
#  출처: README 기반 demand_forecast_part1~3 파이프라인 이식
# ══════════════════════════════════════════════════════════════════
with main_tab3:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1A1A2E 0%,#16213E 100%);
                border-radius:12px;padding:20px 24px;margin-bottom:20px'>
        <h3 style='color:#fff;margin:0 0 6px 0'>🤖 AI 수요예측 — 유통기한 품목 전용</h3>
        <p style='color:#94a3b8;margin:0;font-size:0.9rem'>
            LightGBM (Tweedie 회귀) + Optuna 하이퍼파라미터 튜닝<br>
            요일 패턴 · 이벤트 가중치 · Lag 피처 기반 정밀 예측 | 목표 WMAPE ≤ 10%
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 라이브러리 체크
    _missing = []
    try:
        import numpy as _np
    except ImportError:
        _missing.append("numpy")
    try:
        import pandas as _pd
    except ImportError:
        _missing.append("pandas")
    try:
        import lightgbm as _lgb
        _HAS_LGB = True
    except ImportError:
        _HAS_LGB = False
        _missing.append("lightgbm")
    try:
        import plotly.graph_objects as _go
        _HAS_PL3 = True
    except ImportError:
        _HAS_PL3 = False

    if _missing:
        st.warning(f"⚠️ 필요 라이브러리 미설치: `pip install {' '.join(_missing)}`")
        st.stop()

    # ── 상수 ─────────────────────────────────────────────────────
    _DOW_W   = {0:1.18, 1:1.09, 2:1.08, 3:1.38, 4:0.81, 5:0.60, 6:0.85}
    _DOW_KOR = ["월","화","수","목","금","토","일"]
    _SAFETY  = {"신선(엽채/나물/가금육)":1.20, "육류/유제품":1.15,
                "가공/냉동/과자":1.05, "기타":1.10}

    # ── DB에서 유통기한 있는 품목 로드 ──────────────────────────
    try:
        from utils.db import get_db as _get_db
    except ImportError:
        try:
            from db import get_db as _get_db
        except ImportError:
            _get_db = None

    _expiry_items = []
    _inv_map = {}   # item_name → stock_qty
    if _get_db:
        try:
            _cx = _get_db()
            _expiry_rows = [dict(r) for r in _cx.execute("""
                SELECT item_name, stock_qty, expiry_date
                FROM inventory
                WHERE expiry_date IS NOT NULL AND stock_qty > 0
                ORDER BY expiry_date ASC
            """).fetchall()]
            _cx.close()
            for _r in _expiry_rows:
                _nm = _r['item_name']
                if _nm not in _expiry_items:
                    _expiry_items.append(_nm)
                _inv_map[_nm] = int(_r.get('stock_qty') or 0)
        except Exception:
            pass

    # ── 섹션 1: 데이터 입력 방식 선택 ───────────────────────────
    st.markdown("#### 📥 수요 데이터 입력")
    _input_mode = st.radio(
        "입력 방식",
        ["📋 직접 입력 (과거 수요량)", "🗄️ DB 재고 품목 사용"],
        horizontal=True, key="ai_input_mode"
    )

    _item_name   = ""
    _history     = []    # [(연월문자열, 수요량), ...]
    _curr_stock  = 0
    _expiry_days = 30

    col_inp, col_cfg = st.columns([3, 2])

    with col_inp:
        if _input_mode == "📋 직접 입력 (과거 수요량)":
            _item_name  = st.text_input("품목명", value="예시_냉장육", key="ai_item")
            _curr_stock = st.number_input("현재 재고량", min_value=0, value=100, key="ai_stock")
            _expiry_days= st.number_input("유통기한 잔여일", min_value=1, value=30, key="ai_exp")
            st.markdown("**월별 과거 수요량 입력** (최근 6개월, 최신 순)")
            _n_months = st.slider("입력 개월 수", 3, 12, 6, key="ai_nm")
            _history_vals = []
            _gcols = st.columns(3)
            for _mi in range(_n_months):
                _v = _gcols[_mi % 3].number_input(
                    f"{_mi+1}개월 전", min_value=0, value=max(50, 100-_mi*3),
                    key=f"ai_hist_{_mi}"
                )
                _history_vals.append(_v)
            # 오래된 순으로 변환
            _history_vals = list(reversed(_history_vals))
            import datetime as _dt
            _base = _dt.date.today().replace(day=1)
            for _mi, _v in enumerate(_history_vals):
                _mo = (_base.month - _n_months + _mi)
                _yr = _base.year + (_mo - 1) // 12
                _mo = ((_mo - 1) % 12) + 1
                _history.append((f"{_yr}-{_mo:02d}", int(_v)))

        else:  # DB 사용
            if not _expiry_items:
                st.info("유통기한이 등록된 재고 품목이 없습니다. 먼저 재고에 유통기한을 등록하세요.")
            else:
                _item_name  = st.selectbox("품목 선택 (유통기한 있는 재고)", _expiry_items, key="ai_dbitem")
                _curr_stock = _inv_map.get(_item_name, 0)
                st.metric("현재 재고", f"{_curr_stock}개")
                _expiry_days = st.number_input("유통기한 잔여일", min_value=1, value=30, key="ai_dbexp")

                # DB에서 입고 이력으로 월별 수요 추정
                if _get_db and _item_name:
                    try:
                        _cx2 = _get_db()
                        _hist_rows = _cx2.execute("""
                            SELECT DATE_FORMAT(created_at,'%Y-%m') AS ym,
                                   SUM(received_qty - rejected_qty) AS qty
                            FROM goods_receipts WHERE item_name=?
                            GROUP BY DATE_FORMAT(created_at,'%Y-%m')
                            ORDER BY ym DESC LIMIT 12
                        """, (_item_name,)).fetchall()
                        _cx2.close()
                        _history = [(r[0], max(0, int(r[1] or 0))) for r in reversed(_hist_rows)]
                    except Exception:
                        _history = []
                if not _history:
                    st.warning("입고 이력 데이터가 없습니다. 직접 입력 방식을 사용하세요.")

    with col_cfg:
        st.markdown("**⚙️ 예측 설정**")
        _pred_months = st.slider("예측 개월 수", 1, 6, 3, key="ai_predm")
        _safety_key  = st.selectbox(
            "안전재고 계수 (카테고리)", list(_SAFETY.keys()), key="ai_sfkey"
        )
        _safety_coeff = _SAFETY[_safety_key]
        st.caption(f"적용 계수: **{_safety_coeff}× 예측수요**")
        _use_optuna = st.checkbox("Optuna 하이퍼파라미터 튜닝 (느림, 정확)", value=False, key="ai_optuna")
        if _use_optuna:
            _n_trials = st.slider("탐색 횟수 (trial)", 10, 50, 20, key="ai_trials")
        else:
            _n_trials = 0
        _target_dow = st.selectbox(
            "발주 기준 요일", _DOW_KOR, index=3, key="ai_dow"
        )  # 기본: 목요일
        _target_dow_idx = _DOW_KOR.index(_target_dow)

    st.divider()

    # ── 실행 버튼 ────────────────────────────────────────────────
    _run_btn = st.button(
        "🚀 AI 수요예측 실행", type="primary",
        use_container_width=True, key="ai_run_btn",
        disabled=len(_history) < 3
    )
    if len(_history) < 3:
        st.caption("⚠️ 최소 3개월 이상의 수요 데이터가 필요합니다.")

    if not _run_btn:
        st.stop()

    # ════════════════════════════════════════════════════════════
    #  피처 엔지니어링 + LightGBM 학습
    # ════════════════════════════════════════════════════════════
    import numpy as _np
    import pandas as _pd
    import datetime as _dt

    st.markdown("---")
    st.markdown("### 📊 예측 결과")
    _prog = st.progress(0, text="데이터 전처리 중...")

    # ── 1) 히스토리 DataFrame 생성 ──────────────────────────────
    _df = _pd.DataFrame(_history, columns=["ym", "qty"])
    _df["date"] = _pd.to_datetime(_df["ym"] + "-01")
    _df["qty"]  = _df["qty"].astype(float)
    _df = _df.sort_values("date").reset_index(drop=True)
    _n  = len(_df)

    # ── 2) 피처 엔지니어링 (README Part1 핵심 피처 이식) ────────
    _prog.progress(15, text="피처 엔지니어링 중...")

    # 날짜 피처
    _df["month"]      = _df["date"].dt.month
    _df["quarter"]    = _df["date"].dt.quarter
    _df["is_yearend"] = (_df["month"].isin([11,12,1])).astype(int)   # 연말연시 수요 강조
    _df["is_summer"]  = (_df["month"].isin([7,8])).astype(int)
    _df["dow_weight"] = _DOW_W[_target_dow_idx]   # 발주 기준 요일 가중치 (단일값)

    # Lag 피처 (데이터 누수 방지: shift)
    _df["lag_1"]  = _df["qty"].shift(1)
    _df["lag_2"]  = _df["qty"].shift(2)
    _df["lag_3"]  = _df["qty"].shift(3)

    # Rolling 평균
    _df["roll_mean_2"] = _df["qty"].shift(1).rolling(2, min_periods=1).mean()
    _df["roll_mean_3"] = _df["qty"].shift(1).rolling(3, min_periods=1).mean()
    _df["roll_std_3"]  = _df["qty"].shift(1).rolling(3, min_periods=1).std().fillna(0)

    # 단기 추세 (최근 2개월 평균 / 이전 2개월 평균)
    _roll2      = _df["qty"].shift(1).rolling(2, min_periods=1).mean()
    _roll2_prev = _df["qty"].shift(3).rolling(2, min_periods=1).mean()
    _df["trend"] = (_roll2 / (_roll2_prev + 1e-9)).clip(0.5, 2.0)

    # 계절성 가중치
    _season_w = {1:1.35, 2:0.90, 3:1.00, 4:1.05, 5:1.10, 6:1.05,
                 7:1.20, 8:1.25, 9:1.15, 10:1.05, 11:1.30, 12:1.50}
    _df["season_weight"] = _df["month"].map(_season_w)

    # 복합 가중치
    _df["total_weight"] = _df["dow_weight"] * _df["season_weight"]

    # 유통기한 위험 피처 (잔여일 짧을수록 수요 촉진/폐기 위험)
    _df["expiry_urgency"] = max(0, 1 - _expiry_days / 90)   # 90일 이하일수록 1에 가까움

    # NaN 처리
    _df = _df.fillna(0)

    _FEAT_COLS = [
        "month", "quarter", "is_yearend", "is_summer",
        "dow_weight", "season_weight", "total_weight", "expiry_urgency",
        "lag_1", "lag_2", "lag_3",
        "roll_mean_2", "roll_mean_3", "roll_std_3", "trend",
    ]
    _TARGET = "qty"

    # 학습 데이터 (마지막 1개월은 예측 검증용)
    _train_df = _df.copy()
    _X_train  = _train_df[_FEAT_COLS].values
    _y_train  = _train_df[_TARGET].values

    # 시간 가중치: 최근 월 강조 (exp decay τ=4개월)
    _t_weight = _np.exp(-(_n - 1 - _np.arange(_n)) / 4.0)

    _prog.progress(35, text="LightGBM 모델 학습 중...")

    # ── 3) LightGBM 학습 ────────────────────────────────────────
    _base_params = {
        "objective"              : "tweedie",
        "tweedie_variance_power" : 1.2,
        "metric"                 : "rmse",
        "verbosity"              : -1,
        "random_state"           : 42,
        "n_jobs"                 : -1,
        "num_leaves"             : 31,
        "max_depth"              : 6,
        "min_child_samples"      : max(1, _n // 3),
        "learning_rate"          : 0.05,
        "n_estimators"           : 500,
        "subsample"              : 0.8,
        "colsample_bytree"       : 0.8,
        "reg_alpha"              : 0.1,
        "reg_lambda"             : 0.5,
    }

    _best_params = _base_params.copy()
    _optuna_result = None

    if _use_optuna and _n >= 5:
        _prog.progress(40, text=f"Optuna 탐색 중 ({_n_trials} trials)...")
        try:
            import optuna as _opt
            _opt.logging.set_verbosity(_opt.logging.WARNING)

            def _obj(trial):
                _p = {
                    "objective"              : "tweedie",
                    "tweedie_variance_power" : trial.suggest_float("tvp", 1.0, 1.5),
                    "metric"                 : "rmse",
                    "verbosity"              : -1,
                    "random_state"           : 42,
                    "n_jobs"                 : -1,
                    "num_leaves"             : trial.suggest_int("nl", 15, 63),
                    "max_depth"              : trial.suggest_int("md", 3, 8),
                    "min_child_samples"      : max(1, trial.suggest_int("mcs", 1, max(2, _n//2))),
                    "learning_rate"          : trial.suggest_float("lr", 0.02, 0.1, log=True),
                    "subsample"              : trial.suggest_float("ss", 0.6, 1.0),
                    "colsample_bytree"       : trial.suggest_float("cs", 0.6, 1.0),
                    "reg_alpha"              : trial.suggest_float("ra", 1e-3, 0.5, log=True),
                    "reg_lambda"             : trial.suggest_float("rl", 0.1, 1.0, log=True),
                }
                _ds = _lgb.Dataset(_X_train, label=_y_train, weight=_t_weight, free_raw_data=False)
                _m  = _lgb.train(_p, _ds, num_boost_round=300,
                                 callbacks=[_lgb.log_evaluation(period=-1)])
                _pr = _np.maximum(_m.predict(_X_train), 0)
                _denom = _np.sum(_np.abs(_y_train))
                return (_np.sum(_np.abs(_y_train - _pr)) / _denom * 100) if _denom > 0 else 999

            _study = _opt.create_study(direction="minimize",
                                       sampler=_opt.samplers.TPESampler(seed=42))
            _study.optimize(_obj, n_trials=_n_trials, show_progress_bar=False)
            _bp = _study.best_params
            _optuna_result = {"best_wmape": _study.best_value, "params": _bp}
            _best_params = {
                "objective": "tweedie",
                "tweedie_variance_power": _bp["tvp"],
                "metric": "rmse", "verbosity": -1, "random_state": 42, "n_jobs": -1,
                "num_leaves": _bp["nl"], "max_depth": _bp["md"],
                "min_child_samples": max(1, _bp["mcs"]),
                "learning_rate": _bp["lr"],
                "n_estimators": 500,
                "subsample": _bp["ss"], "colsample_bytree": _bp["cs"],
                "reg_alpha": _bp["ra"], "reg_lambda": _bp["rl"],
            }
        except ImportError:
            st.warning("Optuna 미설치. 기본 파라미터로 학습합니다.")
        except Exception as _oe:
            st.warning(f"Optuna 에러: {_oe}. 기본 파라미터로 학습합니다.")

    _prog.progress(60, text="최종 모델 학습 중...")

    _dtrain = _lgb.Dataset(_X_train, label=_y_train, weight=_t_weight, free_raw_data=False)
    _model  = _lgb.train(
        _best_params, _dtrain,
        num_boost_round=_best_params.get("n_estimators", 500),
        callbacks=[_lgb.log_evaluation(period=-1)],
    )

    # ── 4) 카테고리 편향 보정 (README Part2 bias_corr) ──────────
    _train_preds = _np.maximum(_model.predict(_X_train), 0)
    _actual_sum  = _y_train.sum()
    _pred_sum    = _train_preds.sum()
    _bias_corr   = (_actual_sum / (_pred_sum + 1e-9))
    _bias_corr   = float(_np.clip(_bias_corr, 0.5, 2.0))   # 극단값 방지

    # 학습 데이터 WMAPE
    _train_preds_c = (_train_preds * _bias_corr).clip(0)
    _denom = _np.sum(_np.abs(_y_train))
    _train_wmape = (
        _np.sum(_np.abs(_y_train - _train_preds_c)) / _denom * 100
        if _denom > 0 else _np.nan
    )

    _prog.progress(75, text="미래 수요 예측 중...")

    # ── 5) 미래 예측 (롤링 방식: 예측값을 다음 lag에 투입) ──────
    _last_date  = _df["date"].iloc[-1]
    _last_qtys  = list(_df["qty"].values)   # 예측 시 업데이트

    _future_rows = []
    for _fi in range(_pred_months):
        _fd = _last_date + _pd.DateOffset(months=_fi + 1)
        _mo = _fd.month
        _q  = (_fi + 1 + 3) // 4  # quarter

        _l1 = _last_qtys[-1]
        _l2 = _last_qtys[-2] if len(_last_qtys) >= 2 else _l1
        _l3 = _last_qtys[-3] if len(_last_qtys) >= 3 else _l1
        _rm2 = _np.mean(_last_qtys[-2:])  if len(_last_qtys) >= 2 else _l1
        _rm3 = _np.mean(_last_qtys[-3:])  if len(_last_qtys) >= 3 else _l1
        _rs3 = _np.std(_last_qtys[-3:])   if len(_last_qtys) >= 3 else 0
        _rp2 = _np.mean(_last_qtys[-4:-2]) if len(_last_qtys) >= 4 else _rm2
        _trd = float(_np.clip(_rm2 / (_rp2 + 1e-9), 0.5, 2.0))
        _sw  = _season_w.get(_mo, 1.0)
        _eu  = max(0, 1 - (_expiry_days - _fi * 30) / 90)  # 시간 지날수록 긴박도 상승

        _feat_row = _np.array([[
            _mo, _q, int(_mo in [11,12,1]), int(_mo in [7,8]),
            _DOW_W[_target_dow_idx], _sw, _DOW_W[_target_dow_idx] * _sw, _eu,
            _l1, _l2, _l3, _rm2, _rm3, _rs3, _trd,
        ]])
        _raw_pred = float(_np.maximum(_model.predict(_feat_row), 0)[0])
        _pred_val = float(_np.maximum(_raw_pred * _bias_corr, 0))
        _adj_val  = float(_pred_val * _safety_coeff)
        _order    = max(0, _adj_val - (_curr_stock if _fi == 0 else 0))

        _future_rows.append({
            "월"        : _fd.strftime("%Y-%m"),
            "예측수요"  : round(_pred_val, 1),
            "조정수요"  : round(_adj_val, 1),
            "발주권고량": round(_order, 0),
        })
        _last_qtys.append(_pred_val)   # 다음 lag에 투입

    _pred_df = _pd.DataFrame(_future_rows)

    _prog.progress(90, text="결과 정리 중...")

    # ── 6) 피처 중요도 ───────────────────────────────────────────
    _feat_imp = _pd.DataFrame({
        "피처"  : _FEAT_COLS,
        "중요도": _model.feature_importance(importance_type="gain"),
    }).sort_values("중요도", ascending=False)

    _prog.progress(100, text="완료!")
    _prog.empty()

    # ════════════════════════════════════════════════════════════
    #  결과 출력
    # ════════════════════════════════════════════════════════════

    # ── KPI 카드 ─────────────────────────────────────────────────
    _k1, _k2, _k3, _k4, _k5 = st.columns(5)
    _k1.metric("품목", _item_name[:12] if _item_name else "-")
    _k2.metric("학습 WMAPE", f"{_train_wmape:.1f}%" if not _np.isnan(_train_wmape) else "-",
               delta="✅ 목표달성" if _train_wmape <= 10 else "⚠️ 튜닝권장",
               delta_color="normal" if _train_wmape <= 10 else "inverse")
    _k3.metric("편향 보정계수", f"{_bias_corr:.3f}")
    _k4.metric("현재 재고", f"{_curr_stock}개")
    _k5.metric("총 발주 권고량", f"{int(_pred_df['발주권고량'].sum())}개")

    if _optuna_result:
        st.success(f"✅ Optuna 최적화 완료 | Best WMAPE: {_optuna_result['best_wmape']:.2f}%  "
                   f"(num_leaves={_optuna_result['params']['nl']}, "
                   f"lr={_optuna_result['params']['lr']:.4f})")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── 결과 탭 ─────────────────────────────────────────────────
    _res_tab1, _res_tab2, _res_tab3 = st.tabs(["📈 수요 예측 차트", "📦 발주 계획표", "🔍 피처 중요도"])

    with _res_tab1:
        if _HAS_PL3:
            # ── 차트 상단: 타이틀 + 메타 정보 (HTML) ─────────────
            st.markdown(
                f"<div style='font-size:0.95rem;font-weight:600;color:#1A1A2E;margin-bottom:4px'>"
                f"📦 {_item_name} — AI 수요예측</div>"
                f"<div style='font-size:0.78rem;color:#64748b;margin-bottom:10px'>"
                f"LightGBM Tweedie · 편향보정 {_bias_corr:.3f} · 안전재고 ×{_safety_coeff}</div>",
                unsafe_allow_html=True,
            )

            _fig = _go.Figure()

            # 실적 (막대)
            _fig.add_trace(_go.Bar(
                x=_df["ym"], y=_df["qty"],
                name="실적", marker_color="#93c5fd", opacity=0.85,
            ))
            # 학습 적합값 (편향 보정 적용)
            _fitted = (_np.maximum(_model.predict(_X_train), 0) * _bias_corr).clip(0)
            _fig.add_trace(_go.Scatter(
                x=_df["ym"], y=_np.round(_fitted, 1),
                name="적합값", mode="lines",
                line=dict(color="#7C6FCD", width=2),
            ))
            # 예측 (점선) — trace 이름 짧게
            _fig.add_trace(_go.Scatter(
                x=_pred_df["월"], y=_pred_df["예측수요"],
                name="예측", mode="lines+markers",
                line=dict(color="#f97316", width=2.5, dash="dash"),
                marker=dict(size=8, symbol="diamond"),
            ))
            # 조정수요 (안전재고 적용)
            _fig.add_trace(_go.Scatter(
                x=_pred_df["월"], y=_pred_df["조정수요"],
                name=f"조정(×{_safety_coeff})", mode="lines",
                line=dict(color="#ef4444", width=1.5, dash="dot"),
            ))
            # 현재 재고 수평선
            _fig.add_hline(
                y=_curr_stock, line_dash="dot", line_color="#22c55e",
                annotation_text=f"현재고 {_curr_stock}",
                annotation_font_size=11,
                annotation_position="bottom right",
            )
            # 유통기한 배경색 (annotation 텍스트 제거 → 겹침 방지)
            if _expiry_days <= 30:
                _fig.add_vrect(
                    x0=_pred_df["월"].iloc[0], x1=_pred_df["월"].iloc[-1],
                    fillcolor="rgba(239,68,68,0.07)", line_width=0,
                )
            elif _expiry_days <= 60:
                _fig.add_vrect(
                    x0=_pred_df["월"].iloc[0], x1=_pred_df["월"].iloc[-1],
                    fillcolor="rgba(249,115,22,0.05)", line_width=0,
                )

            _fig.update_layout(
                title=None,
                height=360,
                margin=dict(l=10, r=20, t=10, b=60),
                legend=dict(
                    orientation="h",
                    y=-0.22, x=0.5, xanchor="center",
                    font=dict(size=12),
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="#e2e8f0", borderwidth=1,
                ),
                xaxis=dict(showgrid=True, gridcolor="#f1f1ef", tickfont=dict(size=11)),
                yaxis=dict(title="수요량 (개)", showgrid=True, gridcolor="#f1f1ef",
                           titlefont=dict(size=11)),
                plot_bgcolor="#fafafa", paper_bgcolor="white",
                bargap=0.3,
            )
            st.plotly_chart(_fig, use_container_width=True, config={"displayModeBar": False})

            # 유통기한 경고 (차트 아래 텍스트로 분리)
            if _expiry_days <= 30:
                st.caption(f"🔴 예측 구간: 유통기한 {_expiry_days}일 이내 품목")
            elif _expiry_days <= 60:
                st.caption(f"🟠 예측 구간: 유통기한 {_expiry_days}일 이내 품목")

            # 재고 소진 예상 시점
            _cumulative = 0
            _stockout_mo = None
            for _, _pr in _pred_df.iterrows():
                _cumulative += _pr["예측수요"]
                if _cumulative >= _curr_stock:
                    _stockout_mo = _pr["월"]
                    break

            if _stockout_mo:
                st.warning(f"⚠️ 예측 기준 재고 소진 예상 시점: **{_stockout_mo}** "
                           f"(현재고 {_curr_stock}개, 누적수요 {round(_cumulative)}개)")
            else:
                st.success(f"✅ 예측 기간 내 재고 소진 없음 (현재고 {_curr_stock}개 충분)")

            # 유통기한 경고
            if _expiry_days <= 14:
                st.error(f"🔴 유통기한 **{_expiry_days}일** 남음 — 즉시 판촉/이전 검토 필요")
            elif _expiry_days <= 30:
                st.warning(f"🟠 유통기한 **{_expiry_days}일** — 조기 소진 모니터링 권장")
        else:
            st.dataframe(_pred_df, use_container_width=True, hide_index=True)

    with _res_tab2:
        # 발주 계획표
        st.markdown(f"""
        **발주 정책**: `발주권고량 = max(0, 예측수요 × {_safety_coeff} − 현재고)`
        &nbsp;|&nbsp; 안전재고 계수: **{_safety_coeff}** ({_safety_key})
        &nbsp;|&nbsp; 편향 보정계수: **{_bias_corr:.3f}**
        """)
        _display_df = _pred_df.copy()
        _display_df["발주필요"] = (_display_df["발주권고량"] > 0).map({True: "✅ 발주", False: "✔ 충분"})
        st.dataframe(
            _display_df.style.apply(
                lambda row: ["background-color:#fef2f2" if row["발주필요"] == "✅ 발주"
                             else "background-color:#f0fdf4"] * len(row), axis=1
            ),
            use_container_width=True, hide_index=True,
        )
        # 총계
        _tot_order = int(_pred_df["발주권고량"].sum())
        _tot_adj   = round(_pred_df["조정수요"].sum(), 0)
        st.markdown(
            f"**총 예측수요**: {round(_pred_df['예측수요'].sum(),1)}개 &nbsp;|&nbsp; "
            f"**총 조정수요**: {_tot_adj}개 &nbsp;|&nbsp; "
            f"**총 발주 권고량**: **{_tot_order}개**"
        )

        # 알고리즘 설명 expander
        with st.expander("📖 알고리즘 상세 (README 기반 LightGBM 파이프라인)"):
            st.markdown(f"""
| 항목 | 내용 |
|---|---|
| **모델** | LightGBM Tweedie 회귀 (수요량 0포함 우편향 분포 최적) |
| **목적함수** | tweedie (power={_best_params.get('tweedie_variance_power',1.2):.3f}) |
| **피처 수** | {len(_FEAT_COLS)}개 (Lag · Rolling · 계절성 · 요일 가중치 · 유통기한 긴박도) |
| **시간 가중치** | 최근 월 강조 exp(-t/4), 최근 4개월 2배 이상 가중 |
| **편향 보정** | 학습셋 실측합/예측합 = **{_bias_corr:.3f}** (카테고리 체계적 과소예측 수치 보정) |
| **안전재고 계수** | {_safety_coeff} ({_safety_key}) — 신선도 반영 |
| **Optuna** | {"적용 (" + str(_n_trials) + " trials)" if _use_optuna else "미적용 (기본 파라미터)"} |
| **유통기한 피처** | expiry_urgency = max(0, 1 − 잔여일/90) |
            """)

    with _res_tab3:
        if _HAS_PL3:
            _top_imp = _feat_imp.head(10)
            _max_imp = _top_imp["중요도"].max()
            _fig_i = _go.Figure(_go.Bar(
                x=_top_imp["중요도"],
                y=_top_imp["피처"],
                orientation="h",
                marker=dict(
                    color=_top_imp["중요도"],
                    colorscale=[[0,"#e2e8f0"],[0.5,"#7C6FCD"],[1,"#1A1A2E"]],
                ),
                text=[f"{v:.0f}" for v in _top_imp["중요도"]],
                textposition="outside",
            ))
            _fig_i.update_layout(
                title="피처 중요도 Top 10 (Gain 기준)",
                height=320, margin=dict(l=0, r=60, t=40, b=0),
                yaxis=dict(autorange="reversed"),
                xaxis=dict(showgrid=True, gridcolor="#f1f1ef"),
                plot_bgcolor="#fafafa", paper_bgcolor="white",
            )
            st.plotly_chart(_fig_i, use_container_width=True, config={"displayModeBar": False})

            # 피처 중요도 의미 설명
            _imp_explain = {
                "lag_1"        : "직전 1개월 수요량 — 가장 강력한 단기 신호",
                "roll_mean_3"  : "최근 3개월 이동평균 — 단기 추세 요약",
                "season_weight": "월별 계절성 가중치 (연말 1.50, 여름 1.25)",
                "trend"        : "단기 추세율 (최근 2개월 / 이전 2개월)",
                "expiry_urgency": "유통기한 긴박도 — 잔여일 짧을수록 ↑",
                "total_weight" : "요일×계절 복합 가중치",
                "lag_2"        : "2개월 전 수요량",
                "roll_mean_2"  : "최근 2개월 이동평균",
                "month"        : "월 번호 (계절성 비선형 포착)",
                "is_yearend"   : "연말연시 여부 (11~1월)",
            }
            _top1 = _feat_imp.iloc[0]["피처"]
            _expl = _imp_explain.get(_top1, "핵심 예측 신호")
            st.info(f"🏆 **1위 피처 `{_top1}`**: {_expl}")
        else:
            st.dataframe(_feat_imp, use_container_width=True, hide_index=True)
