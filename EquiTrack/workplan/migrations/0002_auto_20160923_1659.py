# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0024_auto_20160919_1449'),
        ('workplan', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultworkplanproperty',
            name='result',
            field=models.ForeignKey(default=1, to='reports.Result'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='resultworkplanproperty',
            unique_together=set([('workplan', 'result')]),
        ),
    ]
