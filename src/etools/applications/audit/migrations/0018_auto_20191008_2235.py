# Generated by Django 2.2.6 on 2019-10-08 22:35

from django.db import migrations, models
import unicef_djangolib.fields


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0017_auto_20190501_1858'),
    ]

    operations = [
        migrations.AddField(
            model_name='audit',
            name='audited_expenditure_local',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Audited Expenditure Local Currency'),
        ),
        migrations.AddField(
            model_name='audit',
            name='financial_findings_local',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True, verbose_name='Financial Findings Local Currency'),
        ),
        migrations.AddField(
            model_name='engagement',
            name='currency_of_report',
            field=unicef_djangolib.fields.CurrencyField(blank=True, choices=[('GIP', 'GIP'), ('KPW', 'KPW'), ('XEU', 'XEU'), ('BHD', 'BHD'), ('BIF', 'BIF'), ('BMD', 'BMD'), ('BSD', 'BSD'), ('AFN', 'AFN'), ('ALL', 'ALL'), ('AMD', 'AMD'), ('AUD', 'AUD'), ('AZN', 'AZN'), ('BAM', 'BAM'), ('BBD', 'BBD'), ('BDT', 'BDT'), ('BZD', 'BZD'), ('CUP1', 'CUP1'), ('BTN', 'BTN'), ('ZWL', 'ZWL'), ('AWG', 'AWG'), ('CUC', 'CUC'), ('VEF01', 'VEF01'), ('BND', 'BND'), ('BRL', 'BRL'), ('ARS', 'ARS'), ('ETB', 'ETB'), ('EUR', 'EUR'), ('FJD', 'FJD'), ('GBP', 'GBP'), ('GEL', 'GEL'), ('GHS', 'GHS'), ('GNF', 'GNF'), ('GTQ', 'GTQ'), ('GYD', 'GYD'), ('HNL', 'HNL'), ('CAD', 'CAD'), ('CDF', 'CDF'), ('CLP', 'CLP'), ('CNY', 'CNY'), ('COP', 'COP'), ('CRC', 'CRC'), ('CUP', 'CUP'), ('CVE', 'CVE'), ('DJF', 'DJF'), ('DKK', 'DKK'), ('DOP', 'DOP'), ('DZD', 'DZD'), ('EGP', 'EGP'), ('HRK', 'HRK'), ('LVL', 'LVL'), ('LYD', 'LYD'), ('MAD', 'MAD'), ('MGA', 'MGA'), ('MKD', 'MKD'), ('KWD', 'KWD'), ('KYD', 'KYD'), ('LBP', 'LBP'), ('LKR', 'LKR'), ('MDL', 'MDL'), ('KZT', 'KZT'), ('LRD', 'LRD'), ('BOB', 'BOB'), ('HKD', 'HKD'), ('CHF', 'CHF'), ('KES', 'KES'), ('MYR', 'MYR'), ('NGN', 'NGN'), ('KMF', 'KMF'), ('SCR', 'SCR'), ('SEK', 'SEK'), ('TTD', 'TTD'), ('PKR', 'PKR'), ('NIO', 'NIO'), ('RWF', 'RWF'), ('BWP', 'BWP'), ('JMD', 'JMD'), ('TJS', 'TJS'), ('UYU', 'UYU'), ('RON', 'RON'), ('PYG', 'PYG'), ('SYP', 'SYP'), ('LAK', 'LAK'), ('ERN', 'ERN'), ('SLL', 'SLL'), ('PLN', 'PLN'), ('JOD', 'JOD'), ('ILS', 'ILS'), ('AED', 'AED'), ('NPR', 'NPR'), ('NZD', 'NZD'), ('SGD', 'SGD'), ('JPY', 'JPY'), ('PAB', 'PAB'), ('ZMW', 'ZMW'), ('CZK', 'CZK'), ('SOS', 'SOS'), ('LTL', 'LTL'), ('KGS', 'KGS'), ('SHP', 'SHP'), ('BGN', 'BGN'), ('TOP', 'TOP'), ('MVR', 'MVR'), ('VEF02', 'VEF02'), ('TMT', 'TMT'), ('GMD', 'GMD'), ('MZN', 'MZN'), ('RSD', 'RSD'), ('MWK', 'MWK'), ('PGK', 'PGK'), ('MXN', 'MXN'), ('XAF', 'XAF'), ('VND', 'VND'), ('INR', 'INR'), ('NOK', 'NOK'), ('XPF', 'XPF'), ('SSP', 'SSP'), ('IQD', 'IQD'), ('SRD', 'SRD'), ('SAR', 'SAR'), ('XCD', 'XCD'), ('IRR', 'IRR'), ('KPW01', 'KPW01'), ('HTG', 'HTG'), ('IDR', 'IDR'), ('XOF', 'XOF'), ('ISK', 'ISK'), ('ANG', 'ANG'), ('NAD', 'NAD'), ('MMK', 'MMK'), ('STD', 'STD'), ('VUV', 'VUV'), ('LSL', 'LSL'), ('SVC', 'SVC'), ('KHR', 'KHR'), ('SZL', 'SZL'), ('RUB', 'RUB'), ('UAH', 'UAH'), ('UGX', 'UGX'), ('THB', 'THB'), ('AOA', 'AOA'), ('YER', 'YER'), ('USD', 'USD'), ('UZS', 'UZS'), ('OMR', 'OMR'), ('SBD', 'SBD'), ('TZS', 'TZS'), ('SDG', 'SDG'), ('WST', 'WST'), ('QAR', 'QAR'), ('MOP', 'MOP'), ('MRU', 'MRU'), ('VEF', 'VEF'), ('TRY', 'TRY'), ('ZAR', 'ZAR'), ('HUF', 'HUF'), ('MUR', 'MUR'), ('PHP', 'PHP'), ('BYN', 'BYN'), ('KRW', 'KRW'), ('TND', 'TND'), ('MNT', 'MNT'), ('PEN', 'PEN')], default='', max_length=4, null=True, verbose_name='Currency of Report'),
        ),
    ]
