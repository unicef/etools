# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0004_auto_20161109_1200'),
    ]

    operations = [
        migrations.AddField(
            model_name='travel',
            name='mode_of_travel',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]
