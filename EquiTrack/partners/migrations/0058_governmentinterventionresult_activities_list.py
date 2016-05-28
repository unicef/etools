# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0017_auto_20160428_1033'),
        ('partners', '0057_auto_20160509_1827'),
    ]

    operations = [
        migrations.AddField(
            model_name='governmentinterventionresult',
            name='activities_list',
            field=models.ManyToManyField(related_name='activities_list', null=True, to='reports.Result', blank=True),
        ),
    ]
