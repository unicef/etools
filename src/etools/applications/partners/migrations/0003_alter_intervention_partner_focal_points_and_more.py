# Generated by Django 4.2.3 on 2024-07-24 19:12

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('partners', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intervention',
            name='partner_focal_points',
            field=models.ManyToManyField(blank=True, related_name='interventions_focal_points+', to=settings.AUTH_USER_MODEL, verbose_name='CSO Authorized Officials'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='unicef_focal_points',
            field=models.ManyToManyField(blank=True, related_name='unicef_interventions_focal_points+', to=settings.AUTH_USER_MODEL, verbose_name='UNICEF Focal Points'),
        ),
        migrations.AlterField(
            model_name='interventionreview',
            name='prc_officers',
            field=models.ManyToManyField(blank=True, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='PRC Officers'),
        ),
    ]