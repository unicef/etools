# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0002_initial'),
        ('t2f', '0001_initial'),
        ('publics', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='travelactivity',
            name='primary_traveler',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Primary Traveler'),
        ),
        migrations.AddField(
            model_name='travelactivity',
            name='result',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='reports.result', verbose_name='Result'),
        ),
        migrations.AddField(
            model_name='travelactivity',
            name='travels',
            field=models.ManyToManyField(related_name='activities', to='t2f.Travel', verbose_name='Travels'),
        ),
        migrations.AddField(
            model_name='travel',
            name='currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='publics.currency', verbose_name='Currency'),
        ),
        migrations.AddField(
            model_name='travel',
            name='office',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='reports.office', verbose_name='Office'),
        ),
        migrations.AddField(
            model_name='travel',
            name='section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='reports.section', verbose_name='Section'),
        ),
        migrations.AddField(
            model_name='travel',
            name='supervisor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Supervisor'),
        ),
        migrations.AddField(
            model_name='travel',
            name='traveler',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='travels', to=settings.AUTH_USER_MODEL, verbose_name='Traveller'),
        ),
        migrations.AddField(
            model_name='itineraryitem',
            name='airlines',
            field=models.ManyToManyField(related_name='_t2f_itineraryitem_airlines_+', to='publics.AirlineCompany', verbose_name='Airlines'),
        ),
        migrations.AddField(
            model_name='itineraryitem',
            name='dsa_region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='publics.dsaregion', verbose_name='DSA Region'),
        ),
        migrations.AddField(
            model_name='itineraryitem',
            name='travel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itinerary', to='t2f.travel', verbose_name='Travel'),
        ),
        migrations.AlterOrderWithRespectTo(
            name='itineraryitem',
            order_with_respect_to='travel',
        ),
    ]
