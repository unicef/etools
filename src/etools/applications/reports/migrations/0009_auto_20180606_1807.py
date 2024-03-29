# Generated by Django 1.10.8 on 2018-06-06 18:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0008_auto_20180515_1744'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliedindicator',
            name='baseline_new',
            field=models.JSONField(default={'d': 1, 'v': 0}),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='denominator_label',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='label',
            field=models.TextField(blank=True, max_length=4048, null=True),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='measurement_specifications',
            field=models.TextField(blank=True, max_length=4048, null=True),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='numerator_label',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='appliedindicator',
            name='target_new',
            field=models.JSONField(default={'d': 1, 'v': 0}),
        ),
    ]
