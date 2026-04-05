"""
HR → FI 자동전표 생성 (Cross-module integration signal).

Signal overview
---------------
hr_payroll_confirmed : Payroll '확정' 전환 시 → FI 인건비전표 자동 생성

FI 자동전표 계정과목 (K-GAAP)
-------------------------------
  5200  급여        EXPENSE
  2530  미지급급여  LIABILITY
"""
import logging

from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# K-GAAP 인건비 계정과목
# ---------------------------------------------------------------------------

_HR_ACCOUNTS = {
    'salary_expense': ('5200', '급여',       'EXPENSE'),
    'accrued_salary': ('2530', '미지급급여', 'LIABILITY'),
}


def _get_or_create_account(company, key):
    """K-GAAP 표준 계정과목을 가져오거나 없으면 자동 생성."""
    from scm_fi.models import Account

    code, name, atype = _HR_ACCOUNTS[key]
    acc, _ = Account.objects.get_or_create(
        company=company,
        code=code,
        defaults={'name': name, 'account_type': atype, 'is_active': True},
    )
    return acc


# ---------------------------------------------------------------------------
# HR 급여 확정 → FI 인건비전표
# ---------------------------------------------------------------------------

@receiver(pre_save, sender='scm_hr.Payroll')
def hr_payroll_confirmed(sender, instance, **kwargs):
    """
    Payroll → '확정' 전환 시:
      FI 인건비전표: DR 급여(5200) / CR 미지급급여(2530)  (금액 = gross_pay)
    """
    # 신규 생성은 무시
    if not instance.pk:
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    # 상태 전이가 → '확정' 인 경우에만 처리
    if old.state == '확정' or instance.state != '확정':
        return

    try:
        with transaction.atomic():
            _auto_post_payroll(instance)
    except Exception as e:
        logger.warning('HR→FI auto-post failed: %s', e, exc_info=True)


# ---------------------------------------------------------------------------
# FI 자동전표 생성 헬퍼
# ---------------------------------------------------------------------------

def _auto_post_payroll(payroll):
    """
    급여 확정 인건비 전표 생성.

        DR 급여(5200)        gross_pay
        CR 미지급급여(2530)  gross_pay
    """
    from scm_fi.models import AccountMove, AccountMoveLine

    move_number = f'AUTO-HR-{payroll.payroll_number}'

    # 중복 방지
    if AccountMove.objects.filter(
        company=payroll.company,
        move_number=move_number,
    ).exists():
        return

    amount = float(payroll.gross_pay)
    if amount <= 0:
        return

    today = timezone.localdate()
    posting_date = payroll.payment_date if payroll.payment_date else today

    acc_salary  = _get_or_create_account(payroll.company, 'salary_expense')
    acc_accrued = _get_or_create_account(payroll.company, 'accrued_salary')

    employee_name = payroll.employee.name if payroll.employee_id else ''
    label = (
        f'자동전기-인건비: {employee_name} '
        f'{payroll.pay_year}-{payroll.pay_month:02d}'
    )

    move = AccountMove.objects.create(
        company=payroll.company,
        move_number=move_number,
        move_type='ENTRY',
        posting_date=posting_date,
        ref=payroll.payroll_number,
        state='DRAFT',
        total_debit=amount,
        total_credit=amount,
        created_by='system',
    )

    AccountMoveLine.objects.create(
        move=move,
        account=acc_salary,
        name=label,
        debit=amount,
        credit=0,
    )
    AccountMoveLine.objects.create(
        move=move,
        account=acc_accrued,
        name=label,
        debit=0,
        credit=amount,
    )
