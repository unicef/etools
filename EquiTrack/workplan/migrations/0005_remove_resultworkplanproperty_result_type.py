# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workplan', '0004_auto_20160909_1422'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resultworkplanproperty',
            name='result_type',
        ),
    ]
