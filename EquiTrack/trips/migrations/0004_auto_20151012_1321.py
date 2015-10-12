# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0003_auto_20151009_2046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tripfunds',
            name='wbs',
            field=models.ForeignKey(to='reports.Result'),
            preserve_default=True,
        ),
    ]
