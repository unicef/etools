# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0034_ramindicator'),
    ]

    operations = [
        migrations.AddField(
            model_name='ramindicator',
            name='baseline',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='ramindicator',
            name='target',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
