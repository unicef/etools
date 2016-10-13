# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0025_auto_20161013_2235'),
        ('partners', '0073_governmentinterventionresult_planned_visits'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultchain',
            name='lower_indicator',
            field=models.ForeignKey(blank=True, to='reports.LowerIndicator', null=True),
        ),
        migrations.AddField(
            model_name='resultchain',
            name='lower_result',
            field=models.ForeignKey(blank=True, to='reports.LowerResult', null=True),
        ),
    ]
