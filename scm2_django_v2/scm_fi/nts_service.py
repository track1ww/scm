"""
scm_fi.nts_service — 국세청 전자세금계산서 ASP 연동 서비스

## 설정 방법 (.env)
    NTS_ASP_CERT_KEY=<ASP 발급 인증키>
    NTS_ASP_BASE_URL=https://api.등록한ASP사.co.kr   # ASP사별로 다름

## 지원 ASP 제공업체 (환경변수로 선택)
    NTS_ASP_PROVIDER=BIZFORMS | ECOUNT | UPLUS   (기본: BIZFORMS)

## 동작 방식
    - NTS_ASP_CERT_KEY 미설정 → NTSServiceDisabled 예외 발생
    - 설정 시 → 실제 ASP API 호출 (전송, 조회, 취소)

## 법적 근거
    전자세금계산서 의무 발행 (부가가치세법 제32조, 국세청 고시 제2023-19호)
    공급가액 기준 연 1억원 이상 개인사업자 의무 대상
"""

import os
import json
import logging
import hashlib
import datetime
import requests
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger('scm_fi.nts')

# ──────────────────────────────────────────────
# 설정 로드
# ──────────────────────────────────────────────

def _get_config():
    return {
        'cert_key':  os.environ.get('NTS_ASP_CERT_KEY', ''),
        'base_url':  os.environ.get('NTS_ASP_BASE_URL', 'https://api.bizforms.co.kr/etax/v1'),
        'provider':  os.environ.get('NTS_ASP_PROVIDER', 'BIZFORMS'),
    }


def is_enabled() -> bool:
    """NTS_ASP_CERT_KEY 환경변수가 설정돼 있으면 True."""
    return bool(_get_config()['cert_key'])


class NTSServiceDisabled(Exception):
    """ASP 키가 설정되지 않아 서비스를 사용할 수 없음."""


# ──────────────────────────────────────────────
# 데이터 모델
# ──────────────────────────────────────────────

@dataclass
class TaxInvoiceItem:
    item_name: str
    quantity: float
    unit_price: float
    supply_amount: float
    tax_amount: float


@dataclass
class NTSTaxInvoicePayload:
    """국세청 전자세금계산서 표준 필드."""
    # 공급자 정보
    supplier_reg_no: str       # 사업자등록번호 (하이픈 없이 10자리)
    supplier_name: str
    supplier_rep_name: str     # 대표자명
    supplier_addr: str
    supplier_biz_type: str     # 업태
    supplier_biz_class: str    # 종목
    supplier_email: str

    # 공급받는자 정보
    buyer_reg_no: str
    buyer_name: str
    buyer_rep_name: str
    buyer_addr: str
    buyer_email: str

    # 공급가액 정보
    issue_date: str            # YYYYMMDD
    supply_amount: float
    tax_amount: float
    total_amount: float
    remark: str = ''

    # 품목
    items: list = None         # List[TaxInvoiceItem]

    def to_dict(self):
        d = asdict(self)
        d['items'] = [asdict(i) for i in (self.items or [])]
        return d


# ──────────────────────────────────────────────
# ASP 클라이언트
# ──────────────────────────────────────────────

class NTSASPClient:
    """국세청 공인 전자세금계산서 ASP 클라이언트."""

    def __init__(self):
        cfg = _get_config()
        if not cfg['cert_key']:
            raise NTSServiceDisabled(
                'NTS_ASP_CERT_KEY 환경변수가 설정되지 않았습니다. '
                '.env 파일에 NTS_ASP_CERT_KEY=<발급받은 인증키>를 추가하세요.'
            )
        self.cert_key = cfg['cert_key']
        self.base_url = cfg['base_url'].rstrip('/')
        self.provider = cfg['provider']
        self.timeout  = 30

    def _headers(self):
        return {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': f'Bearer {self.cert_key}',
            'X-Provider': self.provider,
        }

    def _request(self, method, path, payload=None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            resp = requests.request(
                method, url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            logger.error('NTS ASP HTTP error: %s — %s', e, e.response.text if e.response else '')
            raise
        except requests.RequestException as e:
            logger.error('NTS ASP connection error: %s', e)
            raise

    # ── 발행 ──

    def issue(self, payload: NTSTaxInvoicePayload) -> dict:
        """
        전자세금계산서 발행 요청.

        Returns:
            {
                'nts_confirm_num': '20240101-...',   # 국세청 승인번호
                'issue_date': 'YYYYMMDD',
                'status': 'ISSUED',
            }
        """
        logger.info('NTS: 전자세금계산서 발행 요청 — %s → %s',
                    payload.supplier_name, payload.buyer_name)
        return self._request('POST', '/issue', payload.to_dict())

    # ── 조회 ──

    def query(self, nts_confirm_num: str) -> dict:
        """국세청 승인번호로 발행 상태 조회."""
        return self._request('GET', f'/query/{nts_confirm_num}')

    # ── 취소 ──

    def cancel(self, nts_confirm_num: str, reason: str = '') -> dict:
        """발행된 세금계산서 취소."""
        logger.info('NTS: 전자세금계산서 취소 — %s', nts_confirm_num)
        return self._request('POST', '/cancel', {
            'nts_confirm_num': nts_confirm_num,
            'cancel_reason': reason,
        })

    # ── 목록 조회 ──

    def list_issued(self, issue_date_from: str, issue_date_to: str) -> list:
        """기간별 발행 목록 조회 (YYYYMMDD 형식)."""
        return self._request('GET', '/list', {
            'date_from': issue_date_from,
            'date_to':   issue_date_to,
        })


# ──────────────────────────────────────────────
# Django TaxInvoice 모델 → ASP 페이로드 변환
# ──────────────────────────────────────────────

def build_payload_from_invoice(tax_invoice) -> NTSTaxInvoicePayload:
    """
    scm_fi.TaxInvoice 인스턴스를 NTSTaxInvoicePayload로 변환합니다.
    회사 정보는 tax_invoice.company에서 읽습니다.
    """
    company = tax_invoice.company
    issue_date = (tax_invoice.issue_date or datetime.date.today()).strftime('%Y%m%d')

    return NTSTaxInvoicePayload(
        supplier_reg_no   = getattr(company, 'business_no', '').replace('-', ''),
        supplier_name     = getattr(company, 'company_name', ''),
        supplier_rep_name = getattr(company, 'rep_name', ''),
        supplier_addr     = getattr(company, 'address', ''),
        supplier_biz_type  = getattr(company, 'biz_type', ''),
        supplier_biz_class = getattr(company, 'biz_class', ''),
        supplier_email    = getattr(company, 'email', ''),

        buyer_reg_no   = getattr(tax_invoice, 'buyer_reg_no', ''),
        buyer_name     = getattr(tax_invoice, 'buyer_name', ''),
        buyer_rep_name = getattr(tax_invoice, 'buyer_rep_name', ''),
        buyer_addr     = getattr(tax_invoice, 'buyer_addr', ''),
        buyer_email    = getattr(tax_invoice, 'buyer_email', ''),

        issue_date     = issue_date,
        supply_amount  = float(getattr(tax_invoice, 'supply_amount', 0) or 0),
        tax_amount     = float(getattr(tax_invoice, 'tax_amount', 0) or 0),
        total_amount   = float(getattr(tax_invoice, 'total_amount', 0) or 0),
        remark         = getattr(tax_invoice, 'remark', ''),
        items          = [],
    )
