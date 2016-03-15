# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0014_auto_20160314_0319'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='ram',
            field=models.BooleanField(default=False),
        ),
    ]
