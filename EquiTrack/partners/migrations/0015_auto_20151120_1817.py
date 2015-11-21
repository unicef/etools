# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0014_auto_20151119_1310'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultchain',
            name='code',
            field=models.CharField(max_length=10, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='resultchain',
            name='in_kind_amount',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='resultchain',
            name='partner_contribution',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='resultchain',
            name='unicef_cash',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
    ]
