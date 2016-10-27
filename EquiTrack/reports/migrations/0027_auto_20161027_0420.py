# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0026_auto_20161013_2034'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goal',
            name='result_structure',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='result_structure',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='result',
            name='result_structure',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
