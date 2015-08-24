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
def show_log_frame(value):

    if not value:
        return ''

    pca = PCA.objects.get(id=int(value))
    results = pca.results.all()
    data = tablib.Dataset()
    log_frame = SortedDict()
    governorates = SortedDict()

    for result in results:
        if result.governorate:
            governorates[result.governorate] = 0

    for result in results:
        row = log_frame.get(result.result.code, SortedDict())
        row['Code'] = result.result.code
        row['Result Type'] = result.result_type.name
        row['Result'] = result.result.name
        row['Indicator'] = result.indicator.name if result.indicator else u'NOT FOUND'
        row['Target'] = result.target
        row.update(governorates)
        if result.governorate:
            row[result.governorate.name] = result.target or 0
        log_frame[result.result.code] = row

    if log_frame:
        for row in log_frame.values():
            if not data.headers or len(data.headers) < len(row.values()):
                data.headers = row.keys()
            data.append(row.values())

        return data.sort('Code').html

    return '<p>No results</p>'
