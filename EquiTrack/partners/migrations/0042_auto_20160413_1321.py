# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0041_auto_20160413_0051'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='vendor_number',
            field=models.BigIntegerField(unique=True, null=True, blank=True),
        ),
    ]
