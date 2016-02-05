# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20160204_1237'),
    ]

    operations = [
        migrations.RenameField(
            model_name='country',
            old_name='buisness_area_code',
            new_name='business_area_code',
        ),
    ]
