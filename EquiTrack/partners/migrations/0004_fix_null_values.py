from __future__ import unicode_literals

from django.db import migrations

from utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('partners.assessment'),
        [
            'names_of_other_agencies',
            'notes',
        ]
    )
    fix_null_values(
        apps.get_model('partners.fundingcommitment'),
        [
            'fc_ref',
        ]
    )
    fix_null_values(
        apps.get_model('partners.intervention'),
        [
            'number',
            'population_focus',
        ]
    )
    fix_null_values(
        apps.get_model('partners.interventionamendment'),
        [
            'other_description',
        ]
    )
    fix_null_values(
        apps.get_model('partners.interventionbudget'),
        [
            'currency',
        ]
    )
    fix_null_values(
        apps.get_model('partners.partnerorganization'),
        [
            'address',
            'alternate_name',
            'basis_for_risk_rating',
            'city',
            'country',
            'email',
            'phone_number',
            'postal_code',
            'rating',
            'street_address',
            'type_of_assessment',
        ]
    )
    fix_null_values(
        apps.get_model('partners.partnerstaffmember'),
        [
            'phone',
            'title',
        ]
    )
    fix_null_values(
        apps.get_model('partners.plannedengagement'),
        [
            'spot_check_mr',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'partners', u'0003_auto_20180329_1155'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
