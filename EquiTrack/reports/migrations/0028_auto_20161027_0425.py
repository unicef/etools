# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0027_auto_20161027_0420'),
    ]

    operations = [
        migrations.RenameModel('ResultStructure', 'ResponsePlan'),
    ]
