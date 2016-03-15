# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0004_auto_20151012_1321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='ta_drafted',
            field=models.BooleanField(default=False, help_text=b'Has the TA been drafted in vision if applicable?', verbose_name=b'TA'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='tripfunds',
            name='wbs',
            field=models.ForeignKey(verbose_name=b'WBS', to='reports.Result'),
            preserve_default=True,
        ),
    ]
