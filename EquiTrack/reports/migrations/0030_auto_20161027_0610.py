# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0029_auto_20161027_0450'),
    ]

    operations = [
        migrations.RenameField(
            model_name='goal',
            old_name='result_structure',
            new_name='humanitarian_response_plan',
        ),
        migrations.RenameField(
            model_name='indicator',
            old_name='result_structure',
            new_name='humanitarian_response_plan',
        ),
        migrations.RenameField(
            model_name='result',
            old_name='result_structure',
            new_name='humanitarian_response_plan',
        ),
    ]
