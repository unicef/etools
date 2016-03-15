# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import smart_selects.db_fields
import trips.models
import EquiTrack.mixins
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
        ('locations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('funds', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActionPoint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=254)),
                ('due_date', models.DateField()),
                ('actions_taken', models.TextField(null=True, blank=True)),
                ('completed_date', models.DateField(null=True, blank=True)),
                ('comments', models.TextField(null=True, blank=True)),
                ('status', models.CharField(max_length=254, null=True, verbose_name=b'Status', choices=[(b'closed', b'Closed'), (b'ongoing', b'On-going'), (b'open', b'Open'), (b'cancelled', b'Cancelled')])),
                ('created_date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('report', models.FileField(upload_to=trips.models.get_report_filename)),
                ('object_id', models.PositiveIntegerField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TravelRoutes',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('origin', models.CharField(max_length=254)),
                ('destination', models.CharField(max_length=254)),
                ('depart', models.DateTimeField()),
                ('arrive', models.DateTimeField()),
                ('remarks', models.CharField(max_length=254, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Travel Itinerary',
                'verbose_name_plural': 'Travel Itinerary',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default='planned', max_length=32L, choices=[('planned', 'Planned'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('completed', 'Completed'), ('cancelled', 'Cancelled')])),
                ('cancelled_reason', models.CharField(help_text=b'Please provide a reason if the mission is cancelled', max_length=254, null=True, blank=True)),
                ('purpose_of_travel', models.CharField(max_length=254)),
                ('travel_type', models.CharField(default='programme_monitoring', max_length=32L, choices=[('programme_monitoring', 'PROGRAMMATIC VISIT'), ('spot_check', 'SPOT CHECK'), ('advocacy', 'ADVOCACY'), ('technical_support', 'TECHNICAL SUPPORT'), ('meeting', 'MEETING'), ('staff_development', 'STAFF DEVELOPMENT'), ('staff_entitlement', 'STAFF ENTITLEMENT')])),
                ('security_clearance_required', models.BooleanField(default=False, help_text=b'Do you need security clarance for this trip?')),
                ('international_travel', models.BooleanField(default=False, help_text=b'International travel will require approval from the representative')),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
                ('main_observations', models.TextField(null=True, blank=True)),
                ('constraints', models.TextField(null=True, blank=True)),
                ('lessons_learned', models.TextField(null=True, blank=True)),
                ('opportunities', models.TextField(null=True, blank=True)),
                ('ta_required', models.BooleanField(default=False, help_text=b'Is a Travel Authorisation (TA) is required?')),
                ('ta_drafted', models.BooleanField(default=False, help_text=b'Has the TA been drafted in vision if applicable?')),
                ('ta_drafted_date', models.DateField(null=True, blank=True)),
                ('ta_reference', models.CharField(max_length=254, null=True, blank=True)),
                ('transport_booked', models.BooleanField(default=False)),
                ('security_granted', models.BooleanField(default=False)),
                ('approved_by_supervisor', models.BooleanField(default=False)),
                ('date_supervisor_approved', models.DateField(null=True, blank=True)),
                ('approved_by_budget_owner', models.BooleanField(default=False)),
                ('date_budget_owner_approved', models.DateField(null=True, blank=True)),
                ('approved_by_human_resources', models.NullBooleanField(default=None, choices=[(None, b'N/A'), (True, b'Yes'), (False, b'No')], help_text=b'HR must approve all trips relating to training and staff development', verbose_name=b'Certified by human resources')),
                ('date_human_resources_approved', models.DateField(null=True, blank=True)),
                ('representative_approval', models.NullBooleanField(default=None, choices=[(None, b'N/A'), (True, b'Yes'), (False, b'No')])),
                ('date_representative_approved', models.DateField(null=True, blank=True)),
                ('approved_date', models.DateField(null=True, blank=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('approved_email_sent', models.BooleanField(default=False)),
                ('ta_trip_took_place_as_planned', models.BooleanField(default=False, help_text=b'I certify that the travel took place exactly as per the attached Travel Authorization and that there were no changes to the itinerary', verbose_name=b'Ta trip took place as attached')),
                ('ta_trip_repay_travel_allowance', models.BooleanField(default=False, help_text=b'I certify that I will repay any travel allowance to which I am not entitled')),
                ('ta_trip_final_claim', models.BooleanField(default=False, help_text=b'I authorize UNICEF to treat this as the FINAL Claim')),
                ('budget_owner', models.ForeignKey(related_name='budgeted_trips', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('human_resources', models.ForeignKey(related_name='certified_trips', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['-created_date'],
            },
            bases=(EquiTrack.mixins.AdminURLMixin, models.Model),
        ),
        migrations.CreateModel(
            name='TripFunds',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.PositiveIntegerField(verbose_name=b'Percentage (%)')),
                ('grant', models.ForeignKey(to='funds.Grant')),
                ('trip', models.ForeignKey(to='trips.Trip')),
                ('wbs', models.ForeignKey(to='reports.WBS')),
            ],
            options={
                'verbose_name': 'Funding',
                'verbose_name_plural': 'Funding',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TripLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('governorate', models.ForeignKey(to='locations.Governorate')),
                ('locality', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'region', chained_field=b'region', blank=True, auto_choose=True, to='locations.Locality', null=True)),
                ('location', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'locality', chained_field=b'locality', blank=True, to='locations.Location', null=True)),
                ('region', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'governorate', chained_field=b'governorate', auto_choose=True, to='locations.Region')),
                ('trip', models.ForeignKey(to='trips.Trip')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
