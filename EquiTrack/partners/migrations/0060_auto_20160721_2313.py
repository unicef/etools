# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0059_auto_20160621_2228'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pca',
            name='number',
            field=models.CharField(max_length=45L, null=True, verbose_name='Reference Number', blank=True),
        ),
    ]
