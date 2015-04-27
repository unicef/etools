__author__ = 'unicef-leb-inn'

import tablib

from django import template
from django.utils.datastructures import SortedDict

from partners.models import PCA

register = template.Library()


@register.simple_tag
def show_log_frame(value):
    pca = PCA.objects.get(id=int(value))
    results = pca.resultchain_set.all()
    data = tablib.Dataset()
    indicators = SortedDict()
    row_mask = SortedDict({
        'Result Type': '',
        'Result': '',
        'Indicator': ''
    })

    # first pass gets all the governorates
    for result in results:
        if result.governorate.name not in row_mask.keys():
            row_mask[result.governorate.name] = 0

    # second pass builds the rows
    for result in results:
        row = indicators.get(result.indicator.id, row_mask.copy())
        row['Result Type'] = result.result_type.name
        row['Result'] = result.result.name
        row['Indicator'] = result.indicator.name
        row[result.governorate.name] = result.target
        indicators[result.indicator.id] = row

    if indicators:
        for row in indicators.values():
            if not data.headers or len(data.headers) < len(row.values()):
                data.headers = row.keys()
            data.append(row.values())

        return data.html
