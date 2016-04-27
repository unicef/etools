# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0043_auto_20160413_1358'),
    ]

    operations = [
        migrations.AddField(
            model_name='indicatorreport',
            name='report_status',
            field=models.CharField(default=b'ontrack', max_length=15, choices=[(b'ontrack', b'On Track'), (b'constrained', b'Constrained'), (b'noprogress', b'No Progress'), (b'targetmet', b'Target Met')]),
        ),
    ]
