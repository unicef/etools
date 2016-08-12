# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0022_auto_20160812_2228'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='result',
            name='milestone',
        ),
        migrations.AddField(
            model_name='milestone',
            name='result',
            field=models.ForeignKey(related_name='milestones', default=1, to='reports.Result'),
            preserve_default=False,
        ),
    ]
