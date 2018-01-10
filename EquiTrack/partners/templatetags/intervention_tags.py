import tablib

from django import template
from django.template.loader import render_to_string
from django.utils.datastructures import OrderedDict as SortedDict

from partners.models import (
    FundingCommitment,
    GovernmentIntervention,
    Intervention,
)

register = template.Library()


@register.simple_tag
def get_interventions(partner_id):
    interventions = Intervention.objects.filter(agreement__partner__pk=partner_id)

    return render_to_string('admin/partners/interventions_table.html', {'interventions': interventions})


@register.simple_tag
def show_government_funding(value):

    if not value:
        return ''

    intervention = GovernmentIntervention.objects.get(id=int(value))

    outputs = [r.result for r in intervention.results.prefetch_related('result', 'result__result_type').all()]
    outputs_wbs = [o.wbs for o in outputs]

    commitments = FundingCommitment.objects.filter(wbs__in=outputs_wbs).all()

    # map all commitments (c.wbs) to int_outputs(io.wbs)

    for out in outputs:
        commits = [c for c in commitments if out.wbs == c.wbs]
        setattr(out, 'commitments', commits)

    data = tablib.Dataset()
    fc_summary = []

    for out in outputs:
        for commit in out.commitments:
            row = SortedDict()
            row['Output'] = out
            row['FC No.'] = commit.fc_ref
            row['FC Commit Amt'] = commit.commitment_amount
            row['FC Agreement Amt'] = commit.agreement_amount
            row['FC Exp Amt'] = commit.expenditure_amount
            fc_summary.append(row)

    if fc_summary:
        data.headers = list(fc_summary[0].keys())
        for row in fc_summary:
            data.append(list(row.values()))

        return data.html

    return '<p>No FCs Found</p>'


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
        data.headers = list(dct_summary[0].keys())
        for row in dct_summary:
            data.append(list(row.values()))

        return data.html

    return '<p>No FR Set</p>'
