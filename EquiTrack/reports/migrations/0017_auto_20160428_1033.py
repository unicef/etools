# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0016_auto_20160323_1933'),
    ]

    operations = [
        migrations.AlterField(
            model_name='indicator',
            name='activity_info_indicators',
            field=models.ManyToManyField(to='activityinfo.Indicator'),
        ),
    ]
