# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0010_auto_20151027_1852'),
    ]

    operations = [
        migrations.AddField(
            model_name='amendmentlog',
            name='status',
            field=models.CharField(blank=True, max_length=32L, choices=[('in_process', 'In Process'), ('active', 'Active'), ('implemented', 'Implemented'), ('cancelled', 'Cancelled')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='amendmentlog',
            name='amended_at',
            field=models.DateField(null=True, verbose_name=b'Signed At'),
            preserve_default=True,
        ),
    ]
