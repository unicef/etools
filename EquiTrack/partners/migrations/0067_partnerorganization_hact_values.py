# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0066_auto_20160826_2026'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='hact_values',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
    ]
