# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0020_indicator_assumptions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='result',
            name='assumptions',
        ),
        migrations.RemoveField(
            model_name='result',
            name='geotag',
        ),
        migrations.RemoveField(
            model_name='result',
            name='metadata',
        ),
        migrations.RemoveField(
            model_name='result',
            name='prioritized',
        ),
        migrations.RemoveField(
            model_name='result',
            name='sections',
        ),
        migrations.RemoveField(
            model_name='result',
            name='status',
        ),
        migrations.RemoveField(
            model_name='result',
            name='users',
        ),
    ]
