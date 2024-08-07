# Generated by Django 3.2.19 on 2024-07-19 11:57

import datetime
from django.db import migrations, models
import django.utils.timezone
from django.utils.timezone import utc
import django_fsm
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('action_points', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonitoringActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('number', models.CharField(blank=True, editable=False, max_length=64, null=True, unique=True, verbose_name='Reference Number')),
                ('monitor_type', models.CharField(choices=[('staff', 'Staff'), ('tpm', 'TPM')], default='staff', max_length=10)),
                ('start_date', models.DateField(blank=True, null=True, verbose_name='Start Date')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='End Date')),
                ('status', django_fsm.FSMField(choices=[('draft', 'Draft'), ('checklist', 'Checklist'), ('review', 'Review'), ('assigned', 'Assigned'), ('data_collection', 'Data Collection'), ('report_finalization', 'Report Finalization'), ('submitted', 'Submitted'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=20, verbose_name='Status')),
                ('reject_reason', models.TextField(blank=True, verbose_name='Rejection reason')),
                ('report_reject_reason', models.TextField(blank=True, verbose_name='Report rejection reason')),
                ('cancel_reason', models.TextField(blank=True, verbose_name='Cancellation reason')),
            ],
            options={
                'verbose_name': 'Monitoring Activity',
                'verbose_name_plural': 'Monitoring Activities',
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='MonitoringActivityGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='QuestionTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('specific_details', models.TextField(blank=True, verbose_name='Specific Details To Probe')),
            ],
            options={
                'verbose_name': 'Question Template',
                'verbose_name_plural': 'Question Templates',
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='YearPlan',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('year', models.PositiveSmallIntegerField(primary_key=True, serialize=False)),
                ('prioritization_criteria', models.TextField(blank=True, verbose_name='Prioritization Criteria')),
                ('methodology_notes', models.TextField(blank=True, verbose_name='Methodology Notes & Standards')),
                ('target_visits', models.PositiveSmallIntegerField(blank=True, default=0, verbose_name='Target Visits For The Year')),
                ('modalities', models.TextField(blank=True, verbose_name='Modalities')),
                ('partner_engagement', models.TextField(blank=True, verbose_name='Partner Engagement')),
                ('other_aspects', models.TextField(blank=True, verbose_name='Other Aspects of the Field Monitoring Plan')),
            ],
            options={
                'verbose_name': 'Year Plan',
                'verbose_name_plural': 'Year Plans',
                'ordering': ('year',),
            },
        ),
        migrations.CreateModel(
            name='MonitoringActivityActionPoint',
            fields=[
            ],
            options={
                'verbose_name': 'Monitoring Activity Action Point',
                'verbose_name_plural': 'Monitoring Activity Action Points',
                'abstract': False,
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('action_points.actionpoint',),
        ),
    ]
