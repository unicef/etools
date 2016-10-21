# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0073_governmentinterventionresult_planned_visits'),
        ('reports', '0027_auto_20161014_2132'),
    ]

    operations = [
        migrations.RenameField('GovernmentIntervention', 'result_structure', 'humanitarian_response_plan'),
        migrations.RenameField('PCA', 'result_structure', 'humanitarian_response_plan')
    ]
