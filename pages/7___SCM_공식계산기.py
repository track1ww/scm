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
