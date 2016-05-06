# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_hstore.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0048_indicatorduedates'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='indicatorduedates',
            options={'ordering': ['-due_date'], 'verbose_name': 'Report Due Date', 'verbose_name_plural': 'Report Due Dates'},
        ),
        migrations.AlterField(
            model_name='governmentintervention',
            name='result_structure',
            field=models.ForeignKey(to='reports.ResultStructure'),
        ),
        migrations.RemoveField(
            model_name='governmentinterventionresult',
            name='activities',
        ),
        migrations.AddField(
            model_name='governmentinterventionresult',
            name='activities',
            field=django_hstore.fields.DictionaryField(null=True, blank=True),
        ),
    ]
