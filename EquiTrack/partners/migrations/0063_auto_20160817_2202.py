# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0062_auto_20160817_1742'),
    ]

    operations = [
        migrations.AlterField(
            model_name='governmentinterventionresult',
            name='activities_list',
            field=models.ManyToManyField(related_name='activities_list', to='reports.Result', blank=True),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='vendor_number',
            field=models.CharField(max_length=30, unique=True, null=True, blank=True),
        ),
    ]
