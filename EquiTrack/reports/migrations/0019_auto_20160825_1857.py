# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.postgres.fields
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20160816_2228'),
        ('locations', '0006_auto_20160229_1545'),
        ('reports', '0018_auto_20160811_1654'),
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
            name='assumptions',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='result',
            name='geotag',
            field=models.ManyToManyField(to='locations.Location'),
        ),
        migrations.AddField(
            model_name='result',
            name='metadata',
            field=jsonfield.fields.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='result',
            name='prioritized',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='result',
            name='sections',
            field=models.ManyToManyField(to='users.Section'),
        ),
        migrations.AddField(
            model_name='result',
            name='status',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'On Track', b'On Track'), (b'Constrained', b'Constrained'), (b'No Progress', b'No Progress'), (b'Target Met', b'Target Met')]),
        ),
        migrations.AddField(
            model_name='result',
            name='users',
            field=django.contrib.postgres.fields.ArrayField(default=list, base_field=models.IntegerField(), size=None),
        ),
        migrations.AddField(
            model_name='milestone',
            name='result',
            field=models.ForeignKey(related_name='milestones', to='reports.Result'),
        ),
    ]
