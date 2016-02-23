# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_auto_20151015_1934'),
    ]

    operations = [
        migrations.AlterField(
            model_name='indicator',
            name='total',
            field=models.IntegerField(null=True, verbose_name=b'UNICEF Target', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='indicator',
            name='unit',
            field=models.ForeignKey(blank=True, to='reports.Unit', null=True),
            preserve_default=True,
        ),
    ]
