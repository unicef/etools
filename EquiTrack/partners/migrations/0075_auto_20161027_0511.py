# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0028_auto_20161027_0425'),
        ('partners', '0074_auto_20161027_0420'),
    ]

    operations = [
        migrations.AlterField(
            model_name='governmentintervention',
            name='result_structure',
            field=models.ForeignKey(to='reports.ResponsePlan'),
        ),
        migrations.AlterField(
            model_name='pca',
            name='result_structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResponsePlan', help_text='Which result structure does this partnership report under?', null=True),
        ),
    ]
