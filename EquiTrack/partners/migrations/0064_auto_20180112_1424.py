# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-01-12 14:24
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0063_auto_20171221_1447'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agreement',
            name='partner_manager',
            field=smart_selects.db_fields.ChainedForeignKey(blank=True, chained_field='partner', chained_model_field='partner', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agreements_signed', to='partners.PartnerStaffMember', verbose_name='Signed by partner'),
        ),
        migrations.AlterField(
            model_name='governmentintervention',
            name='country_programme',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_query_name='government_interventions', to='reports.CountryProgramme'),
        ),
        migrations.AlterField(
            model_name='governmentintervention',
            name='number',
            field=models.CharField(blank=True, max_length=45, unique=True, verbose_name='Reference Number'),
        ),
        migrations.AlterField(
            model_name='governmentinterventionresult',
            name='planned_amount',
            field=models.IntegerField(default=0, verbose_name='Planned Cash Transfers'),
        ),
        migrations.AlterField(
            model_name='governmentinterventionresult',
            name='sectors',
            field=models.ManyToManyField(blank=True, related_name='_governmentinterventionresult_sectors_+', to='reports.Sector', verbose_name='Programme/Sector'),
        ),
        migrations.AlterField(
            model_name='governmentinterventionresult',
            name='unicef_managers',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='Unicef focal points'),
        ),
        migrations.AlterField(
            model_name='interventionbudget',
            name='in_kind_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='UNICEF Supplies'),
        ),
        migrations.AlterField(
            model_name='interventionbudget',
            name='in_kind_amount_local',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='UNICEF Supplies Local'),
        ),
    ]
