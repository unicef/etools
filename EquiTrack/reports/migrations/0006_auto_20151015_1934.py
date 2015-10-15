# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0005_auto_20151015_1930'),
    ]

    operations = [
        migrations.AlterField(
            model_name='result',
            name='name',
            field=models.TextField(),
            preserve_default=True,
        ),
    ]
