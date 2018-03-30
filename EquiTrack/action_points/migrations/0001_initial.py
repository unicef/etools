# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-03-30 11:39
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_fsm
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('partners', '0002_auto_20180326_1605'),
        ('users', '0001_initial'),
        ('reports', '0001_initial'),
        ('locations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActionPoint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('related_module', models.CharField(blank=True, choices=[('t2f', 'Trip Management'), ('tpm', 'Third Party Monitoring'), ('audit', 'Auditor Portal')], max_length=20, null=True)),
                ('related_object_id', models.IntegerField(blank=True, null=True)),
                ('status', django_fsm.FSMField(choices=[('open', 'Open'), ('completed', 'Completed')], default='open', max_length=10, protected=True, verbose_name='Status')),
                ('description', models.TextField(verbose_name='Description')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='Due Date')),
                ('high_priority', models.CharField(choices=[('yes', 'Yes'), ('no', 'No')], default='no', max_length=10, verbose_name='High Priority')),
                ('action_taken', models.TextField(blank=True, verbose_name='Action Taken')),
                ('date_of_complete', model_utils.fields.MonitorField(blank=True, default=django.utils.timezone.now, monitor='status', null=True, verbose_name='Date Action Point Completed', when=set(['completed']))),
                ('assigned_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Assigned By')),
                ('assigned_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_action_points', to=settings.AUTH_USER_MODEL, verbose_name='Assigned To')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_action_points', to=settings.AUTH_USER_MODEL, verbose_name='Author')),
                ('cp_output', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='reports.Result', verbose_name='CP Output')),
                ('intervention', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='partners.Intervention', verbose_name='PD/SSFA')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='locations.Location', verbose_name='Location')),
                ('office', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.Office', verbose_name='Office')),
                ('partner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='partners.PartnerOrganization', verbose_name='Partner')),
                ('related_content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.Section', verbose_name='Section')),
            ],
            options={
                'ordering': ('related_module', 'related_content_type', 'related_object_id'),
            },
        ),
    ]
