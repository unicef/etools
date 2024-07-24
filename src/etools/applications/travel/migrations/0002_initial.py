# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('partners', '0002_initial'),
        ('reports', '0002_initial'),
        ('field_monitoring_planning', '0003_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('locations', '0001_initial'),
        ('travel', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='supervisor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='supervised_itineraries', to=settings.AUTH_USER_MODEL, verbose_name='Supervisor'),
        ),
        migrations.AddField(
            model_name='trip',
            name='traveller',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itineraries', to=settings.AUTH_USER_MODEL, verbose_name='Traveller'),
        ),
        migrations.AddField(
            model_name='report',
            name='trip',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='report', to='travel.trip', verbose_name='Trip'),
        ),
        migrations.AddField(
            model_name='itineraryitem',
            name='monitoring_activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trip_itinerary_items', to='field_monitoring_planning.monitoringactivity'),
        ),
        migrations.AddField(
            model_name='itineraryitem',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itinerary_items', to='travel.trip', verbose_name='Trip'),
        ),
        migrations.AddField(
            model_name='activity',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='trip_activities', to='locations.location'),
        ),
        migrations.AddField(
            model_name='activity',
            name='monitoring_activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trip_activities', to='field_monitoring_planning.monitoringactivity'),
        ),
        migrations.AddField(
            model_name='activity',
            name='partner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trip_activities', to='partners.partnerorganization'),
        ),
        migrations.AddField(
            model_name='activity',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='trip_activities', to='reports.section'),
        ),
        migrations.AddField(
            model_name='activity',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='travel.trip', verbose_name='Trip'),
        ),
    ]
