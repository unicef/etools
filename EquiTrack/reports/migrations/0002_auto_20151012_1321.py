# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0004_auto_20151012_1321'),
        ('partners', '0003_auto_20151012_1321'),
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='activity',
            name='sector',
        ),
        migrations.DeleteModel(
            name='Activity',
        ),
        migrations.RemoveField(
            model_name='intermediateresult',
            name='sector',
        ),
        migrations.AlterUniqueTogether(
            name='rrp5output',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='rrp5output',
            name='objective',
        ),
        migrations.RemoveField(
            model_name='rrp5output',
            name='result_structure',
        ),
        migrations.RemoveField(
            model_name='rrp5output',
            name='sector',
        ),
        migrations.DeleteModel(
            name='Rrp5Output',
        ),
        migrations.RemoveField(
            model_name='rrpobjective',
            name='result_structure',
        ),
        migrations.RemoveField(
            model_name='rrpobjective',
            name='sector',
        ),
        migrations.DeleteModel(
            name='RRPObjective',
        ),
        migrations.RemoveField(
            model_name='wbs',
            name='Intermediate_result',
        ),
        migrations.DeleteModel(
            name='IntermediateResult',
        ),
        migrations.DeleteModel(
            name='WBS',
        ),
        migrations.AddField(
            model_name='result',
            name='gic_code',
            field=models.CharField(max_length=8, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='gic_name',
            field=models.CharField(max_length=255, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='humanitarian_tag',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='level',
            field=models.PositiveIntegerField(default=1, editable=False, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='result',
            name='lft',
            field=models.PositiveIntegerField(default=1, editable=False, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='result',
            name='parent',
            field=mptt.fields.TreeForeignKey(related_name='children', blank=True, to='reports.Result', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='rght',
            field=models.PositiveIntegerField(default=1, editable=False, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='result',
            name='sic_code',
            field=models.CharField(max_length=8, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='sic_name',
            field=models.CharField(max_length=255, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='tree_id',
            field=models.PositiveIntegerField(default=1, editable=False, db_index=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='result',
            name='vision_id',
            field=models.CharField(max_length=10, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='result',
            name='wbs',
            field=models.CharField(max_length=20, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='result',
            name='name',
            field=models.CharField(unique=True, max_length=256L),
            preserve_default=True,
        ),
    ]
