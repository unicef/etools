# Generated by Django 1.10.8 on 2018-04-27 10:25
from __future__ import unicode_literals

from decimal import Decimal

import django.contrib.auth.models
import django.core.validators
import django.db.migrations.operations.special
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import django_tenants.postgresql_backend.base


class Migration(migrations.Migration):

    replaces = [('users', '0001_initial'), ('users', '0002_auto_20180329_2123'), ('users', '0003_fix_null_values'), ('users', '0004_make_not_nullable'), ('users', '0005_auto_20180419_2113'), ('users', '0006_auto_20180423_1515'), ('users', '0007_user')]

    initial = True

    dependencies = [
        ('publics', '0001_initial'),
        ('auth', '0008_alter_user_username_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=256, unique=True, verbose_name='username')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=30, verbose_name='last name')),
                ('date_joined', models.DateTimeField(auto_now_add=True, verbose_name='date joined')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('is_staff', models.BooleanField(default=False, verbose_name='staff')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='superuser')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                 ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'db_table': 'auth_user',
                'ordering': ['first_name'],
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain_url', models.CharField(max_length=128, unique=True)),
                ('schema_name', models.CharField(max_length=63, unique=True, validators=[django_tenants.postgresql_backend.base._check_schema_name])),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('country_short_code', models.CharField(blank=True, max_length=10, null=True, verbose_name='Short Code')),
                ('long_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Long Name')),
                ('business_area_code', models.CharField(blank=True, max_length=10, null=True, verbose_name='Business Area Code')),
                ('latitude', models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, validators=[django.core.validators.MinValueValidator(Decimal('-90')), django.core.validators.MaxValueValidator(Decimal('90'))], verbose_name='Latitude')),
                ('longitude', models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, validators=[django.core.validators.MinValueValidator(Decimal('-180')), django.core.validators.MaxValueValidator(Decimal('180'))], verbose_name='Longitude')),
                ('initial_zoom', models.IntegerField(default=8, verbose_name='Initial Zoom')),
                ('vision_sync_enabled', models.BooleanField(default=True, verbose_name='Vision Sync Enabled')),
                ('vision_last_synced', models.DateTimeField(blank=True, null=True, verbose_name='Vision Last Sync')),
                ('threshold_tre_usd', models.DecimalField(decimal_places=4, default=None, max_digits=20, null=True, verbose_name='Threshold TRE (USD)')),
                ('threshold_tae_usd', models.DecimalField(decimal_places=4, default=None, max_digits=20, null=True, verbose_name='Threshold TAE (USD)')),
                ('local_currency', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workspaces', to='publics.Currency', verbose_name='Local Currency')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'Countries',
            },
        ),
        migrations.CreateModel(
            name='Office',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=254, verbose_name='Name')),
                ('zonal_chief', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='offices', to=settings.AUTH_USER_MODEL, verbose_name='Chief')),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True, verbose_name='Name')),
                ('code', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='Code')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('guid', models.CharField(max_length=40, null=True, unique=True, verbose_name='GUID')),
                ('partner_staff_member', models.IntegerField(blank=True, null=True, verbose_name='Partner Staff Member')),
                ('job_title', models.CharField(blank=True, max_length=255, null=True, verbose_name='Job Title')),
                ('phone_number', models.CharField(blank=True, max_length=32, null=True, verbose_name='Phone Number')),
                ('staff_id', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='Staff ID')),
                ('org_unit_code', models.CharField(blank=True, max_length=32, null=True, verbose_name='Org Unit Code')),
                ('org_unit_name', models.CharField(blank=True, max_length=64, null=True, verbose_name='Org Unit Name')),
                ('post_number', models.CharField(blank=True, max_length=32, null=True, verbose_name='Post Number')),
                ('post_title', models.CharField(blank=True, max_length=64, null=True, verbose_name='Post Title')),
                ('vendor_number', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='Vendor Number')),
                ('section_code', models.CharField(blank=True, max_length=32, null=True, verbose_name='Section Code')),
                ('countries_available', models.ManyToManyField(blank=True, related_name='accessible_by', to='users.Country', verbose_name='Countries Available')),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.Country', verbose_name='Country')),
                ('country_override', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='country_override', to='users.Country', verbose_name='Country Override')),
                ('office', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.Office', verbose_name='Office')),
                ('oic', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='OIC')),
                ('supervisor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supervisee', to=settings.AUTH_USER_MODEL, verbose_name='Supervisor')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
        ),
        migrations.CreateModel(
            name='WorkspaceCounter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('travel_reference_number_counter', models.PositiveIntegerField(default=1, verbose_name='Travel Reference Number Counter')),
                ('travel_invoice_reference_number_counter', models.PositiveIntegerField(default=1, verbose_name='Travel Invoice Reference Number Counter')),
                ('workspace', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='counters', to='users.Country', verbose_name='Workspace')),
            ],
        ),
        migrations.AddField(
            model_name='country',
            name='offices',
            field=models.ManyToManyField(related_name='offices', to='users.Office', verbose_name='Offices'),
        ),
        migrations.AlterField(
            model_name='country',
            name='business_area_code',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='Business Area Code'),
        ),
        migrations.AlterField(
            model_name='country',
            name='country_short_code',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='Short Code'),
        ),
        migrations.AlterField(
            model_name='country',
            name='long_name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Long Name'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='job_title',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Job Title'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='org_unit_code',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Org Unit Code'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='org_unit_name',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Org Unit Name'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Phone Number'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='post_number',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Post Number'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='post_title',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Post Title'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='section_code',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Section Code'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='job_title',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Job Title'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='org_unit_code',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Org Unit Code'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='org_unit_name',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Org Unit Name'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Phone Number'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='post_number',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Post Number'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='post_title',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Post Title'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='section_code',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Section Code'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='staff_id',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Staff ID'),
        ),
    ]
