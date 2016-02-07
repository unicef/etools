# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0010_auto_20160202_1756'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='from_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='result',
            name='to_date',
            field=models.DateField(null=True, blank=True),
        ),
    ]
