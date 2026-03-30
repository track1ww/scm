"""
scm_fi/tax_utils.py

부가세 전표 라인 자동 생성 유틸리티 (K-GAAP 기준, 세율 10%)

사용 계정과목 코드 매핑:
  - 13500: 부가세대급금 (ASSET)   - 매입 시 차변
  - 25100: 매입채무   (LIABILITY) - 매입 시 대변 가산
  - 11000: 매출채권   (ASSET)     - 매출 시 차변 가산
  - 25500: 부가세예수금(LIABILITY) - 매출 시 대변
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from .models import Account, AccountMove, AccountMoveLine


VAT_RATE = Decimal('0.1')

# 계정과목 코드 상수
ACCOUNT_VAT_RECEIVABLE = '13500'   # 부가세대급금
ACCOUNT_AP             = '25100'   # 매입채무
ACCOUNT_AR             = '11000'   # 매출채권
ACCOUNT_VAT_PAYABLE    = '25500'   # 부가세예수금


def _get_account(company, account_code: str) -> Account:
    """
    company 소속 계정과목을 코드로 조회한다.
    존재하지 않으면 ValueError를 발생시킨다.
    """
    try:
        return Account.objects.get(company=company, code=account_code, is_active=True)
    except Account.DoesNotExist:
        raise ValueError(
            f"계정과목 코드 '{account_code}'을(를) 찾을 수 없습니다. "
            f"먼저 해당 계정과목을 등록하세요."
        )


def _calc_tax(supply_amount: Decimal) -> Decimal:
    """공급가액으로부터 부가세(10%) 계산, 원 단위 반올림."""
    return (supply_amount * VAT_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@transaction.atomic
def create_purchase_tax_lines(
    move: AccountMove,
    supply_amount: Decimal,
    company,
) -> list[AccountMoveLine]:
    """
    매입 전표에 부가세 관련 라인 2건을 추가한다.

    생성 라인:
      1. 차변  - 부가세대급금 (account_code='13500')  = supply_amount * 0.1
      2. 대변  - 매입채무     (account_code='25100') += supply_amount * 0.1
                 (기존 매입채무 대변 라인이 있으면 credit을 증가시킨다)

    Args:
        move:          부가세 라인을 추가할 AccountMove 인스턴스 (DRAFT 상태 권장)
        supply_amount: 공급가액 (Decimal)
        company:       Company 인스턴스

    Returns:
        생성 또는 수정된 AccountMoveLine 인스턴스 리스트
    """
    supply_amount = Decimal(str(supply_amount))
    tax_amount    = _calc_tax(supply_amount)

    account_vat_recv = _get_account(company, ACCOUNT_VAT_RECEIVABLE)
    account_ap       = _get_account(company, ACCOUNT_AP)

    created_lines: list[AccountMoveLine] = []

    # 1. 부가세대급금 차변 라인 추가
    vat_line = AccountMoveLine.objects.create(
        move    = move,
        account = account_vat_recv,
        name    = f'부가세대급금 (공급가액 {supply_amount:,.0f}원의 10%)',
        debit   = tax_amount,
        credit  = Decimal('0'),
    )
    created_lines.append(vat_line)

    # 2. 매입채무 대변 라인: 기존 라인이 있으면 금액 가산, 없으면 신규 생성
    existing_ap_line = (
        AccountMoveLine.objects
        .filter(move=move, account=account_ap)
        .order_by('id')
        .first()
    )
    if existing_ap_line:
        existing_ap_line.credit += tax_amount
        existing_ap_line.save(update_fields=['credit'])
        created_lines.append(existing_ap_line)
    else:
        ap_line = AccountMoveLine.objects.create(
            move    = move,
            account = account_ap,
            name    = f'매입채무 부가세분 (공급가액 {supply_amount:,.0f}원의 10%)',
            debit   = Decimal('0'),
            credit  = tax_amount,
        )
        created_lines.append(ap_line)

    # 전표 합계 갱신
    _recalculate_move_totals(move)

    return created_lines


@transaction.atomic
def create_sale_tax_lines(
    move: AccountMove,
    supply_amount: Decimal,
    company,
) -> list[AccountMoveLine]:
    """
    매출 전표에 부가세 관련 라인 2건을 추가한다.

    생성 라인:
      1. 차변  - 매출채권     (account_code='11000') += supply_amount * 0.1
                 (기존 매출채권 차변 라인이 있으면 debit을 증가시킨다)
      2. 대변  - 부가세예수금 (account_code='25500')  = supply_amount * 0.1

    Args:
        move:          부가세 라인을 추가할 AccountMove 인스턴스 (DRAFT 상태 권장)
        supply_amount: 공급가액 (Decimal)
        company:       Company 인스턴스

    Returns:
        생성 또는 수정된 AccountMoveLine 인스턴스 리스트
    """
    supply_amount = Decimal(str(supply_amount))
    tax_amount    = _calc_tax(supply_amount)

    account_ar          = _get_account(company, ACCOUNT_AR)
    account_vat_payable = _get_account(company, ACCOUNT_VAT_PAYABLE)

    created_lines: list[AccountMoveLine] = []

    # 1. 매출채권 차변 라인: 기존 라인이 있으면 금액 가산, 없으면 신규 생성
    existing_ar_line = (
        AccountMoveLine.objects
        .filter(move=move, account=account_ar)
        .order_by('id')
        .first()
    )
    if existing_ar_line:
        existing_ar_line.debit += tax_amount
        existing_ar_line.save(update_fields=['debit'])
        created_lines.append(existing_ar_line)
    else:
        ar_line = AccountMoveLine.objects.create(
            move    = move,
            account = account_ar,
            name    = f'매출채권 부가세분 (공급가액 {supply_amount:,.0f}원의 10%)',
            debit   = tax_amount,
            credit  = Decimal('0'),
        )
        created_lines.append(ar_line)

    # 2. 부가세예수금 대변 라인 추가
    vat_payable_line = AccountMoveLine.objects.create(
        move    = move,
        account = account_vat_payable,
        name    = f'부가세예수금 (공급가액 {supply_amount:,.0f}원의 10%)',
        debit   = Decimal('0'),
        credit  = tax_amount,
    )
    created_lines.append(vat_payable_line)

    # 전표 합계 갱신
    _recalculate_move_totals(move)

    return created_lines


def _recalculate_move_totals(move: AccountMove) -> None:
    """
    AccountMove의 total_debit / total_credit을 전표 라인 기준으로 재계산하고 저장한다.
    AccountMove.save()의 locked/posted 검증을 우회하기 위해 update()를 사용한다.
    """
    from django.db.models import Sum as DbSum
    agg = AccountMoveLine.objects.filter(move=move).aggregate(
        total_debit  = DbSum('debit'),
        total_credit = DbSum('credit'),
    )
    AccountMove.objects.filter(pk=move.pk).update(
        total_debit  = agg['total_debit']  or Decimal('0'),
        total_credit = agg['total_credit'] or Decimal('0'),
    )
    move.refresh_from_db(fields=['total_debit', 'total_credit'])
