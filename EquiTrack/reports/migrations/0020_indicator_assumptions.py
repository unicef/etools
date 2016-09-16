# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0019_auto_20160825_1857'),
    ]

    operations = [
        migrations.AddField(
            model_name='indicator',
            name='assumptions',
            field=models.TextField(null=True, blank=True),
        ),
    ]
