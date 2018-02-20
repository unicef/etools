from __future__ import unicode_literals

from django.db import migrations

from utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('audit.audit'),
        [
            'audit_opinion',
        ]
    )
    fix_null_values(
        apps.get_model('audit.auditorfirm'),
        [
            'city',
            'country',
            'email',
            'phone_number',
            'postal_code',
            'street_address',
            'vendor_number',
        ]
    )
    fix_null_values(
        apps.get_model('audit.purchaseorder'),
        [
            'order_number',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'audit', u'0018_auto_20171113_1009'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
