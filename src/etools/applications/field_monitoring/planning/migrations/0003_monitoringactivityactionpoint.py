# Generated by Django 2.2.7 on 2019-11-26 11:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('action_points', '0013_actionpoint_monitoring_activity'),
        ('field_monitoring_planning', '0002_auto_20191119_1503'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonitoringActivityActionPoint',
            fields=[
            ],
            options={
                'verbose_name': 'Monitoring Activity Action Point',
                'verbose_name_plural': 'Monitoring Activity Action Points',
                'abstract': False,
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('action_points.actionpoint',),
        ),
    ]
