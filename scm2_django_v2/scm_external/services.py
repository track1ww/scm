"""
External API service layer.

Each service class has:
  - test_connection(config: ExternalAPIConfig) -> (ok: bool, message: str)
  - fetch_data(config: ExternalAPIConfig, **kwargs) -> dict
"""
import json
import logging
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)

TIMEOUT = 8  # seconds


def _http_get(url, headers=None, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


# ─────────────────────────────────────────────────────────────
# 1. Exchange Rate Services
# ─────────────────────────────────────────────────────────────

class OpenERService:
    """
    Open Exchange Rates – free, no API key required.
    https://open.er-api.com/v6/latest/{base}
    Returns rates vs USD by default; we convert to KRW-centric.
    """
    BASE_URL = 'https://open.er-api.com/v6/latest'

    def test_connection(self, config):
        try:
            data = _http_get(f'{self.BASE_URL}/USD')
            if data.get('result') == 'success':
                return True, '연결 성공'
            return False, data.get('error-type', '알 수 없는 오류')
        except Exception as e:
            return False, str(e)

    def fetch_data(self, config, base='USD', **kwargs):
        """Returns rates relative to `base` currency."""
        url = f'{self.BASE_URL}/{base}'
        data = _http_get(url)
        rates = data.get('rates', {})
        # Build KRW-focused result
        currencies = config.extra_config.get('currencies', ['KRW', 'USD', 'EUR', 'JPY', 'CNY', 'GBP'])
        result = {
            'base': base,
            'provider': 'open_er',
            'time_last_update': data.get('time_last_update_utc', ''),
            'rates': {c: rates[c] for c in currencies if c in rates},
        }
        # Add KRW-based rates (how many KRW per 1 foreign)
        if 'KRW' in rates and base == 'USD':
            krw_per_usd = rates.get('KRW', 1)
            result['krw_rates'] = {
                c: round(krw_per_usd / rates[c], 2) if rates.get(c) else None
                for c in currencies if c != 'KRW' and rates.get(c)
            }
            result['krw_rates']['KRW'] = 1
        return result


class EcosService:
    """
    한국은행 ECOS OpenAPI.
    Requires API key from https://ecos.bok.or.kr/
    Stat code 731Y001 = 주요국 통화의 대미달러 환율
    """
    BASE_URL = 'https://ecos.bok.or.kr/api'

    def test_connection(self, config):
        if not config.api_key:
            return False, 'API 키가 없습니다.'
        try:
            from datetime import date
            today = date.today().strftime('%Y%m%d')
            url = (
                f"{self.BASE_URL}/StatisticSearch/{config.api_key}/json/kr"
                f"/1/1/731Y001/DD/{today}/{today}/0000001"
            )
            data = _http_get(url)
            if 'StatisticSearch' in data:
                return True, '연결 성공 (한국은행 ECOS)'
            err = data.get('RESULT', {})
            return False, err.get('MESSAGE', str(data))
        except Exception as e:
            return False, str(e)

    def fetch_data(self, config, **kwargs):
        from datetime import date, timedelta
        end   = date.today().strftime('%Y%m%d')
        start = (date.today() - timedelta(days=7)).strftime('%Y%m%d')
        url = (
            f"{self.BASE_URL}/StatisticSearch/{config.api_key}/json/kr"
            f"/1/100/731Y001/DD/{start}/{end}"
        )
        data = _http_get(url)
        rows = data.get('StatisticSearch', {}).get('row', [])
        rates = {}
        for row in rows:
            if row.get('TIME') == end or not rates.get(row.get('ITEM_CODE1')):
                rates[row.get('ITEM_CODE1', '')] = {
                    'currency': row.get('ITEM_NAME1', ''),
                    'rate': row.get('DATA_VALUE'),
                    'date': row.get('TIME'),
                }
        return {'provider': 'ecos', 'rates': list(rates.values())}


# ─────────────────────────────────────────────────────────────
# 2. Delivery Tracking Services
# ─────────────────────────────────────────────────────────────

class SweetTrackerService:
    """
    스윗트래커 배송추적 API.
    https://info.sweettracker.co.kr/apidoc
    """
    BASE_URL = 'https://info.sweettracker.co.kr'

    def test_connection(self, config):
        if not config.api_key:
            return False, 'API 키가 없습니다.'
        try:
            url = f'{self.BASE_URL}/api/v1/companylist?t_key={config.api_key}'
            data = _http_get(url)
            if data.get('Company'):
                return True, f"연결 성공 – 택배사 {len(data['Company'])}개 지원"
            return False, str(data)
        except Exception as e:
            return False, str(e)

    def fetch_data(self, config, tracking_number, carrier_code, **kwargs):
        params = urllib.parse.urlencode({
            't_key': config.api_key,
            't_code': carrier_code,
            't_invoice': tracking_number,
        })
        url = f'{self.BASE_URL}/api/v1/trackingInfo?{params}'
        data = _http_get(url)
        return {
            'provider': 'sweettracker',
            'tracking_number': tracking_number,
            'carrier_code': carrier_code,
            'status': data.get('lastStateItem', {}).get('detail', ''),
            'completed': data.get('complete', False),
            'items': data.get('trackingDetails', []),
            'raw': data,
        }

    def get_carrier_list(self, config):
        url = f'{self.BASE_URL}/api/v1/companylist?t_key={config.api_key}'
        data = _http_get(url)
        return data.get('Company', [])


class SmartDeliveryService:
    """
    스마트택배 배송조회 API.
    https://docu.smart-village.co.kr/
    """
    BASE_URL = 'https://info.smart-village.co.kr/api/GatewayService'

    def test_connection(self, config):
        if not config.api_key:
            return False, 'API 키가 없습니다.'
        return True, 'API 키 등록됨 (실제 조회 시 검증됩니다)'

    def fetch_data(self, config, tracking_number, carrier_code, **kwargs):
        params = urllib.parse.urlencode({
            'key': config.api_key,
            'delivery_no': tracking_number,
            'code': carrier_code,
        })
        url = f'{self.BASE_URL}?{params}'
        data = _http_get(url)
        return {
            'provider': 'smartdelivery',
            'tracking_number': tracking_number,
            'status': data.get('status', ''),
            'items': data.get('trackingList', []),
            'raw': data,
        }


# ─────────────────────────────────────────────────────────────
# 3. Customs Tracking (관세청 UNI-PASS)
# ─────────────────────────────────────────────────────────────

class UnipassService:
    """
    관세청 UNI-PASS 수입화물 진행정보 API.
    https://unipass.customs.go.kr/csp/index.do
    Requires API key registration at 관세청 공공데이터포털.
    """
    BASE_URL = 'https://unipass.customs.go.kr:38010/ext/rest'

    def test_connection(self, config):
        if not config.api_key:
            return False, 'UNI-PASS API 인증키가 없습니다.'
        # Minimal test with empty query
        try:
            url = (
                f"{self.BASE_URL}/cargCsclPrgsInfoQry/retrieveCargCsclPrgsInfo"
                f"?crkyCn={config.api_key}&cargMtNo=TEST0000000001"
            )
            data = _http_get(url)
            # Even an error response means the key is accepted
            if 'cargCsclPrgsInfoQryRtnVo' in str(data):
                return True, '연결 성공 (관세청 UNI-PASS)'
            return False, str(data)[:200]
        except Exception as e:
            return False, str(e)

    def fetch_data(self, config, bl_number, **kwargs):
        """
        bl_number: B/L 번호 또는 화물관리번호
        """
        url = (
            f"{self.BASE_URL}/cargCsclPrgsInfoQry/retrieveCargCsclPrgsInfo"
            f"?crkyCn={config.api_key}&cargMtNo={urllib.parse.quote(bl_number)}"
        )
        data = _http_get(url)
        vo = data.get('cargCsclPrgsInfoQryRtnVo', {})
        items = vo.get('cargCsclPrgsInfoQryRsltVo', [])
        if isinstance(items, dict):
            items = [items]
        return {
            'provider': 'unipass',
            'bl_number': bl_number,
            'items': items,
            'raw': vo,
        }


# ─────────────────────────────────────────────────────────────
# 4. Vessel Tracking (Marine Traffic)
# ─────────────────────────────────────────────────────────────

class MarineTrafficService:
    """
    Marine Traffic API for vessel tracking.
    https://www.marinetraffic.com/en/p/api-service
    Requires paid API key.
    """
    BASE_URL = 'https://services.marinetraffic.com/api'

    def test_connection(self, config):
        if not config.api_key:
            return False, 'Marine Traffic API 키가 없습니다.'
        try:
            url = f"{self.BASE_URL}/exportvessel/v:5/{config.api_key}/limit:1/msgtype:extended/protocol:jsono"
            data = _http_get(url)
            if isinstance(data, list) or 'errors' not in str(data):
                return True, '연결 성공 (Marine Traffic)'
            return False, str(data)[:200]
        except Exception as e:
            return False, str(e)

    def fetch_data(self, config, vessel_name=None, mmsi=None, imo=None, **kwargs):
        params = {'msgtype': 'extended', 'protocol': 'jsono'}
        if vessel_name:
            params['vessel_name'] = vessel_name
        if mmsi:
            params['mmsi'] = mmsi
        if imo:
            params['imo'] = imo
        query = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}/exportvessel/v:5/{config.api_key}/{query}"
        data = _http_get(url)
        vessels = data if isinstance(data, list) else []
        return {
            'provider': 'marinetraffic',
            'count': len(vessels),
            'vessels': vessels[:20],
        }


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

_SERVICE_MAP = {
    'open_er':       OpenERService(),
    'ecos':          EcosService(),
    'sweettracker':  SweetTrackerService(),
    'smartdelivery': SmartDeliveryService(),
    'unipass':       UnipassService(),
    'marinetraffic': MarineTrafficService(),
}


def get_service(provider: str):
    svc = _SERVICE_MAP.get(provider)
    if not svc:
        raise ValueError(f'알 수 없는 provider: {provider}')
    return svc
