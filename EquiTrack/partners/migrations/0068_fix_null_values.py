from __future__ import unicode_literals

from django.db import migrations, models

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
        apps.get_model('partners.intervention'),
        [
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
        apps.get_model('partners.partnerorganization'),
        [
            'address',
            'alternate_name',
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


class Migration(migrations.Migration):

    dependencies = [
        (u'partners', u'0067_auto_20180309_1210'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
