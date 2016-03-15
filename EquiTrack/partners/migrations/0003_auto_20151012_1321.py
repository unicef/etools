# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0002_auto_20151009_2046'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pcasectoractivity',
            name='activity',
        ),
        migrations.RemoveField(
            model_name='pcasectoractivity',
            name='pca_sector',
        ),
        migrations.DeleteModel(
            name='PCASectorActivity',
        ),
        migrations.RemoveField(
            model_name='pcasectorimmediateresult',
            name='Intermediate_result',
        ),
        migrations.RemoveField(
            model_name='pcasectorimmediateresult',
            name='pca_sector',
        ),
        migrations.RemoveField(
            model_name='pcasectorimmediateresult',
            name='wbs_activities',
        ),
        migrations.DeleteModel(
            name='PCASectorImmediateResult',
        ),
        migrations.RemoveField(
            model_name='pcasectoroutput',
            name='output',
        ),
        migrations.RemoveField(
            model_name='pcasectoroutput',
            name='pca_sector',
        ),
        migrations.DeleteModel(
            name='PCASectorOutput',
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='core_values_assessment',
            field=models.FileField(null=True, upload_to=b'partners/core_values/', blank=True),
            preserve_default=True,
        ),
    ]
