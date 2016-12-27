# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0066_auto_20160826_2026'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='deleted_flag',
            field=models.BooleanField(default=False, verbose_name='Marked for deletion'),
        ),
    ]
