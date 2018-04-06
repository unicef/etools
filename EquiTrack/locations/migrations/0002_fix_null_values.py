from __future__ import unicode_literals

from django.db import migrations

from utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('locations.cartodbtable'),
        [
            'color',
            'display_name',
            'parent_code_col',
        ]
    )
    fix_null_values(
        apps.get_model('locations.location'),
        [
            'p_code',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'locations', u'0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
