# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0006_auto_20160229_1545'),
        ('reports', '0019_result_geotag'),
    ]

    operations = [
        migrations.CreateModel(
            name='Milestone',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.TextField()),
                ('assumptions', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='result',
            name='prioritized',
            field=models.BooleanField(default=False),
        ),
        migrations.RemoveField(
            model_name='result',
            name='geotag',
        ),
        migrations.AddField(
            model_name='result',
            name='geotag',
            field=models.ManyToManyField(to='locations.Location'),
        ),
        migrations.AlterField(
            model_name='result',
            name='metadata',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='result',
            name='status',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'on track', b'on track'), (b'constraint', b'constraint'), (b'status3', b'status3')]),
        ),
        migrations.AddField(
            model_name='result',
            name='milestone',
            field=models.OneToOneField(null=True, blank=True, to='reports.Milestone'),
        ),
    ]
