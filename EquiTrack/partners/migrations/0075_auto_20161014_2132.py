# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0027_auto_20161014_2132'),
        ('partners', '0074_auto_20161014_2132'),
    ]

    operations = [
        migrations.AddField(
            model_name='governmentintervention',
            name='humanitarian_response_plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, default=datetime.datetime(2016, 10, 14, 18, 32, 42, 794927, tzinfo=utc), to='reports.ResponsePlan'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pca',
            name='humanitarian_response_plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResponsePlan', help_text='Which result structure does this partnership report under?', null=True),
        ),
    ]
