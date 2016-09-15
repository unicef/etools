# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20160816_2228'),
        ('partners', '0066_auto_20160826_2026'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0021_auto_20160908_1944'),
        ('locations', '0006_auto_20160229_1545'),
        ('workplan', '0002_workplan'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResultWorkplanProperty',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('assumptions', models.TextField(null=True, blank=True)),
                ('status', models.CharField(blank=True, max_length=255, null=True, choices=[(b'On Track', b'On Track'), (b'Constrained', b'Constrained'), (b'No Progress', b'No Progress'), (b'Target Met', b'Target Met')])),
                ('prioritized', models.BooleanField(default=False)),
                ('metadata', jsonfield.fields.JSONField(null=True, blank=True)),
                ('other_partners', models.CharField(max_length=2048, null=True, blank=True)),
                ('rr_funds', models.PositiveIntegerField(null=True, blank=True)),
                ('or_funds', models.PositiveIntegerField(null=True, blank=True)),
                ('ore_funds', models.PositiveIntegerField(null=True, blank=True)),
                ('total_funds', models.PositiveIntegerField(null=True, blank=True)),
                ('geotag', models.ManyToManyField(to='locations.Location')),
                ('partners', models.ManyToManyField(to='partners.PartnerOrganization')),
                ('responsible_persons', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('result_type', models.ForeignKey(to='reports.ResultType')),
                ('sections', models.ManyToManyField(to='users.Section')),
            ],
        ),
        migrations.AlterField(
            model_name='workplan',
            name='status',
            field=models.CharField(blank=True, max_length=32, null=True, choices=[(b'Draft', b'Draft'), (b'Approved', b'Approved'), (b'Completed', b'Completed')]),
        ),
        migrations.AddField(
            model_name='resultworkplanproperty',
            name='workplan',
            field=models.ForeignKey(to='workplan.Workplan'),
        ),
    ]
