# Generated by Django 1.10.8 on 2018-05-18 16:10
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models

import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('action_points', '0002_auto_20180518_0835'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='actionpoint',
            name='action_taken',
        ),
        migrations.RemoveField(
            model_name='actionpoint',
            name='priority',
        ),
        migrations.AddField(
            model_name='actionpoint',
            name='high_priority',
            field=models.BooleanField(default=False, verbose_name='High Priority'),
        ),
        migrations.AlterField(
            model_name='actionpoint',
            name='date_of_completion',
            field=model_utils.fields.MonitorField(blank=True, default=None, monitor='status', null=True, verbose_name='Date Action Point Completed', when=set(['completed'])),
        ),
        migrations.AlterField(
            model_name='actionpoint',
            name='office',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.Office', verbose_name='Office'),
        ),
        migrations.AlterField(
            model_name='actionpoint',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='reports.Sector', verbose_name='Section'),
        ),
    ]
