# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0073_governmentinterventionresult_planned_visits'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='governmentintervention',
            name='result_structure',
        ),
        migrations.RemoveField(
            model_name='pca',
            name='result_structure',
        ),
    ]
