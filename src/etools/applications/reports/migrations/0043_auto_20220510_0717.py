# Generated by Django 3.2.6 on 2022-05-10 07:17

from django.db import migrations


def number_lower_results(apps, schema_editor):
    LowerResult = apps.get_model('reports', 'LowerResult')
    InterventionResultLink = apps.get_model('partners', 'InterventionResultLink')
    for result_link in InterventionResultLink.objects.all():
        lower_results = result_link.ll_results.all()
        lower_results.update(code=None) # reset codes to avoid IntegrityError collision caused by old data
        for i, lower_result in enumerate(lower_results):
            lower_result.code = '{0}.{1}'.format(result_link.code, str(i + 1))
        LowerResult.objects.bulk_update(lower_results, fields=['code'])

def number_intervention_activities(apps, schema_editor):
    InterventionActivity = apps.get_model('reports', 'InterventionActivity')
    LowerResult = apps.get_model('reports', 'LowerResult')
    for lower_result in LowerResult.objects.all():
        activities = lower_result.activities.all()
        for i, activity in enumerate(activities):
            activity.code = '{0}.{1}'.format(lower_result.code, str(i + 1))
        InterventionActivity.objects.bulk_update(activities, fields=['code'])


def number_activity_items(apps, schema_editor):
    InterventionActivityItem = apps.get_model('reports', 'InterventionActivityItem')
    InterventionActivity = apps.get_model('reports', 'InterventionActivity')
    for activity in InterventionActivity.objects.all():
        items = activity.items.all()
        for i, item in enumerate(items):
            item.code = '{0}.{1}'.format(activity.code, str(i + 1))
        InterventionActivityItem.objects.bulk_update(items, fields=['code'])


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0042_auto_20220408_1104'),
        ('partners', '0102_auto_20220510_0711'),
    ]

    operations = [
        migrations.RunPython(number_lower_results, migrations.RunPython.noop),
        migrations.RunPython(number_intervention_activities, migrations.RunPython.noop),
        migrations.RunPython(number_activity_items, migrations.RunPython.noop),
    ]
