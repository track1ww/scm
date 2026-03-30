from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('scm_accounts', '0001_initial'),
        ('scm_hr', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkOrder',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(max_length=50, unique=True)),
                ('title',        models.CharField(max_length=200)),
                ('description',  models.TextField(blank=True)),
                ('status',       models.CharField(
                    choices=[
                        ('DRAFT', '임시'), ('IN_PROGRESS', '진행중'),
                        ('COMPLETED', '완료'), ('CANCELLED', '취소'),
                    ],
                    default='DRAFT', max_length=20,
                )),
                ('priority',     models.CharField(
                    choices=[
                        ('LOW', '낮음'), ('MEDIUM', '보통'),
                        ('HIGH', '높음'), ('URGENT', '긴급'),
                    ],
                    default='MEDIUM', max_length=20,
                )),
                ('due_date',     models.DateField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('updated_at',   models.DateTimeField(auto_now=True)),
                ('company',      models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.CASCADE,
                    to='scm_accounts.company',
                )),
                ('assigned_to',  models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_work_orders',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('department',   models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='scm_hr.department',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WorkOrderComment',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content',    models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('work_order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='comments',
                    to='scm_wi.workorder',
                )),
                ('author',     models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='work_order_comments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
