# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0044_20160414_1846'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pcafile',
            name='file',
        ),
    ]
