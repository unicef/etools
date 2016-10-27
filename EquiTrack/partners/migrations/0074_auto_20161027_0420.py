# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0073_governmentinterventionresult_planned_visits'),
    ]

    operations = [
        migrations.AlterField(
            model_name='governmentintervention',
            name='result_structure',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='pca',
            name='result_structure',
            field=models.IntegerField(help_text='Which result structure does this partnership report under?', null=True, blank=True),
        ),
    ]
