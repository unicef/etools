# Generated by Django 1.10.8 on 2018-07-30 11:21
from __future__ import unicode_literals

from django.db import migrations, models


def update_unicef_allowed(apps, schema_editor):
    AuditorFirm = apps.get_model('purchase_order', 'AuditorFirm')
    AuditorFirm.objects.exclude(purchase_orders__order_number='0000000000').update(unicef_users_allowed=False)


class Migration(migrations.Migration):

    dependencies = [
        ('purchase_order', '0005_auditorstaffmember_hidden'),
    ]

    operations = [
        migrations.RunPython(
            update_unicef_allowed, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='auditorfirm',
            name='unicef_users_allowed',
            field=models.BooleanField(default=False, editable=False, help_text='Allow UNICEF users to join and act as auditors.', verbose_name='UNICEF users allowed'),
        ),
    ]
