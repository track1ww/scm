from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('scm_accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalAPIConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_type', models.CharField(choices=[('exchange_rate', '환율 조회'), ('delivery_tracking', '배송 추적'), ('customs_tracking', '통관 조회'), ('vessel_tracking', '선박 추적')], max_length=30)),
                ('provider', models.CharField(choices=[('open_er', 'Open Exchange Rates (무료·키 불필요)'), ('ecos', '한국은행 ECOS OpenAPI'), ('sweettracker', '스윗트래커'), ('smartdelivery', '스마트택배 API'), ('unipass', '관세청 UNI-PASS'), ('marinetraffic', 'Marine Traffic')], max_length=30)),
                ('api_key', models.CharField(blank=True, help_text='API 키', max_length=500)),
                ('api_secret', models.CharField(blank=True, help_text='API 시크릿 (필요 시)', max_length=500)),
                ('base_url', models.CharField(blank=True, help_text='커스텀 베이스 URL (선택)', max_length=500)),
                ('extra_config', models.JSONField(blank=True, default=dict, help_text='추가 설정 (JSON)')),
                ('is_active', models.BooleanField(default=False)),
                ('last_tested_at', models.DateTimeField(blank=True, null=True)),
                ('last_test_ok', models.BooleanField(blank=True, null=True)),
                ('last_test_msg', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_configs', to='scm_accounts.company')),
            ],
            options={
                'ordering': ['feature_type', 'provider'],
                'unique_together': {('company', 'feature_type', 'provider')},
            },
        ),
    ]
