# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0006_auto_20160229_1545'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0024_auto_20160915_2222'),
        ('partners', '0072_partnerorganization_hact_values'),
        ('users', '0014_auto_20160816_2228'),
        ('funds', '0005_auto_20160910_0836'),
    ]

    operations = [
        migrations.CreateModel(
            name='AirlineCompany',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('code', models.CharField(max_length=12)),
            ],
        ),
        migrations.CreateModel(
            name='Clearances',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('medical_clearance', models.NullBooleanField(default=None, choices=[(None, 'N/A'), (True, 'Yes'), (False, 'No')])),
                ('security_clearance', models.NullBooleanField(default=None, choices=[(None, 'N/A'), (True, 'Yes'), (False, 'No')])),
                ('security_course', models.NullBooleanField(default=None, choices=[(None, 'N/A'), (True, 'Yes'), (False, 'No')])),
            ],
        ),
        migrations.CreateModel(
            name='CostAssignment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('share', models.PositiveIntegerField()),
                ('grant', models.ForeignKey(to='funds.Grant')),
            ],
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('iso_4217', models.CharField(max_length=3)),
            ],
        ),
        migrations.CreateModel(
            name='Deduction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField()),
                ('breakfast', models.BooleanField(default=False)),
                ('lunch', models.BooleanField(default=False)),
                ('dinner', models.BooleanField(default=False)),
                ('accomodation', models.BooleanField(default=False)),
                ('no_dsa', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=64)),
                ('amount', models.DecimalField(max_digits=10, decimal_places=4)),
                ('account_currency', models.ForeignKey(related_name='+', to='et2f.Currency')),
                ('document_currency', models.ForeignKey(related_name='+', to='et2f.Currency')),
            ],
        ),
        migrations.CreateModel(
            name='IteneraryItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('origin', models.CharField(max_length=255)),
                ('destination', models.CharField(max_length=255)),
                ('departure_date', models.DateTimeField()),
                ('arrival_date', models.DateTimeField()),
                ('dsa_region', models.CharField(max_length=255)),
                ('overnight_travel', models.BooleanField(default=False)),
                ('mode_of_travel', models.CharField(max_length=255)),
                ('airline', models.ForeignKey(to='et2f.AirlineCompany')),
            ],
        ),
        migrations.CreateModel(
            name='Travel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('status', models.CharField(blank=True, max_length=10, null=True, choices=[('planned', 'Planned'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('completed', 'Completed'), ('cancelled', 'Cancelled')])),
                ('start_date', models.DateTimeField(null=True, blank=True)),
                ('end_date', models.DateTimeField(null=True, blank=True)),
                ('purpose', models.CharField(max_length=120, null=True, blank=True)),
                ('international_travel', models.NullBooleanField(default=False)),
                ('ta_required', models.NullBooleanField(default=True)),
                ('reference_number', models.CharField(max_length=12, null=True, blank=True)),
                ('office', models.ForeignKey(related_name='+', blank=True, to='users.Office', null=True)),
                ('section', models.ForeignKey(related_name='+', blank=True, to='users.Section', null=True)),
                ('supervisor', models.ForeignKey(related_name='+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('traveller', models.ForeignKey(related_name='travels', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='TravelActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('travel_type', models.CharField(max_length=64)),
                ('location', models.ForeignKey(related_name='+', to='locations.Location')),
                ('partner', models.ForeignKey(related_name='+', to='partners.PartnerOrganization')),
                ('partnership', models.ForeignKey(to='partners.PCA')),
                ('result', models.ForeignKey(related_name='+', to='reports.Result')),
                ('travel', models.ForeignKey(related_name='activities', to='et2f.Travel')),
            ],
        ),
        migrations.AddField(
            model_name='iteneraryitem',
            name='travel',
            field=models.ForeignKey(related_name='itinerary', to='et2f.Travel'),
        ),
        migrations.AddField(
            model_name='expense',
            name='travel',
            field=models.ForeignKey(related_name='expenses', to='et2f.Travel'),
        ),
        migrations.AddField(
            model_name='deduction',
            name='travel',
            field=models.ForeignKey(related_name='deductions', to='et2f.Travel'),
        ),
        migrations.AddField(
            model_name='costassignment',
            name='travel',
            field=models.ForeignKey(related_name='cost_assignments', to='et2f.Travel'),
        ),
        migrations.AddField(
            model_name='costassignment',
            name='wbs',
            field=models.ForeignKey(related_name='+', to='reports.Result'),
        ),
        migrations.AddField(
            model_name='clearances',
            name='travel',
            field=models.OneToOneField(related_name='clearances', to='et2f.Travel'),
        ),
    ]
