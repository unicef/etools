# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0066_auto_20160826_2026'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fundingcommitment',
            name='fc_ref',
            field=models.CharField(max_length=50, unique=True, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='fundingcommitment',
            name='grant',
            field=models.ForeignKey(blank=True, to='funds.Grant', null=True),
        ),
    ]
