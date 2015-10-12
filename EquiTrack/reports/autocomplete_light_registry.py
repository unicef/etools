
__author__ = 'jcranwellward'

import autocomplete_light

from reports.models import Goal, Indicator


autocomplete_light.register(
    Indicator,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name', '^goal__name',],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Type indicator name or CCC',},
)

autocomplete_light.register(
    Goal,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name', '^sector__name',],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Type CCC name or sector', },
)
