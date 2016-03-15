# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0005_auto_20151014_1955'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileattachment',
            name='caption',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
