# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0071_auto_20160917_0142'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='hact_values',
            field=jsonfield.fields.JSONField(default={}, null=True, blank=True),
        ),
    ]
