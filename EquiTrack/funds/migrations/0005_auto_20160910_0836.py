# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funds', '0004_auto_20160909_2258'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='grant',
            unique_together=set([]),
        ),
    ]
