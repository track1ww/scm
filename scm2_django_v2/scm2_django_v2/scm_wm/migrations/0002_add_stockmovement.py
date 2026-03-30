"""
Migration: scm_wm - StockMovement 재고이동이력 테이블 추가
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scm_accounts", "0001_initial"),
        ("scm_wm", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "material_code",
                    models.CharField(max_length=100, verbose_name="자재코드/품목코드"),
                ),
                (
                    "material_name",
                    models.CharField(blank=True, max_length=200, verbose_name="자재명"),
                ),
                (
                    "movement_type",
                    models.CharField(
                        choices=[
                            ("IN",       "입고"),
                            ("OUT",      "출고"),
                            ("TRANSFER", "이동"),
                            ("ADJUST",   "조정"),
                        ],
                        max_length=10,
                        verbose_name="이동유형",
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=3, max_digits=15, verbose_name="수량"
                    ),
                ),
                (
                    "before_qty",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=15,
                        verbose_name="변동 전 재고",
                    ),
                ),
                (
                    "after_qty",
                    models.DecimalField(
                        decimal_places=3,
                        default=0,
                        max_digits=15,
                        verbose_name="변동 후 재고",
                    ),
                ),
                (
                    "reference_document",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="참조 문서번호"
                    ),
                ),
                (
                    "reference_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PO", "발주"),
                            ("SO", "판매주문"),
                            ("WO", "작업지시"),
                        ],
                        max_length=10,
                        verbose_name="참조 문서유형",
                    ),
                ),
                ("note",       models.TextField(blank=True, verbose_name="비고")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="생성일시"),
                ),
                (
                    "created_by",
                    models.CharField(blank=True, max_length=100, verbose_name="생성자"),
                ),
                (
                    "company",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="scm_accounts.company",
                        verbose_name="회사",
                    ),
                ),
                (
                    "warehouse",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="scm_wm.warehouse",
                        verbose_name="창고",
                    ),
                ),
            ],
            options={
                "verbose_name":        "재고이동이력",
                "verbose_name_plural": "재고이동이력",
                "ordering":            ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["material_code", "warehouse"],
                name="scm_wm_stk_matcode_wh_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["reference_document"],
                name="scm_wm_stk_ref_doc_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["movement_type", "created_at"],
                name="scm_wm_stk_mvtype_date_idx",
            ),
        ),
    ]
