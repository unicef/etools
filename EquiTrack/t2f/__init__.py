from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy


class UserTypes(object):
    ANYONE = 'Anyone'
    TRAVELER = 'Traveler'
    TRAVEL_ADMINISTRATOR = 'Travel Administrator'
    SUPERVISOR = 'Supervisor'
    TRAVEL_FOCAL_POINT = 'Travel Focal Point'
    FINANCE_FOCAL_POINT = 'Finance Focal Point'
    REPRESENTATIVE = 'Representative'

    CHOICES = (
        (ANYONE, ugettext_lazy('Anyone')),
        (TRAVELER, ugettext_lazy('Traveler')),
        (TRAVEL_ADMINISTRATOR, ugettext_lazy('Travel Administrator')),
        (SUPERVISOR, ugettext_lazy('Supervisor')),
        (TRAVEL_FOCAL_POINT, ugettext_lazy('Travel Focal Point')),
        (FINANCE_FOCAL_POINT, ugettext_lazy('Finance Focal Point')),
        (REPRESENTATIVE, ugettext_lazy('Representative')),
    )
