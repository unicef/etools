# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0024_pca_fr_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fundingcommitment',
            name='fc_ref',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
