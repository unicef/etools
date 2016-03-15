# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0027_resultchain_current_progress'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='indicatorprogress',
            name='indicator',
        ),
        migrations.RemoveField(
            model_name='indicatorprogress',
            name='pca_sector',
        ),
        migrations.RemoveField(
            model_name='indicatorreport',
            name='from_date',
        ),
        migrations.RemoveField(
            model_name='indicatorreport',
            name='to_date',
        ),
        migrations.AddField(
            model_name='indicatorreport',
            name='end',
            field=models.DateTimeField(null=True, verbose_name='end', blank=True),
        ),
        migrations.AddField(
            model_name='indicatorreport',
            name='start',
            field=models.DateTimeField(null=True, verbose_name='start', blank=True),
        ),
        migrations.DeleteModel(
            name='IndicatorProgress',
        ),
    ]
