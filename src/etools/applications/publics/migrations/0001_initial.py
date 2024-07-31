# Generated by Django 3.2.19 on 2024-07-19 11:57

import datetime
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
from django.utils.timezone import utc


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AirlineCompany',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('code', models.IntegerField(verbose_name='Code')),
                ('iata', models.CharField(max_length=3, verbose_name='IATA')),
                ('icao', models.CharField(max_length=3, verbose_name='ICAO')),
                ('country', models.CharField(max_length=255, verbose_name='Country')),
            ],
            options={
                'verbose_name_plural': 'Airline Companies',
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='BusinessArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('code', models.CharField(max_length=32, verbose_name='Code')),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='BusinessRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('name', models.CharField(max_length=16, verbose_name='Name')),
                ('code', models.CharField(max_length=2, verbose_name='Code')),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('name', models.CharField(max_length=64, verbose_name='Name')),
                ('long_name', models.CharField(max_length=128, verbose_name='Long Name')),
                ('vision_code', models.CharField(max_length=3, null=True, unique=True, verbose_name='Vision Code')),
                ('iso_2', models.CharField(default='', max_length=2, verbose_name='ISO code 2')),
                ('iso_3', models.CharField(default='', max_length=3, verbose_name='ISO code 3')),
                ('dsa_code', models.CharField(default='', max_length=3, verbose_name='DSA Code')),
                ('valid_from', models.DateField(null=True, verbose_name='Valid From')),
                ('valid_to', models.DateField(null=True, verbose_name='Valid To')),
                ('business_area', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='countries', to='publics.businessarea', verbose_name='Business Area')),
            ],
            options={
                'verbose_name_plural': 'Countries',
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('code', models.CharField(max_length=5, verbose_name='Code')),
                ('decimal_places', models.PositiveIntegerField(default=0, verbose_name='Decimal Places')),
            ],
            options={
                'verbose_name_plural': 'Currencies',
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='TravelExpenseType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('title', models.CharField(max_length=128, verbose_name='Title')),
                ('vendor_number', models.CharField(max_length=128, verbose_name='Vendor Number')),
                ('rank', models.PositiveIntegerField(default=100, verbose_name='Rank')),
            ],
            options={
                'ordering': ('rank', 'title'),
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='TravelAgent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('code', models.CharField(max_length=128, verbose_name='Code')),
                ('city', models.CharField(default='', max_length=128, verbose_name='City')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='publics.country', verbose_name='Country')),
                ('expense_type', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='travel_agent', to='publics.travelexpensetype', verbose_name='Expense Type')),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('valid_from', models.DateField(verbose_name='Valid From')),
                ('valid_to', models.DateField(verbose_name='Valid To')),
                ('x_rate', models.DecimalField(decimal_places=5, max_digits=10, verbose_name='X Rate')),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exchange_rates', to='publics.currency', verbose_name='Currency')),
            ],
            options={
                'ordering': ('valid_from',),
            },
            managers=[
                ('admin_objects', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='DSARegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, tzinfo=utc), verbose_name='Deleted At')),
                ('area_name', models.CharField(max_length=120, verbose_name='Area Name')),
                ('area_code', models.CharField(max_length=3, verbose_name='Area Code')),
                ('user_defined', models.BooleanField(default=False, verbose_name='Defined User')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dsa_regions', to='publics.country', verbose_name='Country')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='country',
            name='currency',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='publics.currency', verbose_name='Currency'),
        ),
        migrations.AddField(
            model_name='businessarea',
            name='default_currency',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='publics.currency', verbose_name='Default Currency'),
        ),
        migrations.AddField(
            model_name='businessarea',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='business_areas', to='publics.businessregion', verbose_name='Region'),
        ),
        migrations.CreateModel(
            name='DSARate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_from_date', models.DateField(verbose_name='Effective From Date')),
                ('effective_to_date', models.DateField(default=datetime.date(2999, 12, 31), verbose_name='Effective To Date')),
                ('dsa_amount_usd', models.DecimalField(decimal_places=4, max_digits=20, verbose_name='DSA amount USD')),
                ('dsa_amount_60plus_usd', models.DecimalField(decimal_places=4, max_digits=20, verbose_name='DSA amount 60 plus USD')),
                ('dsa_amount_local', models.DecimalField(decimal_places=4, max_digits=20, verbose_name='DSA amount local')),
                ('dsa_amount_60plus_local', models.DecimalField(decimal_places=4, max_digits=20, verbose_name='DSA Amount 60 plus local')),
                ('room_rate', models.DecimalField(decimal_places=4, max_digits=20, verbose_name='Zoom Rate')),
                ('finalization_date', models.DateField(verbose_name='Finalization Date')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rates', to='publics.dsaregion', verbose_name='Region')),
            ],
            options={
                'unique_together': {('region', 'effective_to_date')},
            },
        ),
    ]
