# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0006_fileattachment_caption'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileattachment',
            name='caption',
            field=models.TextField(help_text=b'Description of the file to upload: optional', null=True, verbose_name=b'Caption / Description', blank=True),
            preserve_default=True,
        ),
    ]
