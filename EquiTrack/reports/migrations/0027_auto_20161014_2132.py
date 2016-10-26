# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        # ('partners', '0074_auto_20161014_2132'),
        ('reports', '0026_auto_20161013_2034'),
    ]

    operations = [

        migrations.RenameModel('ResultStructure', 'ResponsePlan'),

        # migrations.AlterUniqueTogether(
        #     name='resultstructure',
        #     unique_together=set([]),
        # ),

        migrations.RenameField('Goal', 'result_structure', 'humanitarian_response_plan'),
        migrations.RenameField('Indicator', 'result_structure', 'humanitarian_response_plan'),
        migrations.RenameField('Result', 'result_structure', 'humanitarian_response_plan'),
        migrations.RenameField('Goal', 'result_structure', 'humanitarian_response_plan'),
        # migrations.RemoveField(
        #     model_name='resultstructure',
        #     name='country_programme',
        # ),

        # migrations.AlterUniqueTogether(
        #     name='responseplan',
        #     unique_together=set([('name', 'from_date', 'to_date')]),
        # ),
    ]
