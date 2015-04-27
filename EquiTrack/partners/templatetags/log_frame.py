__author__ = 'unicef-leb-inn'

import tablib

from django import template
from django.utils.datastructures import SortedDict

from partners.models import (
    PCA,
    ResultChain,
    Indicator
)

register = template.Library()

@register.simple_tag
def show_results(value):
    pca = PCA.objects.get(id=int(value))
    results = pca.resultchain_set.all()
    data = tablib.Dataset()
    indicators = SortedDict()

    for result in results:
        row = indicators.get(result.indicator.id, SortedDict())
        row['Result Type'] = result.result_type.name
        row['Result'] = result.result.name
        row['Indicator'] = result.indicator.name
        row[result.governerate.name] = result.target
        indicators[result.indicator.id] = row

    if indicators:
        for row in indicators.values():
            if not data.headers or len(data.headers) < len(row.values()):
                data.headers = row.keys()
            data.append(row.values())

        return data.html

    return '<p>No results</p>'
