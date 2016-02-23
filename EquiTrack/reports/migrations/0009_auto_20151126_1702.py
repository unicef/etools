# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0008_auto_20151124_1417'),
    ]

    operations = [
        migrations.AlterField(
            model_name='result',
            name='code',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
