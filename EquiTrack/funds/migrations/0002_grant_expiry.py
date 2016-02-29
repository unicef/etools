# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='grant',
            name='expiry',
            field=models.DateField(null=True, blank=True),
        ),
    ]
