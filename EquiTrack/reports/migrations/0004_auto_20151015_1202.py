# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_auto_20151014_0817'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='activity_focus_code',
            field=models.CharField(max_length=8, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='activity_focus_name',
            field=models.CharField(max_length=255, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='result',
            name='sector',
            field=models.ForeignKey(blank=True, to='reports.Sector', null=True),
            preserve_default=True,
        ),
    ]
