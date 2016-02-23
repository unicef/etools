__author__ = 'jcranwellward'

from autocomplete_light import shortcuts as autocomplete_light

from .models import Location


class AutocompleteLocation(autocomplete_light.AutocompleteModelBase):
    search_fields = ['^name', 'gateway__name']
    placeholder = 'Enter location name or type'
    model = Location

autocomplete_light.register(Location, AutocompleteLocation)