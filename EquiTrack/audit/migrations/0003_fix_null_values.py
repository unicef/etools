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


class Migration(migrations.Migration):

    dependencies = [
        (u'audit', u'0002_auto_20180326_1605'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
