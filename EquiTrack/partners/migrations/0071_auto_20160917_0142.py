# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0070_auto_20160915_2340'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='deleted_flag',
            field=models.BooleanField(default=False, verbose_name='Marked for deletion'),
        ),
    ]
