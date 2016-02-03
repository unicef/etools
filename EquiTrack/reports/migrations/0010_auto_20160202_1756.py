# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0009_auto_20151126_1702'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
    ]
