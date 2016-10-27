# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0075_auto_20161027_0511'),
    ]

    operations = [
        migrations.RenameField(
            model_name='governmentintervention',
            old_name='result_structure',
            new_name='humanitarian_response_plan',
        ),
        migrations.RenameField(
            model_name='pca',
            old_name='result_structure',
            new_name='humanitarian_response_plan',
        ),
    ]
