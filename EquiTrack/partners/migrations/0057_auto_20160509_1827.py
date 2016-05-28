# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0056_auto_20160509_1330'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ramindicator',
            name='baseline',
        ),
        migrations.RemoveField(
            model_name='ramindicator',
            name='target',
        ),
    ]
