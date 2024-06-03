# Generated by Django 3.2.19 on 2024-06-03 12:31

from django.db import migrations, models
import django.utils.timezone
import django_fsm
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ActionPoint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', django_fsm.FSMField(choices=[('open', 'Open'), ('completed', 'Completed')], default='open', max_length=10, protected=True, verbose_name='Status')),
                ('description', models.TextField(verbose_name='Description')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='Due Date')),
                ('high_priority', models.BooleanField(default=False, verbose_name='High Priority')),
                ('date_of_completion', model_utils.fields.MonitorField(blank=True, default=None, monitor='status', null=True, verbose_name='Date Action Point Completed', when={'completed'})),
                ('date_of_verification', model_utils.fields.MonitorField(blank=True, default=None, monitor='verified_by', null=True, verbose_name='Date Action Point Verified')),
                ('reference_number', models.CharField(max_length=100, null=True, verbose_name='Reference Number')),
                ('is_adequate', models.BooleanField(default=False, verbose_name='Is Adequate')),
            ],
            options={
                'verbose_name': 'Action Point',
                'verbose_name_plural': 'Action Points',
                'ordering': ('id',),
            },
        ),
    ]
