# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations, models

def create_initial_models(apps, schema_editor):
    WBS = apps.get_model('et2f', 'WBS')
    Grant = apps.get_model('et2f', 'Grant')
    Fund = apps.get_model('et2f', 'Fund')

    try:
        WBS.objects.get(id=1)
    except ObjectDoesNotExist:
        WBS.objects.create(name='Initial WBS')

    try:
        Grant.objects.get(id=1)
    except ObjectDoesNotExist:
        Grant.objects.create(name='Initial Grant')

    try:
        Fund.objects.get(id=1)
    except ObjectDoesNotExist:
        Fund.objects.create(name='Initial Fund')


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0020_travel_cancellation_note'),
    ]

    operations = [
        migrations.CreateModel(
            name='Grant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
            ],
        ),
        migrations.CreateModel(
            name='WBS',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=25)),
            ],
        ),
        migrations.AlterField(
            model_name='costassignment',
            name='fund',
            field=models.ForeignKey(related_name='+', to='et2f.Fund'),
        ),

        migrations.RemoveField(
            model_name='costassignment',
            name='wbs',
        ),
        migrations.RemoveField(
            model_name='costassignment',
            name='grant',
        ),

        migrations.RunPython(create_initial_models),

        migrations.AddField(
            model_name='costassignment',
            name='wbs',
            field=models.ForeignKey(related_name='+', default=1, to='et2f.WBS'),
        ),
        migrations.AddField(
            model_name='costassignment',
            name='grant',
            field=models.ForeignKey(related_name='+', default=1, to='et2f.Grant'),
        ),


        migrations.AddField(
            model_name='grant',
            name='wbs',
            field=models.ForeignKey(related_name='grants', default=1, to='et2f.WBS'),
        ),
        migrations.AddField(
            model_name='fund',
            name='grant',
            field=models.ForeignKey(related_name='funds', default=1, to='et2f.Grant'),
            preserve_default=False,
        ),
    ]
