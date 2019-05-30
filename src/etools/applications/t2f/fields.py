from django.db import models
from django.utils.translation import ugettext_lazy as _


class TravelModeField(models.CharField):
    PLANE = 'Plane'
    BUS = 'Bus'
    CAR = 'Car'
    BOAT = 'Boat'
    RAIL = 'Rail'
    TRAVEL_MODE_CHOICES = (
        (PLANE, 'Plane'),
        (BUS, 'Bus'),
        (CAR, 'Car'),
        (BOAT, 'Boat'),
        (RAIL, 'Rail')
    )

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 5)
        kwargs['choices'] = TravelModeField.TRAVEL_MODE_CHOICES
        kwargs['null'] = kwargs.get('null', True)
        kwargs['blank'] = kwargs.get('blank', True)
        kwargs['verbose_name'] = kwargs.get('verbose_name', _('Mode of Travel'))
        super().__init__(*args, **kwargs)
