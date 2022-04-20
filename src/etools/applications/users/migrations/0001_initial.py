# Generated by Django 3.2.6 on 2022-04-20 16:15

from decimal import Decimal
from django.conf import settings
import django.contrib.auth.models
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_tenants.postgresql_backend.base
import etools.applications.users.models
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('publics', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('username', models.CharField(max_length=256, unique=True, verbose_name='username')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('middle_name', models.CharField(blank=True, max_length=50, verbose_name='middle_name')),
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
                ('schema_name', models.CharField(db_index=True, max_length=63, unique=True, validators=[django_tenants.postgresql_backend.base._check_schema_name])),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('country_short_code', models.CharField(blank=True, default='', max_length=10, verbose_name='UNICEF Country Reference Code')),
                ('iso3_code', models.CharField(blank=True, default='', max_length=10, verbose_name='ISO3 Code')),
                ('long_name', models.CharField(blank=True, default='', max_length=255, verbose_name='Long Name')),
                ('business_area_code', models.CharField(blank=True, default='', max_length=10, verbose_name='Business Area Code')),
                ('latitude', models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, validators=[django.core.validators.MinValueValidator(Decimal('-90')), django.core.validators.MaxValueValidator(Decimal('90'))], verbose_name='Latitude')),
                ('longitude', models.DecimalField(blank=True, decimal_places=5, max_digits=8, null=True, validators=[django.core.validators.MinValueValidator(Decimal('-180')), django.core.validators.MaxValueValidator(Decimal('180'))], verbose_name='Longitude')),
                ('initial_zoom', models.IntegerField(default=8, verbose_name='Initial Zoom')),
                ('vision_sync_enabled', models.BooleanField(default=True, verbose_name='Vision Sync Enabled')),
                ('vision_last_synced', models.DateTimeField(blank=True, null=True, verbose_name='Vision Last Sync')),
                ('custom_dashboards', models.JSONField(default=etools.applications.users.models.custom_dashboards_default, verbose_name='Custom Dashboards')),
                ('local_currency', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workspaces', to='publics.currency', verbose_name='Local Currency')),
            ],
            options={
                'verbose_name_plural': 'Countries',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Office',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=254, verbose_name='Name')),
                ('zonal_chief', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='offices_old', to=settings.AUTH_USER_MODEL, verbose_name='Chief')),
            ],
            options={
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='WorkspaceCounter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('travel_reference_number_counter', models.PositiveIntegerField(default=1, verbose_name='Travel Reference Number Counter')),
                ('travel_invoice_reference_number_counter', models.PositiveIntegerField(default=1, verbose_name='Travel Invoice Reference Number Counter')),
                ('workspace', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='counters', to='users.country', verbose_name='Workspace')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('guid', models.CharField(max_length=40, null=True, unique=True, verbose_name='GUID')),
                ('_partner_staff_member', models.IntegerField(blank=True, null=True, verbose_name='Partner Staff Member')),
                ('job_title', models.CharField(blank=True, max_length=255, null=True, verbose_name='Job Title')),
                ('phone_number', models.CharField(blank=True, max_length=255, null=True, verbose_name='Phone Number')),
                ('staff_id', models.CharField(blank=True, max_length=32, null=True, verbose_name='Staff ID')),
                ('org_unit_code', models.CharField(blank=True, max_length=32, null=True, verbose_name='Org Unit Code')),
                ('org_unit_name', models.CharField(blank=True, max_length=64, null=True, verbose_name='Org Unit Name')),
                ('post_number', models.CharField(blank=True, max_length=32, null=True, verbose_name='Post Number')),
                ('post_title', models.CharField(blank=True, max_length=64, null=True, verbose_name='Post Title')),
                ('vendor_number', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='Vendor Number')),
                ('countries_available', models.ManyToManyField(blank=True, related_name='accessible_by', to='users.Country', verbose_name='Countries Available')),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.country', verbose_name='Country')),
                ('country_override', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='country_override', to='users.country', verbose_name='Country Override')),
                ('office', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.office', verbose_name='Office')),
                ('oic', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='OIC')),
                ('supervisor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supervisee', to=settings.AUTH_USER_MODEL, verbose_name='Supervisor')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name_plural': 'User Profile',
            },
        ),
        migrations.AddField(
            model_name='country',
            name='offices',
            field=models.ManyToManyField(blank=True, related_name='offices', to='users.Office', verbose_name='Offices'),
        ),
    ]
