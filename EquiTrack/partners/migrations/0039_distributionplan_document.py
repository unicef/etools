# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0038_auto_20160404_1519'),
    ]

    operations = [
        migrations.AddField(
            model_name='distributionplan',
            name='document',
            field=jsonfield.fields.JSONField(null=True),
        ),
    ]
