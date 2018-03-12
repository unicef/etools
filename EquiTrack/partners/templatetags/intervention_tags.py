import tablib

from django import template
from django.template.loader import render_to_string
from django.utils.datastructures import OrderedDict as SortedDict

from partners.models import Intervention

register = template.Library()


@register.simple_tag
def get_interventions(partner_id):
    interventions = Intervention.objects.filter(agreement__partner__pk=partner_id)

    return render_to_string('admin/partners/interventions_table.html', {'interventions': interventions})


@register.simple_tag
def show_dct(value):

    if not value:
        return ''

    # intervention = Intervention.objects.get(id=int(value))
    # fr_number = intervention.fr_number
    data = tablib.Dataset()
    dct_summary = []

    row = SortedDict()

    row['FC Ref'] = ''
    row['Amount'] = ''
    row['Liquidation Amount'] = ''
    row['Outstanding Amount'] = ''
    row['Amount Less than 3 Months'] = ''
    row['Amount 3 to 6 Months'] = ''
    row['Amount 6 to 9 Months'] = ''
    row['Amount More than 9 Months'] = ''

    dct_summary.append(row)

    if dct_summary:
        data.headers = dct_summary[0].keys()
        for row in dct_summary:
            data.append(row.values())

        return data.html

    return '<p>No FR Set</p>'
