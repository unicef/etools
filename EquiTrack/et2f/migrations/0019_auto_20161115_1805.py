# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0018_auto_20161115_1800'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clearances',
            name='medical_clearance',
        ),
        migrations.RemoveField(
            model_name='clearances',
            name='security_clearance',
        ),
        migrations.RemoveField(
            model_name='clearances',
            name='security_course',
        ),
        migrations.RenameField(
            model_name='clearances',
            old_name='mc',
            new_name='medical_clearance',
        ),
        migrations.RenameField(
            model_name='clearances',
            old_name='sc',
            new_name='security_clearance',
        ),
        migrations.RenameField(
            model_name='clearances',
            old_name='sco',
            new_name='security_course',
        ),
    ]
