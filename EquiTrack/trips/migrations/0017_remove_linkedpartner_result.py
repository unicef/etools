# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0016_auto_20160607_2237'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='linkedpartner',
            name='result',
        ),
    ]
