# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0042_auto_20160413_1321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pca',
            name='number',
            field=models.CharField(help_text='Document Reference Number', max_length=45L, null=True, blank=True),
        ),
    ]
