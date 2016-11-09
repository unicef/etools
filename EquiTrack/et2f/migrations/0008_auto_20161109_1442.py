# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0007_auto_20161109_1405'),
    ]

    operations = [
        migrations.AlterField(
            model_name='travelactivity',
            name='date',
            field=models.DateTimeField(),
        ),
    ]
