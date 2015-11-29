# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.postgres.fields.hstore
from django.contrib.postgres.operations import HStoreExtension


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0015_auto_20151120_1817'),
    ]

    operations = [
        HStoreExtension(),
        migrations.RemoveField(
            model_name='resultchain',
            name='governorate',
        ),
        migrations.AddField(
            model_name='resultchain',
            name='disaggregation',
            field=django.contrib.postgres.fields.hstore.HStoreField(null=True),
        ),
    ]
