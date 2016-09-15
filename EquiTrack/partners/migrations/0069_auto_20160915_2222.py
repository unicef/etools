# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0068_remove_fundingcommitment_intervention'),
    ]

    operations = [
        migrations.AlterField(
            model_name='governmentintervention',
            name='result_structure',
            field=models.ForeignKey(to='reports.ResultStructure', on_delete=django.db.models.deletion.DO_NOTHING),
        ),
        migrations.AlterField(
            model_name='pca',
            name='result_structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResultStructure', help_text='Which result structure does this partnership report under?', null=True),
        ),
    ]
