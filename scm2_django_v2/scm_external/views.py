import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ExternalAPIConfig
from .serializers import ExternalAPIConfigSerializer
from .services import get_service

logger = logging.getLogger(__name__)


class ExternalAPIConfigViewSet(viewsets.ModelViewSet):
    """
    관리자 전용 – 외부 API 설정 CRUD + 연결 테스트.
    """
    serializer_class = ExternalAPIConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExternalAPIConfig.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    # ── GET /api/external/configs/active-features/ ──────────────
    @action(detail=False, methods=['get'], url_path='active-features')
    def active_features(self, request):
        """
        Returns list of feature_types that have at least one active config.
        Used by frontend to conditionally render widgets.
        """
        active = (
            ExternalAPIConfig.objects
            .filter(company=request.user.company, is_active=True)
            .values_list('feature_type', flat=True)
            .distinct()
        )
        return Response({'active_features': list(active)})

    # ── POST /api/external/configs/{id}/test/ ───────────────────
    @action(detail=True, methods=['post'], url_path='test')
    def test_connection(self, request, pk=None):
        """Test the API connection and update last_test fields."""
        config = self.get_object()
        try:
            svc = get_service(config.provider)
            ok, msg = svc.test_connection(config)
        except Exception as e:
            ok, msg = False, str(e)

        config.last_tested_at = timezone.now()
        config.last_test_ok   = ok
        config.last_test_msg  = msg
        config.save(update_fields=['last_tested_at', 'last_test_ok', 'last_test_msg'])

        return Response({
            'ok': ok,
            'message': msg,
            'last_tested_at': config.last_tested_at,
        }, status=status.HTTP_200_OK)


class RealTimeProxyViewSet(viewsets.ViewSet):
    """
    실시간 데이터 프록시 – 인증된 사용자 누구나 사용 가능.
    백엔드가 외부 API를 호출하여 결과를 반환 (API 키 노출 방지).
    """
    permission_classes = [IsAuthenticated]

    def _get_active_config(self, company, feature_type, provider=None):
        qs = ExternalAPIConfig.objects.filter(
            company=company, feature_type=feature_type, is_active=True
        )
        if provider:
            qs = qs.filter(provider=provider)
        return qs.first()

    # ── GET /api/external/exchange-rates/ ───────────────────────
    @action(detail=False, methods=['get'], url_path='exchange-rates')
    def exchange_rates(self, request):
        provider = request.query_params.get('provider')
        config = self._get_active_config(request.user.company, 'exchange_rate', provider)
        if not config:
            # Fall back to open_er which needs no key
            from .models import ExternalAPIConfig as Cfg
            # Try to find any active exchange_rate config
            config = ExternalAPIConfig.objects.filter(
                company=request.user.company, feature_type='exchange_rate'
            ).first()
            if not config:
                return Response({'error': '환율 API가 등록되지 않았습니다.'}, status=404)

        try:
            svc = get_service(config.provider)
            base = request.query_params.get('base', 'USD')
            data = svc.fetch_data(config, base=base)
            return Response(data)
        except Exception as e:
            logger.warning('exchange_rates proxy error: %s', e)
            return Response({'error': str(e)}, status=502)

    # ── GET /api/external/track-delivery/ ───────────────────────
    @action(detail=False, methods=['get'], url_path='track-delivery')
    def track_delivery(self, request):
        tracking_number = request.query_params.get('tracking_number')
        carrier_code    = request.query_params.get('carrier_code', '')
        provider        = request.query_params.get('provider')
        if not tracking_number:
            return Response({'error': '운송장 번호(tracking_number)가 필요합니다.'}, status=400)

        config = self._get_active_config(request.user.company, 'delivery_tracking', provider)
        if not config:
            return Response({'error': '배송추적 API가 등록되지 않았습니다.'}, status=404)

        try:
            svc = get_service(config.provider)
            data = svc.fetch_data(config, tracking_number=tracking_number, carrier_code=carrier_code)
            return Response(data)
        except Exception as e:
            logger.warning('track_delivery proxy error: %s', e)
            return Response({'error': str(e)}, status=502)

    # ── GET /api/external/track-customs/ ────────────────────────
    @action(detail=False, methods=['get'], url_path='track-customs')
    def track_customs(self, request):
        bl_number = request.query_params.get('bl_number')
        if not bl_number:
            return Response({'error': 'B/L 번호(bl_number)가 필요합니다.'}, status=400)

        config = self._get_active_config(request.user.company, 'customs_tracking')
        if not config:
            return Response({'error': '통관조회 API가 등록되지 않았습니다.'}, status=404)

        try:
            svc = get_service(config.provider)
            data = svc.fetch_data(config, bl_number=bl_number)
            return Response(data)
        except Exception as e:
            logger.warning('track_customs proxy error: %s', e)
            return Response({'error': str(e)}, status=502)

    # ── GET /api/external/track-vessel/ ─────────────────────────
    @action(detail=False, methods=['get'], url_path='track-vessel')
    def track_vessel(self, request):
        vessel_name = request.query_params.get('vessel_name')
        mmsi        = request.query_params.get('mmsi')
        imo         = request.query_params.get('imo')

        if not any([vessel_name, mmsi, imo]):
            return Response({'error': 'vessel_name, mmsi, imo 중 하나가 필요합니다.'}, status=400)

        config = self._get_active_config(request.user.company, 'vessel_tracking')
        if not config:
            return Response({'error': '선박추적 API가 등록되지 않았습니다.'}, status=404)

        try:
            svc = get_service(config.provider)
            data = svc.fetch_data(config, vessel_name=vessel_name, mmsi=mmsi, imo=imo)
            return Response(data)
        except Exception as e:
            logger.warning('track_vessel proxy error: %s', e)
            return Response({'error': str(e)}, status=502)

    # ── GET /api/external/carrier-list/ ─────────────────────────
    @action(detail=False, methods=['get'], url_path='carrier-list')
    def carrier_list(self, request):
        """스윗트래커 택배사 목록 조회."""
        config = self._get_active_config(request.user.company, 'delivery_tracking', 'sweettracker')
        if not config:
            return Response({'error': '스윗트래커 API가 등록되지 않았습니다.'}, status=404)
        try:
            from .services import SweetTrackerService
            carriers = SweetTrackerService().get_carrier_list(config)
            return Response({'carriers': carriers})
        except Exception as e:
            return Response({'error': str(e)}, status=502)
