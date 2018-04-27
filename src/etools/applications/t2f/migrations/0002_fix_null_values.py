
from django.db import migrations

from etools.applications.utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('t2f.actionpoint'),
        [
            'actions_taken',
            'comments',
            'status',
        ]
    )
    fix_null_values(
        apps.get_model('t2f.invoice'),
        [
            'vision_fi_id',
        ]
    )
    fix_null_values(
        apps.get_model('t2f.invoice'),
        [
            'messages',
        ],
        []
    )
    fix_null_values(
        apps.get_model('t2f.itineraryitem'),
        [
            'mode_of_travel',
        ]
    )
    fix_null_values(
        apps.get_model('t2f.travel'),
        [
            'additional_note',
            'cancellation_note',
            'certification_note',
            'misc_expenses',
            'purpose',
            'rejection_note',
            'report_note',
        ]
    )
    fix_null_values(
        apps.get_model('t2f.travelactivity'),
        [
            'travel_type',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u't2f', u'0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
