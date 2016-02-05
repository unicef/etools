# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_country_buisness_area_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='buisness_area_code',
            field=models.CharField(max_length=10, null=True, blank=True),
        ),
    ]
