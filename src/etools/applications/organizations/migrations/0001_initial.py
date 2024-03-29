# Generated by Django 3.2.6 on 2022-07-19 10:39
from django.core.management import call_command
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


def init_organizations(apps, schema_editor):
    call_command('loaddata', 'organizations')


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('name', models.CharField(blank=True, max_length=255, null=True, verbose_name='Vendor Name')),
                ('vendor_number', models.CharField(max_length=30, unique=True, verbose_name='Vendor Number')),
                ('organization_type', models.CharField(blank=True, null=True, choices=[('Bilateral / Multilateral', 'Bilateral / Multilateral'), ('Civil Society Organization', 'Civil Society Organization'), ('Government', 'Government'), ('UN Agency', 'UN Agency')], max_length=50, verbose_name='Organization Type')),
                ('cso_type', models.CharField(blank=True, choices=[('International', 'International'), ('National', 'National'), ('Community Based Organization', 'Community Based Organization'), ('Academic Institution', 'Academic Institution')], max_length=50, null=True, verbose_name='CSO Type')),
                ('short_name', models.CharField(blank=True, max_length=50, null=True, verbose_name='Short Name')),
                ('other', models.JSONField(blank=True, null=True, verbose_name='Other Details')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='organizations.organization', verbose_name='Parent Organization')),
            ],
            options={
                'verbose_name': 'Organization',
                'verbose_name_plural': 'Organizations',
                'ordering': ('name',),
                'unique_together': {('name', 'vendor_number')},
            },
        ),
        migrations.RunPython(init_organizations, migrations.RunPython.noop)
    ]
