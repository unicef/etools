# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import et2f.models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0003_auto_20161103_1127'),
    ]

    operations = [
        migrations.AddField(
            model_name='travelactivity',
            name='date',
            field=models.DateField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='travelactivity',
            name='primary_traveler',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='costassignment',
            name='grant',
            field=models.ForeignKey(related_name='+', to='funds.Grant'),
        ),
        migrations.AlterField(
            model_name='iteneraryitem',
            name='airline',
            field=models.ForeignKey(related_name='+', to='et2f.AirlineCompany'),
        ),
        migrations.AlterField(
            model_name='travel',
            name='reference_number',
            field=models.CharField(default=et2f.models.make_reference_number, max_length=12),
        ),
        migrations.AlterField(
            model_name='travelactivity',
            name='partnership',
            field=models.ForeignKey(related_name='+', to='partners.PCA'),
        ),
    ]
