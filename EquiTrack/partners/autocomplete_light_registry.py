from reports.models import Goal, Indicator, Activity, Rrp5Output, WBS, IntermediateResult

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

autocomplete_light.register(
    Rrp5Output,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name', '^sector__name',],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Type output name or sector',},
)

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

autocomplete_light.register(
    IntermediateResult,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name', '^ir_wbs_reference'],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Type IR name or reference', },
)

autocomplete_light.register(
    WBS,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name', '^code',],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Type WBS name or code',},
)

autocomplete_light.register(
    Activity,
    # Just like in ModelAdmin.search_fields
    search_fields=['^name',],
    # This will actually html attribute data-placeholder which will set
    # javascript attribute widget.autocomplete.placeholder.
    autocomplete_js_attributes={'placeholder': 'Type activity name',},
)