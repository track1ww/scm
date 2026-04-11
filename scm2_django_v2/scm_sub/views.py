import logging
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import SubcontractOrder, SubcontractOrderLine, SubcontractMaterial, SubcontractReceipt
from .serializers import (
    SubcontractOrderSerializer,
    SubcontractOrderLineSerializer,
    SubcontractMaterialSerializer,
    SubcontractReceiptSerializer,
)

logger = logging.getLogger(__name__)


def _gen_order_number(company):
    today = date.today().strftime('%Y%m%d')
    prefix = f'SUB-{today}-'
    count = SubcontractOrder.objects.filter(company=company, order_number__startswith=prefix).count()
    return f'{prefix}{count + 1:03d}'


def _gen_receipt_number(company):
    today = date.today().strftime('%Y%m%d')
    prefix = f'SR-{today}-'
    count = SubcontractReceipt.objects.filter(company=company, receipt_number__startswith=prefix).count()
    return f'{prefix}{count + 1:03d}'


class SubcontractOrderViewSet(viewsets.ModelViewSet):
    serializer_class   = SubcontractOrderSerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['order_number', 'supplier__name', 'work_description']
    filterset_fields   = ['status', 'supplier']

    def get_queryset(self):
        return SubcontractOrder.objects.filter(
            company=self.request.user.company
        ).select_related('supplier', 'issued_by').prefetch_related('lines', 'materials')

    def perform_create(self, serializer):
        company = self.request.user.company
        serializer.save(
            company=company,
            order_number=_gen_order_number(company),
        )

    # ── POST /api/sub/orders/{id}/issue/ ─────────────────────
    @action(detail=True, methods=['post'], url_path='issue')
    def issue(self, request, pk=None):
        """발주 확정 + 외주업체 이메일 발송"""
        order = self.get_object()
        if order.status != 'draft':
            return Response({'error': '초안 상태에서만 발주확정 가능합니다.'}, status=400)

        with transaction.atomic():
            order.status    = 'issued'
            order.issued_at = timezone.now()
            order.issued_by = request.user
            order.save(update_fields=['status', 'issued_at', 'issued_by'])

        # 이메일 발송 (DB 커밋 후)
        email_sent = False
        email_error = ''
        supplier_email = order.supplier.email if order.supplier else ''
        if supplier_email:
            try:
                _send_issue_email(order, supplier_email)
                email_sent = True
            except Exception as e:
                logger.warning('외주 발주 이메일 발송 실패: %s', e)
                email_error = str(e)

        return Response({
            'ok': True,
            'order_number': order.order_number,
            'status': order.status,
            'email_sent': email_sent,
            'email_error': email_error,
            'supplier_email': supplier_email,
        })

    # ── POST /api/sub/orders/{id}/transition/ ────────────────
    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        """상태 전이: issued→in_progress, in_progress→completed, 등"""
        order  = self.get_object()
        new_st = request.data.get('status')
        ALLOWED = {
            'issued':      'in_progress',
            'in_progress': 'completed',
            'completed':   'received',
            'received':    'closed',
        }
        if new_st != ALLOWED.get(order.status):
            return Response(
                {'error': f'{order.get_status_display()} 상태에서 {new_st}(으)로 전환할 수 없습니다.'},
                status=400
            )
        if order.status in ('closed', 'received'):
            return Response({'error': '이미 완료된 발주서입니다.'}, status=400)

        order.status = new_st
        order.save(update_fields=['status'])
        return Response({'ok': True, 'status': order.status})

    # ── POST /api/sub/orders/{id}/cancel/ ────────────────────
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status in ('received', 'closed'):
            return Response({'error': '입고완료/마감 발주서는 취소할 수 없습니다.'}, status=400)
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return Response({'ok': True})


class SubcontractOrderLineViewSet(viewsets.ModelViewSet):
    serializer_class   = SubcontractOrderLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SubcontractOrderLine.objects.filter(
            order__company=self.request.user.company
        )
        order_id = self.request.query_params.get('order')
        if order_id:
            qs = qs.filter(order_id=order_id)
        return qs

    def perform_create(self, serializer):
        serializer.save()


class SubcontractMaterialViewSet(viewsets.ModelViewSet):
    serializer_class   = SubcontractMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SubcontractMaterial.objects.filter(
            order__company=self.request.user.company
        ).select_related('material')
        order_id = self.request.query_params.get('order')
        if order_id:
            qs = qs.filter(order_id=order_id)
        return qs


class SubcontractReceiptViewSet(viewsets.ModelViewSet):
    serializer_class   = SubcontractReceiptSerializer
    permission_classes = [IsAuthenticated]
    search_fields      = ['receipt_number', 'item_name', 'order__order_number']
    filterset_fields   = ['order']

    def get_queryset(self):
        return SubcontractReceipt.objects.filter(
            company=self.request.user.company
        ).select_related('order__supplier')

    def perform_create(self, serializer):
        company = self.request.user.company
        receipt = serializer.save(
            company=company,
            receipt_number=_gen_receipt_number(company),
        )
        # 연결된 발주서 상태 completed → received 자동 전환
        if receipt.order and receipt.order.status == 'completed':
            receipt.order.status = 'received'
            receipt.order.save(update_fields=['status'])


# ─── 이메일 발송 헬퍼 ─────────────────────────────────────────
def _send_issue_email(order, to_email):
    lines_text = '\n'.join(
        f'  {l.line_no}. {l.item_name}  {l.quantity}{l.unit}  단가 {l.unit_price:,.0f} {order.currency}'
        for l in order.lines.all()
    )
    materials_text = ''
    if order.materials.exists():
        materials_text = '\n[사급 자재]\n' + '\n'.join(
            f'  - {m.material_name}  {m.quantity}{m.unit}'
            for m in order.materials.all()
        )

    body = f"""외주 발주서가 확정되었습니다.

발주번호 : {order.order_number}
발주일   : {order.order_date}
납기일   : {order.due_date or '미정'}
작업내용 : {order.work_description}

[발주 라인]
{lines_text or '  (없음)'}
{materials_text}

총 발주금액 : {order.total_amount:,.0f} {order.currency}

비고 : {order.note or '-'}

---
문의사항이 있으시면 회신해 주세요.
"""
    send_mail(
        subject=f'[외주발주] {order.order_number} 발주 확정 안내',
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@scm2.local'),
        recipient_list=[to_email],
        fail_silently=False,
    )
