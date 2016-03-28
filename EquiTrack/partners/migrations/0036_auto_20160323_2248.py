# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0035_auto_20160314_1524'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resultchain',
            name='disaggregation',
            field=jsonfield.fields.JSONField(null=True),
        ),
    ]
