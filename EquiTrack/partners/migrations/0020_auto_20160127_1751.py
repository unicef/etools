# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0019_auto_20160113_1554'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gwpcalocation',
            name='governorate',
            field=models.ForeignKey(blank=True, to='locations.Governorate', null=True),
        ),
        migrations.AlterField(
            model_name='gwpcalocation',
            name='region',
            field=models.ForeignKey(blank=True, to='locations.Region', null=True),
        ),
        migrations.AlterField(
            model_name='pca',
            name='end_date',
            field=models.DateField(help_text='The date the Intervention will end', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='pca',
            name='start_date',
            field=models.DateField(help_text='The date the Intervention will start', null=True, blank=True),
        ),
    ]
