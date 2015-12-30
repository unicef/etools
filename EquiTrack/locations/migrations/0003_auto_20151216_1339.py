# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0002_auto_20151211_1528'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='locality',
            field=models.ForeignKey(blank=True, to='locations.Locality', null=True),
        ),
    ]
