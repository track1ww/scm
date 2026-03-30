"""
세금계산서 (Tax Invoice) 유틸리티

부가가치세(VAT) 전표 분리 로직:
- 공급가액 + VAT 10% 를 자동 분리
- AccountMove / AccountMoveLine 자동 생성
- 매입/매출 세금계산서 양방향 지원
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from django.db import transaction

# 한국 표준 부가세율
VAT_RATE = Decimal('0.10')


def split_vat(total_with_vat: Decimal) -> dict:
    """
    VAT 포함 금액에서 공급가액과 부가세를 분리한다.

    Args:
        total_with_vat: VAT 포함 총액

    Returns:
        {
            'supply_amount': 공급가액 (원),
            'vat_amount':    부가세액 (원),
            'total':         총액 (검증용),
        }
    """
    total = Decimal(str(total_with_vat))
    supply = (total / (1 + VAT_RATE)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    vat = total - supply
    return {
        'supply_amount': supply,
        'vat_amount':    vat,
        'total':         total,
    }


def calculate_vat(supply_amount: Decimal) -> dict:
    """
    공급가액으로부터 부가세와 총액을 계산한다.

    Args:
        supply_amount: 공급가액

    Returns:
        {
            'supply_amount': 공급가액,
            'vat_amount':    부가세액,
            'total':         합계금액,
        }
    """
    supply = Decimal(str(supply_amount))
    vat = (supply * VAT_RATE).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return {
        'supply_amount': supply,
        'vat_amount':    vat,
        'total':         supply + vat,
    }


def build_tax_invoice_lines(
    move_type: str,
    supply_amount: Decimal,
    vat_amount: Decimal,
    account_codes: dict,
) -> list[dict]:
    """
    세금계산서를 위한 전표 라인을 생성한다.

    Args:
        move_type: 'SALE' (매출) 또는 'PURCHASE' (매입)
        supply_amount: 공급가액
        vat_amount: 부가세액
        account_codes: {
            'revenue_or_expense': 매출/매입 계정코드,
            'receivable_or_payable': 매출채권/매입채무 계정코드,
            'vat': 부가세 대급금/예수금 계정코드,
        }

    Returns:
        전표 라인 딕셔너리 리스트 (AccountMoveLine 생성에 사용)
    """
    supply = Decimal(str(supply_amount))
    vat = Decimal(str(vat_amount))
    total = supply + vat

    if move_type == 'SALE':
        # 매출 세금계산서: 차변=매출채권(total), 대변=매출(supply)+부가세예수금(vat)
        return [
            {
                'account_code': account_codes['receivable_or_payable'],
                'name': '매출채권',
                'debit': total,
                'credit': Decimal('0'),
            },
            {
                'account_code': account_codes['revenue_or_expense'],
                'name': '매출',
                'debit': Decimal('0'),
                'credit': supply,
            },
            {
                'account_code': account_codes['vat'],
                'name': '부가세 예수금',
                'debit': Decimal('0'),
                'credit': vat,
            },
        ]
    elif move_type == 'PURCHASE':
        # 매입 세금계산서: 차변=매입(supply)+부가세대급금(vat), 대변=매입채무(total)
        return [
            {
                'account_code': account_codes['revenue_or_expense'],
                'name': '매입',
                'debit': supply,
                'credit': Decimal('0'),
            },
            {
                'account_code': account_codes['vat'],
                'name': '부가세 대급금',
                'debit': vat,
                'credit': Decimal('0'),
            },
            {
                'account_code': account_codes['receivable_or_payable'],
                'name': '매입채무',
                'debit': Decimal('0'),
                'credit': total,
            },
        ]
    else:
        raise ValueError(f"지원하지 않는 move_type: {move_type}. 'SALE' 또는 'PURCHASE'만 가능.")


def create_tax_invoice_move(
    company,
    move_type: str,
    supply_amount: Decimal,
    ref: str = '',
    posting_date: date = None,
    account_codes: dict = None,
    created_by: str = '',
):
    """
    세금계산서 전표(AccountMove + Lines)를 한번에 생성한다.

    Args:
        company: Company 인스턴스
        move_type: 'SALE' 또는 'PURCHASE'
        supply_amount: 공급가액
        ref: 참조 (예: 세금계산서 번호)
        posting_date: 전기일 (기본: 오늘)
        account_codes: 계정코드 딕셔너리 (None이면 기본값 사용)
        created_by: 작성자

    Returns:
        생성된 AccountMove 인스턴스
    """
    from .models import Account, AccountMove, AccountMoveLine

    if posting_date is None:
        posting_date = date.today()

    vat_info = calculate_vat(supply_amount)

    # 기본 계정코드 (한국 K-GAAP 표준)
    if account_codes is None:
        if move_type == 'SALE':
            account_codes = {
                'revenue_or_expense': '4010',       # 상품매출
                'receivable_or_payable': '1080',    # 외상매출금
                'vat': '2150',                       # 부가세 예수금
            }
        else:
            account_codes = {
                'revenue_or_expense': '5010',       # 상품매입
                'receivable_or_payable': '2010',    # 외상매입금
                'vat': '1350',                       # 부가세 대급금
            }

    lines_data = build_tax_invoice_lines(
        move_type, vat_info['supply_amount'], vat_info['vat_amount'], account_codes
    )

    # 전표번호 생성
    prefix = 'SI' if move_type == 'SALE' else 'PI'
    last = AccountMove.objects.filter(
        company=company, move_number__startswith=prefix
    ).order_by('-move_number').first()

    if last:
        seq = int(last.move_number[len(prefix):]) + 1
    else:
        seq = 1
    move_number = f"{prefix}{seq:06d}"

    with transaction.atomic():
        move = AccountMove.objects.create(
            company=company,
            move_number=move_number,
            move_type=move_type,
            posting_date=posting_date,
            ref=ref,
            state='DRAFT',
            total_debit=vat_info['total'],
            total_credit=vat_info['total'],
            created_by=created_by,
        )

        move_lines = []
        for line in lines_data:
            account = Account.objects.get(company=company, code=line['account_code'])
            move_lines.append(AccountMoveLine(
                move=move,
                account=account,
                name=line['name'],
                debit=line['debit'],
                credit=line['credit'],
            ))
        AccountMoveLine.objects.bulk_create(move_lines)

    return move
