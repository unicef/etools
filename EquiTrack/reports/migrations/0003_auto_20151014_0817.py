# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_auto_20151012_1321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='result',
            name='name',
            field=models.TextField(unique=True),
            preserve_default=True,
        ),
    ]
