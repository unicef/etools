# Generated by Django 3.2.6 on 2021-09-18 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_settings', '0008_auto_20210108_1634'),
        ('partners', '0090_alter_intervention_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='sites',
            field=models.ManyToManyField(blank=True, related_name='interventions', to='field_monitoring_settings.LocationSite', verbose_name='Sites'),
        ),
    ]
