# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0019_auto_20160825_1857'),
        ('workplan', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Workplan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(blank=True, max_length=32, null=True, choices=[(b'On Track', b'On Track'), (b'Constrained', b'Constrained'), (b'No Progress', b'No Progress'), (b'Target Met', b'Target Met')])),
                ('result_structure', models.ForeignKey(to='reports.ResultStructure')),
            ],
        ),
    ]
