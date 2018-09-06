# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-02-21 12:34

from django.db import migrations, models
from unicef_djangolib.fields import CurrencyField, QuarterField

import etools.applications.EquiTrack


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0004_fix_null_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessment',
            name='names_of_other_agencies',
            field=models.CharField(blank=True, default=True, help_text='List the names of the other agencies they have worked with',
                                   max_length=255, verbose_name='Other Agencies'),
        ),
        migrations.AlterField(
            model_name='assessment',
            name='notes',
            field=models.CharField(blank=True, default='', help_text='Note any special requests to be considered during the assessment',
                                   max_length=255, verbose_name='Special requests'),
        ),
        migrations.AlterField(
            model_name='fundingcommitment',
            name='fc_ref',
            field=models.CharField(blank=True, default='', max_length=50, unique=True, verbose_name='Reference'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='number',
            field=models.CharField(blank=True, default='', max_length=64,
                                   unique=True, verbose_name='Reference Number'),
        ),
        migrations.AlterField(
            model_name='intervention',
            name='population_focus',
            field=models.CharField(blank=True, default='', max_length=130, verbose_name='Population Focus'),
        ),
        migrations.AlterField(
            model_name='interventionamendment',
            name='other_description',
            field=models.CharField(blank=True, default='', max_length=512, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='interventionbudget',
            name='currency',
            field=CurrencyField(blank=True, choices=[('GIP', 'GIP'), ('KPW', 'KPW'), ('XEU', 'XEU'), ('BHD', 'BHD'), ('BIF', 'BIF'), ('BMD', 'BMD'), ('BSD', 'BSD'), ('YER1', 'YER1'), ('AFN', 'AFN'), ('ALL', 'ALL'), ('AMD', 'AMD'), ('AUD', 'AUD'), ('AZN', 'AZN'), ('BAM', 'BAM'), ('BBD', 'BBD'), ('BDT', 'BDT'), ('BZD', 'BZD'), ('CUP1', 'CUP1'), ('BTN', 'BTN'), ('ZWL', 'ZWL'), ('AWG', 'AWG'), ('CUC', 'CUC'), ('VEF01', 'VEF01'), ('BND', 'BND'), ('BRL', 'BRL'), ('ARS', 'ARS'), ('ETB', 'ETB'), ('EUR', 'EUR'), ('FJD', 'FJD'), ('GBP', 'GBP'), ('GEL', 'GEL'), ('GHS', 'GHS'), ('GNF', 'GNF'), ('GTQ', 'GTQ'), ('GYD', 'GYD'), ('HNL', 'HNL'), ('CAD', 'CAD'), ('CDF', 'CDF'), ('CLP', 'CLP'), ('CNY', 'CNY'), ('COP', 'COP'), ('CRC', 'CRC'), ('CUP', 'CUP'), ('CVE', 'CVE'), ('DJF', 'DJF'), ('DKK', 'DKK'), ('DOP', 'DOP'), ('DZD', 'DZD'), ('EGP', 'EGP'), ('HRK', 'HRK'), ('LVL', 'LVL'), ('LYD', 'LYD'), ('MAD', 'MAD'), ('MGA', 'MGA'), ('MKD', 'MKD'), ('KWD', 'KWD'), ('KYD', 'KYD'), ('LBP', 'LBP'), ('LKR', 'LKR'), ('MDL', 'MDL'), ('KZT', 'KZT'), ('LRD', 'LRD'), ('BOB', 'BOB'), ('HKD', 'HKD'), ('CHF', 'CHF'), ('KES', 'KES'), ('MYR', 'MYR'), ('NGN', 'NGN'), ('KMF', 'KMF'), ('SCR', 'SCR'), ('SEK', 'SEK'), ('TTD', 'TTD'), ('PKR', 'PKR'), ('NIO', 'NIO'), ('RWF', 'RWF'), ('BWP', 'BWP'), ('JMD', 'JMD'), ('TJS', 'TJS'), ('UYU', 'UYU'), ('RON', 'RON'), ('PYG', 'PYG'), (
                'SYP', 'SYP'), ('LAK', 'LAK'), ('ERN', 'ERN'), ('SLL', 'SLL'), ('PLN', 'PLN'), ('JOD', 'JOD'), ('ILS', 'ILS'), ('AED', 'AED'), ('NPR', 'NPR'), ('NZD', 'NZD'), ('SGD', 'SGD'), ('JPY', 'JPY'), ('PAB', 'PAB'), ('ZMW', 'ZMW'), ('CZK', 'CZK'), ('SOS', 'SOS'), ('LTL', 'LTL'), ('KGS', 'KGS'), ('SHP', 'SHP'), ('BGN', 'BGN'), ('TOP', 'TOP'), ('MVR', 'MVR'), ('VEF02', 'VEF02'), ('TMT', 'TMT'), ('GMD', 'GMD'), ('MZN', 'MZN'), ('RSD', 'RSD'), ('MWK', 'MWK'), ('PGK', 'PGK'), ('MXN', 'MXN'), ('XAF', 'XAF'), ('VND', 'VND'), ('INR', 'INR'), ('NOK', 'NOK'), ('XPF', 'XPF'), ('SSP', 'SSP'), ('IQD', 'IQD'), ('SRD', 'SRD'), ('SAR', 'SAR'), ('XCD', 'XCD'), ('IRR', 'IRR'), ('KPW01', 'KPW01'), ('HTG', 'HTG'), ('IDR', 'IDR'), ('XOF', 'XOF'), ('ISK', 'ISK'), ('ANG', 'ANG'), ('NAD', 'NAD'), ('MMK', 'MMK'), ('STD', 'STD'), ('VUV', 'VUV'), ('LSL', 'LSL'), ('SVC', 'SVC'), ('KHR', 'KHR'), ('SZL', 'SZL'), ('RUB', 'RUB'), ('UAH', 'UAH'), ('UGX', 'UGX'), ('THB', 'THB'), ('AOA', 'AOA'), ('YER', 'YER'), ('USD', 'USD'), ('UZS', 'UZS'), ('OMR', 'OMR'), ('SBD', 'SBD'), ('TZS', 'TZS'), ('SDG', 'SDG'), ('WST', 'WST'), ('QAR', 'QAR'), ('MOP', 'MOP'), ('MRO', 'MRO'), ('VEF', 'VEF'), ('TRY', 'TRY'), ('ZAR', 'ZAR'), ('HUF', 'HUF'), ('MUR', 'MUR'), ('PHP', 'PHP'), ('BYN', 'BYN'), ('KRW', 'KRW'), ('TND', 'TND'), ('MNT', 'MNT'), ('PEN', 'PEN')], default='', max_length=4, verbose_name='Currency'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='address',
            field=models.TextField(blank=True, default='', verbose_name='Address'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='alternate_name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Alternate Name'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='basis_for_risk_rating',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Basis for Risk Rating'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='city',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='City'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='country',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Country'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='email',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Email Address'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='phone_number',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Phone Number'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='postal_code',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Postal Code'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='rating',
            field=models.CharField(blank=True, choices=[('High', 'High'), ('Significant', 'Significant'), ('Moderate', 'Medium'), (
                'Low', 'Low'), ('Non-Assessed', 'Non Required')], default='', max_length=50, verbose_name='Risk Rating'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='street_address',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='Street Address'),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='type_of_assessment',
            field=models.CharField(default='', max_length=50, verbose_name='Assessment Type'),
        ),
        migrations.AlterField(
            model_name='partnerstaffmember',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Phone Number'),
        ),
        migrations.AlterField(
            model_name='partnerstaffmember',
            name='title',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Title'),
        ),
        migrations.AlterField(
            model_name='plannedengagement',
            name='spot_check_mr',
            field=QuarterField(blank=True, choices=[(
                b'q1', b'Q1'), (b'q2', b'Q2'), (b'q3', b'Q3'), (b'q4', b'Q4')], default='', max_length=2, null=True, verbose_name='Spot Check MR'),
        ),
    ]
