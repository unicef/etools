# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0017_auto_20151203_1758'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerstaffmember',
            name='email',
            field=models.CharField(unique=True, max_length=128L),
        ),
    ]
