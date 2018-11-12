# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-11-12 08:29
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0013_auto_20180709_1348'),
        ('field_monitoring_visits', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='unicefvisit',
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='visit',
            managers=[
            ],
        ),
        migrations.RemoveField(
            model_name='unicefvisit',
            name='primary_field_monitor',
        ),
        migrations.RemoveField(
            model_name='unicefvisit',
            name='team_members',
        ),
        migrations.AddField(
            model_name='visit',
            name='primary_field_monitor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fm_primary_visits', to=settings.AUTH_USER_MODEL, verbose_name='Primary Field Monitor'),
        ),
        migrations.AddField(
            model_name='visit',
            name='team_members',
            field=models.ManyToManyField(blank=True, related_name='fm_visits', to=settings.AUTH_USER_MODEL, verbose_name='Team Members'),
        ),
        migrations.AddField(
            model_name='visitmethodtype',
            name='cp_output',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='visit_method_types', to='reports.Result', verbose_name='CP Output'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='visitmethodtype',
            name='visit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='method_types', to='field_monitoring_visits.Visit', verbose_name='Visit'),
        ),
    ]
