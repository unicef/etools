# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import partners.models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0006_auto_20160229_1545'),
        ('partners', '0037_auto_20160329_0220'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='distributionplan',
            name='location',
        ),
        migrations.AddField(
            model_name='distributionplan',
            name='site',
            field=models.ForeignKey(to='locations.Location', null=True),
        ),
        migrations.AlterField(
            model_name='agreement',
            name='attached_agreement',
            field=models.FileField(upload_to=partners.models.get_agreement_path, blank=True),
        ),
    ]
