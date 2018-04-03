from __future__ import unicode_literals

from django.db import migrations

from utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('purchase_order.auditorfirm'),
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


class Migration(migrations.Migration):

    dependencies = [
        (u'purchase_order', u'0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
