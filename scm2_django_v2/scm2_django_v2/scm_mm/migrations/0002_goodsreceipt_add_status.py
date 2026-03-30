"""
Migration: scm_mm - GoodsReceipt 에 status 필드 추가
Signal 연계에서 status='completed' 로 트리거합니다.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scm_mm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="goodsreceipt",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft",     "임시저장"),
                    ("confirmed", "입고확인"),
                    ("completed", "입고완료"),
                    ("cancelled", "취소"),
                ],
                default="draft",
                max_length=20,
                verbose_name="상태",
            ),
        ),
    ]
