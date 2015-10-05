# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import paintstore.fields


class Migration(migrations.Migration):

    dependencies = [
        ('activityinfo', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=128L)),
                ('type', models.CharField(max_length=30L, null=True, blank=True)),
                ('alternate_id', models.IntegerField(null=True, blank=True)),
                ('alternate_name', models.CharField(max_length=255, null=True, blank=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'Activities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Goal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=512L)),
                ('description', models.CharField(max_length=512L, blank=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'CCC',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Indicator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=128L)),
                ('code', models.CharField(max_length=10, null=True, blank=True)),
                ('total', models.IntegerField(verbose_name=b'UNICEF Target')),
                ('sector_total', models.IntegerField(null=True, verbose_name=b'Sector Target', blank=True)),
                ('current', models.IntegerField(default=0, null=True, blank=True)),
                ('sector_current', models.IntegerField(null=True, blank=True)),
                ('view_on_dashboard', models.BooleanField(default=False)),
                ('in_activity_info', models.BooleanField(default=False)),
                ('activity_info_indicators', models.ManyToManyField(to='activityinfo.Indicator', null=True, blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IntermediateResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ir_wbs_reference', models.CharField(max_length=50L)),
                ('name', models.CharField(unique=True, max_length=128L)),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
                ('alternate_id', models.IntegerField(null=True, blank=True)),
                ('alternate_name', models.CharField(max_length=255, null=True, blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256L)),
                ('code', models.CharField(max_length=10, null=True, blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResultStructure',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=150)),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResultType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=150)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Rrp5Output',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256L)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Output',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RRPObjective',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256L)),
                ('result_structure', models.ForeignKey(blank=True, to='reports.ResultStructure', null=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Objective',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sector',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=45L)),
                ('description', models.CharField(max_length=256L, null=True, blank=True)),
                ('alternate_id', models.IntegerField(null=True, blank=True)),
                ('alternate_name', models.CharField(max_length=255, null=True, blank=True)),
                ('dashboard', models.BooleanField(default=False)),
                ('color', paintstore.fields.ColorPickerField(max_length=7, null=True, blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(unique=True, max_length=45L)),
            ],
            options={
                'ordering': ['type'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WBS',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128L)),
                ('code', models.CharField(max_length=128L)),
                ('Intermediate_result', models.ForeignKey(to='reports.IntermediateResult')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='rrpobjective',
            name='sector',
            field=models.ForeignKey(to='reports.Sector'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rrp5output',
            name='objective',
            field=models.ForeignKey(blank=True, to='reports.RRPObjective', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rrp5output',
            name='result_structure',
            field=models.ForeignKey(blank=True, to='reports.ResultStructure', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rrp5output',
            name='sector',
            field=models.ForeignKey(to='reports.Sector'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='rrp5output',
            unique_together=set([('result_structure', 'name')]),
        ),
        migrations.AddField(
            model_name='result',
            name='result_structure',
            field=models.ForeignKey(to='reports.ResultStructure'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='result_type',
            field=models.ForeignKey(to='reports.ResultType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='sector',
            field=models.ForeignKey(to='reports.Sector'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='intermediateresult',
            name='sector',
            field=models.ForeignKey(to='reports.Sector'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='indicator',
            name='result',
            field=models.ForeignKey(blank=True, to='reports.Result', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='indicator',
            name='result_structure',
            field=models.ForeignKey(blank=True, to='reports.ResultStructure', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='indicator',
            name='sector',
            field=models.ForeignKey(to='reports.Sector'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='indicator',
            name='unit',
            field=models.ForeignKey(to='reports.Unit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='goal',
            name='result_structure',
            field=models.ForeignKey(blank=True, to='reports.ResultStructure', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='goal',
            name='sector',
            field=models.ForeignKey(related_name='goals', to='reports.Sector'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='activity',
            name='sector',
            field=models.ForeignKey(to='reports.Sector'),
            preserve_default=True,
        ),
    ]
