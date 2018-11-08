# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-11-08 09:21
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_fsm


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('field_monitoring_shared', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('field_monitoring_visits', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StartedMethod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', django_fsm.FSMField(choices=[('started', 'Started'), ('completed', 'Completed')], default='started', max_length=50)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='started_methods', to=settings.AUTH_USER_MODEL, verbose_name='Author')),
                ('method', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='started_methods', to='field_monitoring_shared.Method', verbose_name='Method')),
                ('method_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='started_methods', to='field_monitoring_visits.VisitMethodType', verbose_name='Method Type')),
                ('visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='started_methods', to='field_monitoring_visits.Visit', verbose_name='Visit')),
            ],
        ),
    ]
