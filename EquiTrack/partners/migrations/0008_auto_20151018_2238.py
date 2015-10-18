# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0007_auto_20151018_2024'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agreement',
            name='end',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='agreement',
            name='start',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
