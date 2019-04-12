# Generated by Django 1.10.8 on 2018-03-26 16:05

import datetime

import django.db.models.deletion
import django.db.models.manager
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.utils.timezone import utc

import django_fsm
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0001_initial'),
        ('reports', '0001_initial'),
        ('tpmpartners', '0001_initial'),
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TPMActionPoint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('due_date', models.DateField(verbose_name='Due Date')),
                ('description', models.TextField(verbose_name='Description')),
                ('comments', models.TextField(blank=True, verbose_name='Comments')),
                ('status', models.CharField(choices=[('open', 'Open'), ('progress', 'In-Progress'), ('completed',
                                                                                                     'Completed'), ('cancelled', 'Cancelled')], default='open', max_length=9, verbose_name='Status')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='created_tpm_action_points', to=settings.AUTH_USER_MODEL, verbose_name='Assigned By')),
                ('person_responsible', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                         related_name='tpm_action_points', to=settings.AUTH_USER_MODEL, verbose_name='Person Responsible')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TPMActivity',
            fields=[
                ('activity_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE,
                                                      parent_link=True, primary_key=True, serialize=False, to='activities.Activity')),
                ('additional_information', models.TextField(blank=True, verbose_name='Additional Information')),
                ('is_pv', models.BooleanField(default=False, verbose_name='HACT Programmatic Visit')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='tpm_activities', to='reports.Section', verbose_name='Section')),
            ],
            options={
                'ordering': ['tpm_visit', 'id'],
                'verbose_name_plural': 'TPM Activities',
            },
            bases=('activities.activity',),
        ),
        migrations.CreateModel(
            name='TPMPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_type', models.CharField(max_length=30)),
                ('permission', models.CharField(choices=[('view', 'View'),
                                                         ('edit', 'Edit'), ('action', 'Action')], max_length=10)),
                ('permission_type', models.CharField(choices=[
                 ('allow', 'Allow'), ('disallow', 'Disallow')], default='allow', max_length=10)),
                ('target', models.CharField(max_length=100)),
                ('instance_status', models.CharField(max_length=32, verbose_name='Instance Status')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TPMVisit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(
                    1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('created', model_utils.fields.AutoCreatedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(
                    default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', django_fsm.FSMField(choices=[('draft', 'Draft'), ('assigned', 'Assigned'), ('cancelled', 'Cancelled'), ('tpm_accepted', 'TPM Accepted'), ('tpm_rejected', 'TPM Rejected'), (
                    'tpm_reported', 'TPM Reported'), ('tpm_report_rejected', 'Sent Back to TPM'), ('unicef_approved', 'UNICEF Approved')], default='draft', max_length=20, protected=True, verbose_name='Status')),
                ('reject_comment', models.TextField(blank=True, verbose_name='Request For More Information')),
                ('approval_comment', models.TextField(blank=True, verbose_name='Approval Comments')),
                ('visit_information', models.TextField(blank=True, verbose_name='Visit Information')),
                ('date_of_assigned', models.DateField(blank=True, null=True, verbose_name='Date of Assigned')),
                ('date_of_cancelled', models.DateField(blank=True, null=True, verbose_name='Date of Cancelled')),
                ('date_of_tpm_accepted', models.DateField(blank=True, null=True, verbose_name='Date of TPM Accepted')),
                ('date_of_tpm_rejected', models.DateField(blank=True, null=True, verbose_name='Date of TPM Rejected')),
                ('date_of_tpm_reported', models.DateField(blank=True, null=True, verbose_name='Date of TPM Reported')),
                ('date_of_tpm_report_rejected', models.DateField(
                    blank=True, null=True, verbose_name='Date of Sent Back to TPM')),
                ('date_of_unicef_approved', models.DateField(blank=True, null=True, verbose_name='Date of UNICEF Approved')),
                ('offices', models.ManyToManyField(blank=True, related_name='tpm_visits',
                                                   to='users.Office', verbose_name='Office(s) of UNICEF Focal Point(s)')),
                ('tpm_partner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                                  to='tpmpartners.TPMPartner', verbose_name='TPM Vendor')),
                ('tpm_partner_focal_points', models.ManyToManyField(blank=True, related_name='tpm_visits',
                                                                    to='tpmpartners.TPMPartnerStaffMember', verbose_name='TPM Focal Points')),
                ('unicef_focal_points', models.ManyToManyField(blank=True, related_name='tpm_visits',
                                                               to=settings.AUTH_USER_MODEL, verbose_name='UNICEF Focal Points')),
            ],
            options={
                'abstract': False,
                'ordering': ('id',),
                'verbose_name': 'TPM Visit',
                'verbose_name_plural': 'TPM Visits'
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='TPMVisitReportRejectComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rejected_at', models.DateTimeField(auto_now_add=True, verbose_name='Rejected At')),
                ('reject_reason', models.TextField(verbose_name='Reason of Rejection')),
                ('tpm_visit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                related_name='report_reject_comments', to='tpm.TPMVisit', verbose_name='Visit')),
            ],
            options={
                'ordering': ['tpm_visit', 'id'],
                'verbose_name_plural': 'Report Reject Comments',
            },
        ),
        migrations.AlterUniqueTogether(
            name='tpmpermission',
            unique_together=set([('user_type', 'instance_status', 'target', 'permission_type')]),
        ),
        migrations.AddField(
            model_name='tpmactivity',
            name='tpm_visit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='tpm_activities', to='tpm.TPMVisit', verbose_name='Visit'),
        ),
        migrations.AddField(
            model_name='tpmactionpoint',
            name='tpm_visit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='action_points', to='tpm.TPMVisit', verbose_name='Visit'),
        ),
    ]
