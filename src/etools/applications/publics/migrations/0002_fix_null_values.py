
from django.db import migrations

from etools.applications.utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('publics.country'),
        [
            'dsa_code',
            'iso_2',
            'iso_3',
        ]
    )
    fix_null_values(
        apps.get_model('publics.dsarateupload'),
        [
            'status',
        ]
    )
    fix_null_values(
        apps.get_model('publics.travelagent'),
        [
            'city',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'publics', u'0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
