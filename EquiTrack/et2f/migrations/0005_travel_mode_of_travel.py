# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0004_auto_20161109_1200'),
    ]

    operations = [
        migrations.AddField(
            model_name='travel',
            name='mode_of_travel',
            field=django.contrib.postgres.fields.ArrayField(default=[], base_field=models.CharField(max_length=255), size=None),
        ),
    ]
