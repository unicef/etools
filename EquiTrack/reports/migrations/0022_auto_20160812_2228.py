# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0021_auto_20160811_1818'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='result',
            name='labels',
        ),
        migrations.AlterField(
            model_name='result',
            name='status',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'On Track', b'On Track'), (b'Constrained', b'Constrained'), (b'No Progress', b'No Progress'), (b'Target Met', b'Target Met')]),
        ),
    ]
