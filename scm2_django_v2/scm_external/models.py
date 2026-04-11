from django.db import models
from scm_accounts.models import Company


class ExternalAPIConfig(models.Model):
    FEATURE_CHOICES = [
        ('exchange_rate',       '환율 조회'),
        ('delivery_tracking',   '배송 추적'),
        ('customs_tracking',    '통관 조회'),
        ('vessel_tracking',     '선박 추적'),
        ('weather',             '날씨 조회'),
        ('economic_indicators', '경제지표 조회'),
    ]
    PROVIDER_CHOICES = [
        # 환율
        ('open_er',          'Open Exchange Rates (무료·키 불필요)'),
        ('ecos',             '한국은행 ECOS OpenAPI'),
        # 배송추적
        ('sweettracker',     '스윗트래커'),
        ('smartdelivery',    '스마트택배 API'),
        # 통관
        ('unipass',          '관세청 UNI-PASS'),
        # 선박
        ('marinetraffic',    'Marine Traffic'),
        # 날씨
        ('openweathermap',   'OpenWeatherMap'),
        ('weather_kr',       '기상청 (공공데이터포털)'),
        # 경제지표
        ('ecos_economic',    '한국은행 ECOS (경제지표)'),
        ('data_go_kr',       '공공데이터포털'),
    ]

    company       = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='api_configs')
    feature_type  = models.CharField(max_length=30, choices=FEATURE_CHOICES)
    provider      = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    api_key       = models.CharField(max_length=500, blank=True, help_text='API 키')
    api_secret    = models.CharField(max_length=500, blank=True, help_text='API 시크릿 (필요 시)')
    base_url      = models.CharField(max_length=500, blank=True, help_text='커스텀 베이스 URL (선택)')
    extra_config  = models.JSONField(default=dict, blank=True, help_text='추가 설정 (JSON)')
    is_active     = models.BooleanField(default=False)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_test_ok  = models.BooleanField(null=True, blank=True)
    last_test_msg = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'feature_type', 'provider')
        ordering = ['feature_type', 'provider']

    def __str__(self):
        return f"{self.get_feature_type_display()} / {self.get_provider_display()}"

    def masked_key(self):
        """Returns partially masked API key for display."""
        if not self.api_key:
            return ''
        if len(self.api_key) <= 8:
            return '****'
        return self.api_key[:4] + '****' + self.api_key[-4:]
