# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0022_auto_20160906_1927'),
    ]

    operations = [
        migrations.AlterField(
            model_name='indicator',
            name='activity_info_indicators',
            field=models.ManyToManyField(to='activityinfo.Indicator', blank=True),
        ),
    ]
