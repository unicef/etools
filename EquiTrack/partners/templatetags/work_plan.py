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
def show_work_plan(value):

    if not value:
        return ''

    pca = PCA.objects.get(id=int(value))
    results = pca.results.all()
    data = tablib.Dataset()
    work_plan = SortedDict()
    governorates = SortedDict()

    # for result in results:
    #     if result.governorate:
    #         governorates[result.governorate] = 0

    for result in results:
        row = work_plan.get(result.result.code, SortedDict())
        row['Code'] = result.result.code
        row['Indicator'] = result.indicator.name if result.indicator else result.result.name
        row['Targets'] = result.target
        row['Total'] = result.total
        row['CSO'] = result.partner_contribution
        row['UNICEF Cash'] = result.unicef_cash
        row['UNICEF Supplies'] = result.in_kind_amount
        # row.update(governorates)
        # if result.governorate:
        #     row[result.governorate.name] = result.target or 0
        # work_plan[result.result.code] = row

    if work_plan:
        for row in work_plan.values():
            if not data.headers or len(data.headers) < len(row.values()):
                data.headers = row.keys()
            data.append(row.values())

        return data.sort('Code').html

    return '<p>No results</p>'
