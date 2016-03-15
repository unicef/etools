# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import filer.fields.file
import partners.models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0012_auto_20151109_1503'),
    ]

    operations = [
        migrations.AddField(
            model_name='pcafile',
            name='attachment',
            field=models.FileField(default='', max_length=255, upload_to=partners.models.get_file_path),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='pcafile',
            name='file',
            field=filer.fields.file.FilerFileField(blank=True, to='filer.File', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='pcafile',
            name='pca',
            field=models.ForeignKey(related_name='attachments', to='partners.PCA'),
            preserve_default=True,
        ),
    ]
