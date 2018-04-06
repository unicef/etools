from __future__ import unicode_literals

from django.db import migrations

from utils.common.migrating import fix_null_values


def fix_nulls(apps, schema):
    # Change null values in these fields to empty strings
    fix_null_values(
        apps.get_model('reports.appliedindicator'),
        [
            'assumptions',
            'cluster_indicator_title',
            'cluster_name',
            'context_code',
            'means_of_verification',
            'response_plan_name',
        ]
    )
    fix_null_values(
        apps.get_model('reports.indicator'),
        [
            'assumptions',
            'baseline',
            'code',
            'target',
        ]
    )
    fix_null_values(
        apps.get_model('reports.indicatorblueprint'),
        [
            'description',
            'subdomain',
        ]
    )
    fix_null_values(
        apps.get_model('reports.result'),
        [
            'activity_focus_code',
            'activity_focus_name',
            'code',
            'gic_code',
            'gic_name',
            'sic_code',
            'sic_name',
            'vision_id',
        ]
    )
    fix_null_values(
        apps.get_model('reports.sector'),
        [
            'alternate_name',
            'color',
            'description',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        (u'reports', u'0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_nulls, migrations.RunPython.noop)
    ]
