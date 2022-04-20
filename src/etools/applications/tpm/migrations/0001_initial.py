# Generated by Django 3.2.6 on 2022-04-20 16:15

import datetime
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
from django.utils.timezone import utc
import django.utils.timezone
import django_fsm
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('activities', '0002_initial'),
        ('action_points', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TPMActivity',
            fields=[
                ('activity_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='activities.activity')),
                ('additional_information', models.TextField(blank=True, verbose_name='Additional Information')),
                ('is_pv', models.BooleanField(default=False, verbose_name='HACT Programmatic Visit')),
            ],
            options={
                'verbose_name_plural': 'TPM Activities',
                'ordering': ['tpm_visit', 'id'],
            },
            bases=('activities.activity',),
        ),
        migrations.CreateModel(
            name='TPMVisit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('status', django_fsm.FSMField(choices=[('draft', 'Draft'), ('assigned', 'Assigned'), ('cancelled', 'Cancelled'), ('tpm_accepted', 'TPM Accepted'), ('tpm_rejected', 'TPM Rejected'), ('tpm_reported', 'TPM Reported'), ('tpm_report_rejected', 'Sent Back to TPM'), ('unicef_approved', 'UNICEF Approved')], default='draft', max_length=20, protected=True, verbose_name='Status')),
                ('cancel_comment', models.TextField(blank=True, verbose_name='Cancel Comment')),
                ('reject_comment', models.TextField(blank=True, verbose_name='Reason for Rejection')),
                ('approval_comment', models.TextField(blank=True, verbose_name='Approval Comments')),
                ('visit_information', models.TextField(blank=True, verbose_name='Visit Information')),
                ('date_of_assigned', models.DateField(blank=True, null=True, verbose_name='Date of Assigned')),
                ('date_of_cancelled', models.DateField(blank=True, null=True, verbose_name='Date of Cancelled')),
                ('date_of_tpm_accepted', models.DateField(blank=True, null=True, verbose_name='Date of TPM Accepted')),
                ('date_of_tpm_rejected', models.DateField(blank=True, null=True, verbose_name='Date of TPM Rejected')),
                ('date_of_tpm_reported', models.DateField(blank=True, null=True, verbose_name='Date of TPM Reported')),
                ('date_of_tpm_report_rejected', models.DateField(blank=True, null=True, verbose_name='Date of Sent Back to TPM')),
                ('date_of_unicef_approved', models.DateField(blank=True, null=True, verbose_name='Date of UNICEF Approved')),
            ],
            options={
                'verbose_name': 'TPM Visit',
                'verbose_name_plural': 'TPM Visits',
                'ordering': ('id',),
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='TPMActionPoint',
            fields=[
            ],
            options={
                'verbose_name': 'TPM Action Point',
                'verbose_name_plural': 'TPM Action Points',
                'abstract': False,
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('action_points.actionpoint',),
        ),
        migrations.CreateModel(
            name='TPMVisitReportRejectComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rejected_at', models.DateTimeField(auto_now_add=True, verbose_name='Rejected At')),
                ('reject_reason', models.TextField(verbose_name='Reason for Rejection')),
                ('tpm_visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='report_reject_comments', to='tpm.tpmvisit', verbose_name='Visit')),
            ],
            options={
                'verbose_name_plural': 'Report Reject Comments',
                'ordering': ['tpm_visit', 'id'],
            },
        ),
    ]
