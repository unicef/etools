# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20160313_1241'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='vision_last_synced',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
