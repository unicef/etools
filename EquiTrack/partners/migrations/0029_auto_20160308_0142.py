# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0028_auto_20160304_1840'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agreement',
            name='agreement_number',
            field=models.CharField(help_text='Reference Number', max_length=45L, blank=True),
        ),
    ]
