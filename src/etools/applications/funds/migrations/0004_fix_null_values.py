
from django.db import migrations

from etools.applications.utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('funds.fundscommitmentheader'),
        [
            'document_text',
            'exchange_rate',
            'fc_type',
            'responsible_person',
            'currency',
        ]
    )
    fix_null_values(
        apps.get_model('funds.fundscommitmentitem'),
        [
            'fc_ref_number',
            'fr_number',
            'fund',
            'gl_account',
            'grant_number',
            'line_item_text',
            'wbs',
        ]
    )
    fix_null_values(
        apps.get_model('funds.fundsreservationheader'),
        [
            'document_text',
            'fr_type',
            'currency',
        ]
    )
    fix_null_values(
        apps.get_model('funds.fundsreservationitem'),
        [
            'fr_ref_number',
            'fund',
            'grant_number',
            'line_item_text',
            'wbs',
        ]
    )
    fix_null_values(
        apps.get_model('funds.grant'),
        [
            'description',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'funds', u'0003_auto_20180329_1154'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
