# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_fsm
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('activity_date', models.DateField(verbose_name='Activity Date')),
                ('activity_type', models.CharField(blank=True, choices=[('Monitoring Activity', 'Monitoring Activity'), ('Technical Support', 'Technical Support'), ('Meeting', 'Meeting'), ('Staff Development', 'Staff Development'), ('Staff Entitlement', 'Staff Entitlement')], default='Monitoring Activity', max_length=64, verbose_name='Activity Type')),
            ],
            options={
                'verbose_name': 'Activity',
                'verbose_name_plural': 'Activities',
                'ordering': ['-activity_date'],
            },
        ),
        migrations.CreateModel(
            name='ItineraryItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('start_date', models.DateField(blank=True, null=True, verbose_name='Start Date')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='End Date')),
                ('travel_method', models.CharField(blank=True, max_length=150, verbose_name='Travel Method')),
                ('destination', models.CharField(blank=True, max_length=150, verbose_name='Destination')),
            ],
            options={
                'verbose_name': 'Itinerary Item',
                'verbose_name_plural': 'Itinerary Items',
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('narrative', models.TextField(blank=True, verbose_name='Narrative')),
            ],
            options={
                'verbose_name': 'Report',
                'verbose_name_plural': 'Reports',
            },
        ),
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('reference_number', models.CharField(max_length=100, unique=True, verbose_name='Reference Number')),
                ('status', django_fsm.FSMField(choices=[('draft', 'Draft'), ('submission', 'Submission Review'), ('submitted', 'Submitted'), ('rejected', 'Rejected'), ('approved', 'Approved'), ('review', 'Review'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=30, verbose_name='Status')),
                ('not_as_planned', models.BooleanField(default=False, verbose_name='Trip completed not as planned')),
                ('title', models.CharField(blank=True, max_length=120, verbose_name='Title')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('start_date', models.DateField(blank=True, null=True, verbose_name='Start Date')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='End Date')),
                ('additional_notes', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('user_info_text', models.JSONField(blank=True, default=dict, verbose_name='User Information Text')),
                ('office', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='trips', to='reports.office', verbose_name='Office')),
                ('section', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='trips', to='reports.section', verbose_name='Section')),
            ],
            options={
                'verbose_name': 'Trip',
                'verbose_name_plural': 'Trips',
                'ordering': ('-start_date',),
            },
        ),
        migrations.CreateModel(
            name='TripStatusHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submission', 'Submission Review'), ('submitted', 'Submitted'), ('rejected', 'Rejected'), ('approved', 'Approved'), ('review', 'Review'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], max_length=30)),
                ('comment', models.TextField(blank=True)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='travel.trip', verbose_name='Trip')),
            ],
            options={
                'verbose_name': 'Trip Status History',
                'verbose_name_plural': 'Trip Status History',
                'ordering': ('-created',),
            },
        ),
    ]
