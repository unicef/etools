# Generated by Django 3.2.6 on 2022-04-08 11:04

from django.db import migrations


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
        ('reports', '0041_interventionactivityitem_code'),
    ]

    operations = [
        migrations.RunPython(number_activity_items, migrations.RunPython.noop),
    ]
