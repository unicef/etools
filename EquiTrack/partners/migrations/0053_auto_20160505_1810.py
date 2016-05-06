# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0052_convert_disaggregation_to_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='indicatorreport',
            name='report_status',
            field=models.CharField(default=b'ontrack', max_length=15, choices=[(b'ontrack', b'On Track'), (b'constrained', b'Constrained'), (b'noprogress', b'No Progress'), (b'targetmet', b'Target Met')]),
        ),
        migrations.AlterField(
            model_name='resultchain',
            name='disaggregation',
            field=jsonfield.fields.JSONField(null=True),
        ),
    ]
