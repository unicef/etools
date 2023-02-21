from django.db import models

from model_utils import Choices

CURRENCY_LIST = [
    'GIP', 'KPW', 'XEU', 'BHD', 'BIF', 'BMD', 'BSD', 'AFN', 'ALL', 'AMD', 'AUD', 'AZN', 'BAM',
    'BBD', 'BDT', 'BZD', 'CUP1', 'BTN', 'ZWL', 'AWG', 'CUC', 'VEF01', 'BND', 'BRL', 'ARS', 'ETB', 'EUR',
    'FJD', 'GBP', 'GEL', 'GHS', 'GNF', 'GTQ', 'GYD', 'HNL', 'CAD', 'CDF', 'CLP', 'CNY', 'COP', 'CRC',
    'CUP', 'CVE', 'DJF', 'DKK', 'DOP', 'DZD', 'EGP', 'HRK', 'LVL', 'LYD', 'MAD', 'MGA', 'MKD', 'KWD',
    'KYD', 'LBP', 'LKR', 'MDL', 'KZT', 'LRD', 'BOB', 'HKD', 'CHF', 'KES', 'MYR', 'NGN', 'KMF', 'SCR',
    'SEK', 'TTD', 'PKR', 'NIO', 'RWF', 'BWP', 'JMD', 'TJS', 'UYU', 'RON', 'PYG', 'SYP', 'LAK', 'ERN',
    'SLE', 'PLN', 'JOD', 'ILS', 'AED', 'NPR', 'NZD', 'SGD', 'JPY', 'PAB', 'ZMW', 'CZK', 'SOS', 'LTL',
    'KGS', 'SHP', 'BGN', 'TOP', 'MVR', 'VEF02', 'TMT', 'GMD', 'MZN', 'RSD', 'MWK', 'PGK', 'MXN', 'XAF',
    'VND', 'INR', 'NOK', 'XPF', 'SSP', 'IQD', 'SRD', 'SAR', 'XCD', 'IRR', 'KPW01', 'HTG', 'IDR', 'XOF',
    'ISK', 'ANG', 'NAD', 'MMK', 'STD', 'VUV', 'LSL', 'SVC', 'KHR', 'SZL', 'RUB', 'UAH', 'UGX', 'THB',
    'AOA', 'YER', 'USD', 'UZS', 'OMR', 'SBD', 'TZS', 'SDG', 'WST', 'QAR', 'MOP', 'MRU', 'VEF', 'TRY',
    'ZAR', 'HUF', 'MUR', 'PHP', 'BYN', 'KRW', 'TND', 'MNT', 'PEN'
]

CURRENCIES = Choices(*[(c, c) for c in CURRENCY_LIST])


class CurrencyField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 5)
        kwargs['choices'] = CURRENCIES
        kwargs['null'] = kwargs.get('null', False)
        kwargs['blank'] = kwargs.get('blank', True)
        kwargs['default'] = kwargs.get('default', '')
        super().__init__(*args, **kwargs)
