# Generated by Django 1.10.8 on 2018-07-09 13:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0012_auto_20180709_1328'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appliedindicator',
            name='baseline',
            field=models.JSONField(default={'d': 1, 'v': 0}, null=True),
        ),
    ]
