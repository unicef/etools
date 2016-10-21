# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0023_auto_20160909_2203'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goal',
            name='result_structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResultStructure', null=True),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='result_structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResultStructure', null=True),
        ),
        migrations.AlterField(
            model_name='result',
            name='result_structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResultStructure', null=True),
        ),
    ]
