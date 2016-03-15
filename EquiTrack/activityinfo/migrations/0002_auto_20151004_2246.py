# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activityinfo', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attributegroup',
            name='mandatory',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='attributegroup',
            name='multiple_allowed',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
