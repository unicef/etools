# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0009_auto_20151118_1151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='triplocation',
            name='governorate',
            field=models.ForeignKey(blank=True, to='locations.Governorate', null=True),
        ),
        migrations.AlterField(
            model_name='triplocation',
            name='locality',
            field=models.ForeignKey(blank=True, to='locations.Locality', null=True),
        ),
        migrations.AlterField(
            model_name='triplocation',
            name='location',
            field=models.ForeignKey(blank=True, to='locations.Location', null=True),
        ),
        migrations.AlterField(
            model_name='triplocation',
            name='region',
            field=models.ForeignKey(blank=True, to='locations.Region', null=True),
        ),
    ]
