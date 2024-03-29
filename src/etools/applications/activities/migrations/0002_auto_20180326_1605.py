# Generated by Django 1.10.8 on 2018-03-26 16:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('activities', '0001_initial'),
        ('locations', '0001_initial'),
        ('unicef_locations', '0001_initial'),
        ('reports', '0001_initial'),
        ('partners', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='cp_output',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='reports.Result', verbose_name='CP Output'),
        ),
        migrations.AddField(
            model_name='activity',
            name='intervention',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='partners.Intervention', verbose_name='Intervention'),
        ),
        migrations.AddField(
            model_name='activity',
            name='locations',
            field=models.ManyToManyField(related_name='_activity_locations_+',
                                         to='locations.Location', verbose_name='Locations'),
        ),
        migrations.AddField(
            model_name='activity',
            name='partner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='partners.PartnerOrganization', verbose_name='Implementing Partner'),
        ),
    ]
