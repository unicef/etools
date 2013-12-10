__author__ = 'jcranwellward'

import autocomplete_light

from .models import (
    Governorate,
    Region,
    Locality,
    Location
)

autocomplete_light.register(
    Governorate,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name'],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Governorate name..'},
)


class AutocompleteRegion(autocomplete_light.AutocompleteModelBase):

    autocomplete_js_attributes = {'placeholder': 'Region name...'}

    def choices_for_request(self):
        q = self.request.GET.get('q', '')
        governorate_id = self.request.GET.get('governorate_id', None)

        choices = self.choices.all()
        if q:
            choices = choices.filter(name__icontains=q)
        if governorate_id:
            choices = choices.filter(governorate_id=governorate_id)

        return self.order_choices(choices)[0:self.limit_choices]

autocomplete_light.register(Region, AutocompleteRegion)


class AutocompleteLocality(autocomplete_light.AutocompleteModelBase):

    autocomplete_js_attributes = {'placeholder': 'Locality name...'}

    def choices_for_request(self):
        q = self.request.GET.get('q', '')
        region_id = self.request.GET.get('region_id', None)

        choices = self.choices.all()
        if q:
            choices = choices.filter(name__icontains=q)
        if region_id:
            choices = choices.filter(region_id=region_id)

        return self.order_choices(choices)[0:self.limit_choices]


class AutocompleteLocation(autocomplete_light.AutocompleteModelBase):

    autocomplete_js_attributes = {'placeholder': 'Location name...'}

    def choices_for_request(self):
        q = self.request.GET.get('q', '')
        locality_id = self.request.GET.get('locality_id', None)

        choices = self.choices.all()
        if q:
            choices = choices.filter(name__icontains=q)
        if locality_id:
            choices = choices.filter(locality_id=locality_id)

        return self.order_choices(choices)[0:self.limit_choices]

autocomplete_light.register(Locality, AutocompleteLocality)


autocomplete_light.register(
    Location,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name',],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Location name..',},
)