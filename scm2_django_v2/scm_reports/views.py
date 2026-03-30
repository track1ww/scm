import datetime
from decimal import Decimal

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .pdf_utils import make_styles, header_table_style, build_pdf, _FONT_NAME

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER


class PurchaseOrderPDF(APIView):
    """GET /api/reports/po/{pk}/pdf/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from scm_mm.models import PurchaseOrder
        try:
            po = PurchaseOrder.objects.select_related('supplier').get(
                pk=pk, company=request.user.company
            )
        except PurchaseOrder.DoesNotExist:
            return Response({'detail': '발주서를 찾을 수 없습니다.'}, status=404)

        title_s, sub_s, label_s = make_styles()
        elements = []
        elements.append(Paragraph('발 주 서', title_s))
        elements.append(Paragraph(f'발주번호: {po.po_number}', sub_s))
        elements.append(Spacer(1, 4 * mm))

        # Compute total amount from quantity * unit_price
        try:
            total_amount = po.quantity * po.unit_price
            total_str = f'{total_amount:,.2f} {po.currency}'
        except Exception:
            total_str = '-'

        supplier_name = str(po.supplier) if po.supplier else '-'
        delivery_date = str(po.delivery_date) if po.delivery_date else '-'

        info_data = [
            ['공급처',  supplier_name,                        '발주번호',  po.po_number],
            ['품목명',  po.item_name,                         '발주일',    po.created_at.strftime('%Y-%m-%d')],
            ['수량',    str(po.quantity),                     '단가',      f'{po.unit_price:,.2f} {po.currency}'],
            ['납기일',  delivery_date,                        '총금액',    total_str],
            ['창고',    po.warehouse or '-',                  '상태',      po.status],
            ['비고',    po.note or '-',                       '',          ''],
        ]

        info_table = Table(info_data, colWidths=[30 * mm, 65 * mm, 30 * mm, 45 * mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME',        (0, 0), (-1, -1), _FONT_NAME),
            ('FONTSIZE',        (0, 0), (-1, -1), 9),
            ('GRID',            (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND',      (0, 0), (0, -1),  colors.HexColor('#f1f5f9')),
            ('BACKGROUND',      (2, 0), (2, -1),  colors.HexColor('#f1f5f9')),
            ('BOTTOMPADDING',   (0, 0), (-1, -1), 5),
            ('TOPPADDING',      (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(f'생성일시: {timezone.now().strftime("%Y-%m-%d %H:%M")}', label_s))

        pdf_bytes = build_pdf(elements)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="PO_{po.po_number}.pdf"'
        return resp


class InspectionReportPDF(APIView):
    """GET /api/reports/inspection/{pk}/pdf/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from scm_qm.models import InspectionResult

        try:
            record = InspectionResult.objects.select_related('plan').get(
                pk=pk, company=request.user.company
            )
        except InspectionResult.DoesNotExist:
            return Response({'detail': '검사 기록을 찾을 수 없습니다.'}, status=404)

        title_s, sub_s, label_s = make_styles()
        elements = []
        elements.append(Paragraph('검 사 성 적 서', title_s))
        elements.append(Paragraph(f'검사번호: {record.result_number}', sub_s))
        elements.append(Spacer(1, 4 * mm))

        plan_name = str(record.plan) if record.plan else '-'
        inspected_at = record.inspected_at.strftime('%Y-%m-%d %H:%M') if record.inspected_at else '-'

        try:
            pass_rate_val = f'{record.pass_rate}%'
        except Exception:
            pass_rate_val = '-'

        info_data = [
            ['검사번호',  record.result_number,   '검사계획',   plan_name],
            ['품목명',    record.item_name,        '로트번호',   record.lot_number or '-'],
            ['검사수량',  str(record.inspected_qty), '합격수량',  str(record.passed_qty)],
            ['불합격수량', str(record.failed_qty),  '합격률',    pass_rate_val],
            ['결과',      record.result,           '검사일시',   inspected_at],
            ['검사자',    record.inspector or '-', '',           ''],
            ['비고',      record.remark or '-',    '',           ''],
        ]

        info_table = Table(info_data, colWidths=[30 * mm, 65 * mm, 30 * mm, 45 * mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME',        (0, 0), (-1, -1), _FONT_NAME),
            ('FONTSIZE',        (0, 0), (-1, -1), 9),
            ('GRID',            (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND',      (0, 0), (0, -1),  colors.HexColor('#f1f5f9')),
            ('BACKGROUND',      (2, 0), (2, -1),  colors.HexColor('#f1f5f9')),
            ('BOTTOMPADDING',   (0, 0), (-1, -1), 5),
            ('TOPPADDING',      (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(f'생성일시: {timezone.now().strftime("%Y-%m-%d %H:%M")}', label_s))

        pdf_bytes = build_pdf(elements)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="Inspection_{record.result_number}.pdf"'
        return resp


class SalesInvoicePDF(APIView):
    """GET /api/reports/invoice/{pk}/pdf/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from scm_sd.models import SalesInvoice
        try:
            inv = SalesInvoice.objects.select_related(
                'sales_order__customer', 'delivery'
            ).get(pk=pk, company=request.user.company)
        except SalesInvoice.DoesNotExist:
            return Response({'detail': '송장을 찾을 수 없습니다.'}, status=404)

        title_s, sub_s, label_s = make_styles()
        elements = []
        elements.append(Paragraph('세  금  계  산  서', title_s))
        elements.append(Paragraph(f'송장번호: {inv.invoice_number}', sub_s))
        elements.append(Spacer(1, 4 * mm))

        order = inv.sales_order
        customer = order.customer if order else None

        info_data = [
            ['공급자', request.user.company.name if hasattr(request.user.company, 'name') else str(request.user.company),
             '공급받는자', str(customer) if customer else '-'],
            ['송장일', str(inv.invoice_date), '결제기한', str(inv.due_date or '-')],
            ['공급가액', f"{int(inv.supply_amount):,}원", '부가세(10%)', f"{int(inv.vat_amount):,}원"],
            ['합계금액', f"{int(inv.total_amount):,}원", '상태', inv.get_status_display()],
        ]
        info_table = Table(info_data, colWidths=[30 * mm, 60 * mm, 30 * mm, 50 * mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), _FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f1f5f9')),
            ('FONTSIZE', (1, 2), (1, 2), 11),
            ('FONTSIZE', (1, 3), (1, 3), 12),
            ('TEXTCOLOR', (1, 3), (1, 3), colors.HexColor('#1e40af')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8 * mm))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph(
            f'본 세금계산서는 {timezone.now().strftime("%Y년 %m월 %d일")}에 발행되었습니다.', label_s
        ))

        pdf_bytes = build_pdf(elements)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="Invoice_{inv.invoice_number}.pdf"'
        return resp


# ─────────────────────────────────────────────────────────────
# 재무제표 PDF  GET /api/reports/financial-statement/pdf/
#   ?type=income|balance  &year=YYYY  &month=M
# ─────────────────────────────────────────────────────────────

class FinancialStatementPDF(APIView):
    """손익계산서 또는 대차대조표를 PDF로 출력."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stmt_type = request.query_params.get('type', 'income')
        try:
            year  = int(request.query_params.get('year',  timezone.now().year))
            month = int(request.query_params.get('month', timezone.now().month))
        except ValueError:
            return Response({'detail': 'year/month 파라미터가 잘못되었습니다.'}, status=400)

        company = request.user.company
        data = _build_statement_data(company, stmt_type, year, month)

        title_s, sub_s, label_s = make_styles()
        right_s = ParagraphStyle('Right', fontName=_FONT_NAME, fontSize=9,
                                  alignment=TA_RIGHT)
        elements = []

        period_label = f'{year}년 {month}월'
        if stmt_type == 'income':
            elements.append(Paragraph('손  익  계  산  서', title_s))
            elements.append(Paragraph(f'기간: {period_label}  |  회사: {company}', sub_s))
            elements.append(Spacer(1, 5 * mm))
            elements += _income_table(data, label_s, right_s)
        else:
            elements.append(Paragraph('재  무  상  태  표', title_s))
            elements.append(Paragraph(f'기준일: {period_label} 말  |  회사: {company}', sub_s))
            elements.append(Spacer(1, 5 * mm))
            elements += _balance_table(data, label_s, right_s)

        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph(f'출력일시: {timezone.now().strftime("%Y-%m-%d %H:%M")}', label_s))

        pdf_bytes = build_pdf(elements)
        fname = f'{"IS" if stmt_type == "income" else "BS"}_{year}{month:02d}.pdf'
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp


def _build_statement_data(company, stmt_type, year, month):
    """FI AccountMoveLine 집계 (FinancialStatementView 와 동일 로직)."""
    from scm_fi.models import AccountMoveLine
    from django.db.models import Sum

    date_from = datetime.date(year, month, 1)
    if month == 12:
        date_to = datetime.date(year + 1, 1, 1)
    else:
        date_to = datetime.date(year, month + 1, 1)

    qs = (AccountMoveLine.objects
          .filter(
              move__company=company,
              move__state='POSTED',
              move__posting_date__gte=date_from,
              move__posting_date__lt=date_to,
          )
          .select_related('account'))

    result = {}
    for line in qs:
        code  = line.account.code
        name  = line.account.name
        atype = line.account.account_type
        if code not in result:
            result[code] = {'name': name, 'type': atype, 'debit': Decimal('0'), 'credit': Decimal('0')}
        result[code]['debit']  += line.debit  or Decimal('0')
        result[code]['credit'] += line.credit or Decimal('0')

    revenues  = [{'code': k, **v} for k, v in result.items() if v['type'] == 'REVENUE']
    expenses  = [{'code': k, **v} for k, v in result.items() if v['type'] == 'EXPENSE']
    assets    = [{'code': k, **v} for k, v in result.items() if v['type'] == 'ASSET']
    liabs     = [{'code': k, **v} for k, v in result.items() if v['type'] == 'LIABILITY']
    equity    = [{'code': k, **v} for k, v in result.items() if v['type'] == 'EQUITY']

    total_rev  = sum(r['credit'] - r['debit']  for r in revenues)
    total_exp  = sum(e['debit']  - e['credit'] for e in expenses)
    net_income = total_rev - total_exp

    total_assets = sum(a['debit'] - a['credit'] for a in assets)
    total_liabs  = sum(l['credit'] - l['debit'] for l in liabs)
    total_equity = sum(e['credit'] - e['debit'] for e in equity)

    return {
        'revenues': revenues, 'expenses': expenses,
        'assets': assets,     'liabilities': liabs, 'equity': equity,
        'total_revenue': total_rev,   'total_expense': total_exp,   'net_income': net_income,
        'total_assets':  total_assets, 'total_liabilities': total_liabs, 'total_equity': total_equity,
    }


def _income_table(data, label_s, right_s):
    """손익계산서 테이블 엘리먼트 목록 반환."""
    elements = []
    col_w = [120 * mm, 50 * mm]
    hstyle = header_table_style()

    def _section(title, rows, total_label, total_val):
        tdata = [[title, '금액(원)']]
        for r in rows:
            net = float(r['credit'] - r['debit'])
            tdata.append([f"  {r['code']} {r['name']}", f"{net:>15,.0f}"])
        tdata.append([total_label, f"{float(total_val):>15,.0f}"])
        t = Table(tdata, colWidths=col_w)
        t.setStyle(hstyle)
        t.setStyle(TableStyle([
            ('FONTNAME',   (0, 0), (-1, -1), _FONT_NAME),
            ('ALIGN',      (1, 1), (1, -1),  'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eff6ff')),
            ('FONTSIZE',   (0, -1), (-1, -1), 9),
        ]))
        return t

    # 수익 섹션
    elements.append(_section('수  익', data['revenues'],
                              '수익 합계', data['total_revenue']))
    elements.append(Spacer(1, 4 * mm))

    # 비용 섹션
    exp_rows = [{'code': r['code'], 'name': r['name'],
                 'credit': r['debit'], 'debit': r['credit']}
                for r in data['expenses']]
    elements.append(_section('비  용', exp_rows,
                              '비용 합계', data['total_expense']))
    elements.append(Spacer(1, 6 * mm))

    # 당기순이익
    ni_color = colors.HexColor('#16a34a') if data['net_income'] >= 0 else colors.HexColor('#dc2626')
    ni_table = Table([
        ['당 기 순 이 익', f"{float(data['net_income']):>15,.0f}  원"]
    ], colWidths=col_w)
    ni_table.setStyle(TableStyle([
        ('FONTNAME',   (0, 0), (-1, -1), _FONT_NAME),
        ('FONTSIZE',   (0, 0), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fdf4')),
        ('TEXTCOLOR',  (1, 0), (1, 0),   ni_color),
        ('ALIGN',      (1, 0), (1, 0),   'RIGHT'),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#86efac')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
    ]))
    elements.append(ni_table)
    return elements


def _balance_table(data, label_s, right_s):
    """대차대조표 테이블 엘리먼트 목록 반환."""
    elements = []
    col_w = [120 * mm, 50 * mm]
    hstyle = header_table_style()

    def _section(title, rows, total_label, total_val):
        tdata = [[title, '금액(원)']]
        for r in rows:
            net = float(r['debit'] - r['credit'])
            tdata.append([f"  {r['code']} {r['name']}", f"{net:>15,.0f}"])
        tdata.append([total_label, f"{float(total_val):>15,.0f}"])
        t = Table(tdata, colWidths=col_w)
        t.setStyle(hstyle)
        t.setStyle(TableStyle([
            ('FONTNAME',   (0, 0), (-1, -1), _FONT_NAME),
            ('ALIGN',      (1, 1), (1, -1),  'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eff6ff')),
        ]))
        return t

    elements.append(_section('자  산', data['assets'],
                              '자산 합계', data['total_assets']))
    elements.append(Spacer(1, 4 * mm))

    # 부채: credit - debit
    liab_rows = [{'code': r['code'], 'name': r['name'],
                  'debit': r['credit'], 'credit': r['debit']}
                 for r in data['liabilities']]
    elements.append(_section('부  채', liab_rows,
                              '부채 합계', data['total_liabilities']))
    elements.append(Spacer(1, 4 * mm))

    eq_rows = [{'code': r['code'], 'name': r['name'],
                'debit': r['credit'], 'credit': r['debit']}
               for r in data['equity']]
    elements.append(_section('자  본', eq_rows,
                              '자본 합계', data['total_equity']))
    elements.append(Spacer(1, 6 * mm))

    balanced = abs(float(data['total_assets']) -
                   float(data['total_liabilities'] + data['total_equity'])) < 0.01
    chk_color = colors.HexColor('#16a34a') if balanced else colors.HexColor('#dc2626')
    chk_label = '✓ 대차 균형' if balanced else '✗ 대차 불일치'
    chk_table = Table([[chk_label, '']], colWidths=col_w)
    chk_table.setStyle(TableStyle([
        ('FONTNAME',   (0, 0), (-1, -1), _FONT_NAME),
        ('FONTSIZE',   (0, 0), (0, 0),   10),
        ('TEXTCOLOR',  (0, 0), (0, 0),   chk_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(chk_table)
    return elements


# ─────────────────────────────────────────────────────────────
# 급여명세서 PDF  GET /api/reports/payroll/{pk}/pdf/
# ─────────────────────────────────────────────────────────────

class PayrollSlipPDF(APIView):
    """급여명세서 PDF 출력."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from scm_hr.models import Payroll
        try:
            payroll = Payroll.objects.select_related(
                'employee__dept', 'employee'
            ).get(pk=pk, company=request.user.company)
        except Payroll.DoesNotExist:
            return Response({'detail': '급여 기록을 찾을 수 없습니다.'}, status=404)

        title_s, sub_s, label_s = make_styles()
        elements = []

        emp = payroll.employee
        period = f'{payroll.pay_year}년 {payroll.pay_month}월'

        elements.append(Paragraph('급  여  명  세  서', title_s))
        elements.append(Paragraph(f'{period}  |  {request.user.company}', sub_s))
        elements.append(Spacer(1, 5 * mm))

        # 직원 정보
        emp_data = [
            ['성명',   emp.name,           '사원번호', emp.emp_code],
            ['부서',   str(emp.dept) if emp.dept else '-', '직위', emp.position or '-'],
            ['고용형태', emp.employment_type, '입사일', str(emp.hire_date)],
        ]
        emp_table = Table(emp_data, colWidths=[25 * mm, 60 * mm, 25 * mm, 60 * mm])
        emp_table.setStyle(TableStyle([
            ('FONTNAME',    (0, 0), (-1, -1), _FONT_NAME),
            ('FONTSIZE',    (0, 0), (-1, -1), 9),
            ('BACKGROUND',  (0, 0), (0, -1),  colors.HexColor('#dbeafe')),
            ('BACKGROUND',  (2, 0), (2, -1),  colors.HexColor('#dbeafe')),
            ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor('#bfdbfe')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ]))
        elements.append(emp_table)
        elements.append(Spacer(1, 5 * mm))

        # 지급 항목 / 공제 항목 나란히
        pay_rows = [
            ['지급 항목', '금액(원)', '공제 항목', '금액(원)'],
            ['기본급',           f"{float(payroll.base_salary):>12,.0f}",
             '국민연금',         f"{float(payroll.national_pension):>12,.0f}"],
            ['초과근무수당',     f"{float(payroll.overtime_pay):>12,.0f}",
             '건강보험',         f"{float(payroll.health_insurance):>12,.0f}"],
            ['상여금',           f"{float(payroll.bonus):>12,.0f}",
             '고용보험',         f"{float(payroll.employment_insurance):>12,.0f}"],
            ['',                 '',
             '소득세',           f"{float(payroll.income_tax):>12,.0f}"],
            ['지급 합계',        f"{float(payroll.gross_pay):>12,.0f}",
             '공제 합계',        f"{float(payroll.total_deduction):>12,.0f}"],
        ]
        pay_table = Table(pay_rows, colWidths=[40 * mm, 45 * mm, 40 * mm, 45 * mm])
        pay_table.setStyle(TableStyle([
            ('FONTNAME',    (0, 0), (-1, -1), _FONT_NAME),
            ('FONTSIZE',    (0, 0), (-1, -1), 9),
            ('BACKGROUND',  (0, 0), (-1, 0),  colors.HexColor('#1e40af')),
            ('TEXTCOLOR',   (0, 0), (-1, 0),  colors.white),
            ('BACKGROUND',  (0, -1), (-1, -1), colors.HexColor('#eff6ff')),
            ('ALIGN',       (1, 1), (1, -1),  'RIGHT'),
            ('ALIGN',       (3, 1), (3, -1),  'RIGHT'),
            ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2),
             [colors.white, colors.HexColor('#f8fafc')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ]))
        elements.append(pay_table)
        elements.append(Spacer(1, 6 * mm))

        # 실수령액
        np_color = colors.HexColor('#1e40af')
        np_table = Table([
            ['실  수  령  액', f"{float(payroll.net_pay):>15,.0f}  원"]
        ], colWidths=[80 * mm, 90 * mm])
        np_table.setStyle(TableStyle([
            ('FONTNAME',   (0, 0), (-1, -1), _FONT_NAME),
            ('FONTSIZE',   (0, 0), (0, 0),   12),
            ('FONTSIZE',   (1, 0), (1, 0),   13),
            ('TEXTCOLOR',  (1, 0), (1, 0),   np_color),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eff6ff')),
            ('ALIGN',      (1, 0), (1, 0),   'RIGHT'),
            ('GRID',       (0, 0), (-1, -1), 1.0, colors.HexColor('#bfdbfe')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ]))
        elements.append(np_table)
        elements.append(Spacer(1, 5 * mm))

        payment_date = str(payroll.payment_date) if payroll.payment_date else '미정'
        elements.append(Paragraph(f'지급예정일: {payment_date}', label_s))
        elements.append(Paragraph(
            f'출력일시: {timezone.now().strftime("%Y-%m-%d %H:%M")}  |  {request.user.company}', label_s
        ))

        pdf_bytes = build_pdf(elements)
        fname = f'Payroll_{payroll.payroll_number}.pdf'
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp
