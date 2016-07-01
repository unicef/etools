# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0058_governmentinterventionresult_activities_list'),
    ]

    operations = [
        migrations.AddField(
            model_name='governmentintervention',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 6, 21, 19, 28, 31, 356899, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='governmentintervention',
            name='number',
            field=models.CharField(max_length=45L, verbose_name=b'Reference Number', blank=True),
        ),
        migrations.AlterField(
            model_name='agreement',
            name='agreement_number',
            field=models.CharField(max_length=45L, verbose_name='Reference Number', blank=True),
        ),
    ]
