# Generated by Django 2.2.7 on 2020-08-07 12:07

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0051_auto_20200722_1257'),
        ('reports', '0027_auto_20200728_1339'),
    ]

    operations = [
        migrations.CreateModel(
            name='InterventionTimeFrame',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('start_date', models.DateField(verbose_name='Start Date')),
                ('end_date', models.DateField(verbose_name='End Date')),
                ('intervention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quarters', to='partners.Intervention', verbose_name='Intervention')),
                ('quarter', models.PositiveSmallIntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.DeleteModel(
            name='InterventionActivityTimeFrame',
        ),
        migrations.AddField(
            model_name='interventionactivity',
            name='time_frames',
            field=models.ManyToManyField(blank=True, to='reports.InterventionTimeFrame', verbose_name='Time Frames Enabled', related_name='activities',),
        ),
        migrations.AlterModelOptions(
            name='interventiontimeframe',
            options={'ordering': ('intervention', 'start_date')},
        ),
    ]
