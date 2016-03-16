# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0031_auto_20160313_1241'),
    ]

    operations = [
        migrations.AddField(
            model_name='pca',
            name='project_type',
            field=models.CharField(blank=True, max_length=20, null=True, choices=[('Bulk Procurement', 'Bulk Procurement'), ('Construction Project', 'Construction Project')]),
        ),
    ]
