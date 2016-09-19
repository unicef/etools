# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20160816_2228'),
        ('partners', '0066_auto_20160826_2026'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0024_auto_20160919_1449'),
        ('locations', '0006_auto_20160229_1545'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('text', models.TextField()),
                ('author', models.ForeignKey(related_name='comments', to=settings.AUTH_USER_MODEL)),
                ('tagged_users', models.ManyToManyField(related_name='_comment_tagged_users_+', to=settings.AUTH_USER_MODEL, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=32)),
            ],
        ),
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
                ('labels', models.ManyToManyField(to='workplan.Label')),
                ('partners', models.ManyToManyField(to='partners.PartnerOrganization')),
                ('responsible_persons', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('sections', models.ManyToManyField(to='users.Section')),
            ],
        ),
        migrations.CreateModel(
            name='Workplan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(blank=True, max_length=32, null=True, choices=[(b'On Track', b'On Track'), (b'Constrained', b'Constrained'), (b'No Progress', b'No Progress'), (b'Target Met', b'Target Met')])),
                ('result_structure', models.ForeignKey(to='reports.ResultStructure')),
            ],
        ),
        migrations.AddField(
            model_name='resultworkplanproperty',
            name='workplan',
            field=models.ForeignKey(to='workplan.Workplan'),
        ),
        migrations.AddField(
            model_name='comment',
            name='workplan',
            field=models.ForeignKey(related_name='comments', to='workplan.Workplan'),
        ),
    ]
