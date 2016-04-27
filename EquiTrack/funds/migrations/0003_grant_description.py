# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0002_grant_expiry'),
    ]

    operations = [
        migrations.AddField(
            model_name='grant',
            name='description',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
