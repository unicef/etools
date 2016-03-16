# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_auto_20160216_1814'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='country_short_code',
            field=models.CharField(max_length=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='vision_sync_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
