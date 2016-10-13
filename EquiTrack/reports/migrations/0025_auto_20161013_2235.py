# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0024_auto_20161005_2137'),
    ]

    operations = [
        migrations.CreateModel(
            name='LowerIndicator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=1024)),
                ('code', models.CharField(max_length=50, null=True, blank=True)),
                ('total', models.IntegerField(null=True, verbose_name=b'UNICEF Target', blank=True)),
                ('sector_total', models.IntegerField(null=True, verbose_name=b'Sector Target', blank=True)),
                ('current', models.IntegerField(default=0, null=True, blank=True)),
                ('sector_current', models.IntegerField(null=True, blank=True)),
                ('assumptions', models.TextField(null=True, blank=True)),
                ('target', models.CharField(max_length=255, null=True, blank=True)),
                ('baseline', models.CharField(max_length=255, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='LowerResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('code', models.CharField(max_length=50, null=True, blank=True)),
                ('from_date', models.DateField(null=True, blank=True)),
                ('to_date', models.DateField(null=True, blank=True)),
                ('hidden', models.BooleanField(default=False)),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('country_programme', models.ForeignKey(blank=True, to='reports.CountryProgramme', null=True)),
                ('parent', mptt.fields.TreeForeignKey(related_name='children', blank=True, to='reports.LowerResult', null=True)),
                ('result_structure', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResultStructure', null=True)),
                ('result_type', models.ForeignKey(to='reports.ResultType')),
                ('sector', models.ForeignKey(blank=True, to='reports.Sector', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='lowerindicator',
            name='result',
            field=models.ForeignKey(blank=True, to='reports.LowerResult', null=True),
        ),
        migrations.AddField(
            model_name='lowerindicator',
            name='result_structure',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, blank=True, to='reports.ResultStructure', null=True),
        ),
        migrations.AddField(
            model_name='lowerindicator',
            name='sector',
            field=models.ForeignKey(blank=True, to='reports.Sector', null=True),
        ),
        migrations.AddField(
            model_name='lowerindicator',
            name='unit',
            field=models.ForeignKey(blank=True, to='reports.Unit', null=True),
        ),
    ]
