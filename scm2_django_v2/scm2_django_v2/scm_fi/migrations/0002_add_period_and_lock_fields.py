from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scm_fi", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountmove",
            name="period_year",
            field=models.IntegerField(blank=True, null=True, verbose_name="회계 연도"),
        ),
        migrations.AddField(
            model_name="accountmove",
            name="period_month",
            field=models.IntegerField(blank=True, null=True, verbose_name="회계 월"),
        ),
        migrations.AddField(
            model_name="accountmove",
            name="is_locked",
            field=models.BooleanField(default=False, verbose_name="기간 마감 잠금"),
        ),
        migrations.AlterModelOptions(
            name="accountmove",
            options={"ordering": ["-posting_date", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="accountmove",
            index=models.Index(
                fields=["company", "period_year", "period_month"],
                name="scm_fi_acc_company_period_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="accountmove",
            index=models.Index(
                fields=["company", "state"],
                name="scm_fi_acc_company_state_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="accountmove",
            index=models.Index(
                fields=["posting_date"],
                name="scm_fi_acc_posting_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="accountmoveline",
            index=models.Index(
                fields=["account"],
                name="scm_fi_line_account_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="accountmoveline",
            index=models.Index(
                fields=["move"],
                name="scm_fi_line_move_idx",
            ),
        ),
    ]
