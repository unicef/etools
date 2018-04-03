from __future__ import unicode_literals

from django.db import migrations

from utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('users.country'),
        [
            'business_area_code',
            'country_short_code',
            'long_name',
        ]
    )
    fix_null_values(
        apps.get_model('users.userprofile'),
        [
            'job_title',
            'org_unit_code',
            'org_unit_name',
            'phone_number',
            'post_number',
            'post_title',
            'section_code',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'users', u'0002_auto_20180329_2123'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
