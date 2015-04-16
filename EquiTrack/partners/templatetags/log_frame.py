__author__ = 'unicef-leb-inn'

from django import template
import tablib
from partners.models import (
    PCA,
    ResultChain,
    Indicator
)

register = template.Library()

# @register.inclusion_tag('admin/partners/log_frame.html')
@register.simple_tag
def show_results(value):
    pca = PCA.objects.get(id=int(value))
    results = pca.resultchain_set.all()
    data = tablib.Dataset()
    indicators = []
    governorates = []
    headers = ["Result Type", "Result", "Indicator"]

    for result in results:
        indicators.append({'ind': result.indicator, 'gov': result.governerate.name, 'tar': result.target})
        if result.governerate.name not in governorates:
            governorates.append(result.governerate.name)


    govs = {}
    for governorate in governorates:
        govs[governorate] = 0
        headers.append(governorate)

    gov_dict = {}
    for indicator in indicators:
        # if indicator["gov"] == governorate:
        # results_trans.append(indicator["ind"], {})
        if indicator['ind'] not in gov_dict:
            gov_dict[indicator['ind']] = govs.copy()
        gov_dict[indicator["ind"]][indicator["gov"]] = indicator['tar']

    for key, value in gov_dict.iteritems():
        res = results.filter(indicator=key)
        tup1 = (res[0].result_type, res[0].result, key)
        for gov, target in value.iteritems():
            tup2 = (target,)
            tup1 = tup1 + tup2
        data.append(tup1)

    data.headers = headers

    datahtml = data.html
    """Removes all values of arg from the given string"""
    return data.html

