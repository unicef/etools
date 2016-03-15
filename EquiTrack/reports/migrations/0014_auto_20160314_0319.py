# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0013_auto_20160226_1543'),
    ]

    operations = [
        migrations.AddField(
            model_name='indicator',
            name='baseline',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='indicator',
            name='ram_indicator',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='indicator',
            name='target',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='name',
            field=models.CharField(unique=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='sector',
            field=models.ForeignKey(blank=True, to='reports.Sector', null=True),
        ),
    ]
