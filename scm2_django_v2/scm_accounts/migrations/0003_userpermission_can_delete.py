from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('scm_accounts', '0002_role_userrole')]

    operations = [
        migrations.AddField(
            model_name='userpermission',
            name='can_delete',
            field=models.BooleanField(default=False),
        ),
    ]
