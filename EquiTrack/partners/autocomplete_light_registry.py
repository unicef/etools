__author__ = 'jcranwellward'

import autocomplete_light

from .models import (
    PartnerOrganization,
)


autocomplete_light.register(
    PartnerOrganization,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name',],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Type partner name',},
)