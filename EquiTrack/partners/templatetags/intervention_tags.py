__author__ = 'unicef-leb-inn'

import tablib

from django import template
from django.utils.datastructures import OrderedDict as SortedDict

from partners.models import (
    PCA,
    PartnerOrganization,
    FundingCommitment,
    DirectCashTransfer,
    GovernmentIntervention,
)
from trips.models import Trip


register = template.Library()


@register.simple_tag
def show_work_plan(value):

    if not value:
        return ''

    intervention = PCA.objects.get(id=int(value))
    results = intervention.results.all()
    data = tablib.Dataset()
    work_plan = SortedDict()

    for num, result in enumerate(results):
        row = SortedDict()
        row['Code'] = result.indicator.code if result.indicator else result.result.code
        row['Details'] = result.indicator.name if result.indicator else result.result.name
        row['Targets'] = result.target if result.target else ''
        # temporarily remove disaggregations since the number of fields can vary
        # if result.disaggregation:
        #     row.update(result.disaggregation)
        row['Total'] = result.total if result.total else ''
        row['CSO'] = result.partner_contribution if result.partner_contribution else ''
        row['UNICEF Cash'] = result.unicef_cash if result.unicef_cash else ''
        row['UNICEF Supplies'] = result.in_kind_amount if result.in_kind_amount else ''

        work_plan[num] = row

    if work_plan:
        for row in work_plan.values():
            if not data.headers or len(data.headers) < len(row.values()):
                data.headers = row.keys()
            data.append(row.values())

        return data.html

    return '<p>No results</p>'


@register.simple_tag
def show_trips(value):

    if not value:
        return ''

    intervention = PCA.objects.get(id=int(value))
    trips = Trip.objects.filter(pcas__in=[intervention])
    data = tablib.Dataset()
    trip_summary = []

    for trip in trips:
        row = SortedDict()
        row['Ref'] = '<a href="{}">{}</a>'.format(
            trip.get_admin_url(),
            trip.reference()
        )
        row['Status'] = trip.status
        row['Traveller'] = trip.owner
        row['Trip Type'] = trip.travel_type
        row['Purpose'] = trip.purpose_of_travel
        row['From'] = trip.from_date
        row['To'] = trip.to_date

        trip_summary.append(row)

    if trip_summary:
        data.headers = trip_summary[0].keys()
        for row in trip_summary:
            data.append(row.values())

        return data.html

    return '<p>No trips</p>'


@register.simple_tag
def show_fr_fc(value):

    if not value:
        return ''

    intervention = PCA.objects.get(id=int(value))
    commitments = FundingCommitment.objects.filter(intervention=intervention)
    data = tablib.Dataset()
    fr_fc_summary = []

    for commit in commitments:
        row = SortedDict()
        row['Grant'] = commit.grant.__unicode__()
        row['FR Number'] = commit.fr_number
        row['WBS'] = commit.wbs
        row['FC Type'] = commit.fc_type
        row['FC Ref'] = commit.fc_ref
        row['Agreement Amount'] = commit.agreement_amount
        row['Commitment Amount'] = commit.commitment_amount
        row['Expenditure Amount'] = commit.expenditure_amount
        fr_fc_summary.append(row)

    if fr_fc_summary:
        data.headers = fr_fc_summary[0].keys()
        for row in fr_fc_summary:
            data.append(row.values())

        return data.html

    return '<p>No FR Set</p>'


@register.simple_tag
def show_government_funding(value):

    if not value:
        return ''

    intervention = GovernmentIntervention.objects.get(id=int(value))
    commitments = FundingCommitment.objects.filter(wbs=intervention)
    data = tablib.Dataset()
    fr_fc_summary = []

    for commit in commitments:
        row = SortedDict()
        row['Grant'] = commit.grant.__unicode__()
        row['FR Number'] = commit.fr_number
        row['WBS'] = commit.wbs
        row['FC Type'] = commit.fc_type
        row['FC Ref'] = commit.fc_ref
        row['Agreement Amount'] = commit.agreement_amount
        row['Commitment Amount'] = commit.commitment_amount
        row['Expenditure Amount'] = commit.expenditure_amount
        fr_fc_summary.append(row)

    if fr_fc_summary:
        data.headers = fr_fc_summary[0].keys()
        for row in fr_fc_summary:
            data.append(row.values())

        return data.html

    return '<p>No FR Set</p>'


@register.simple_tag
def show_dct(value):

    if not value:
        return ''

    intervention = PCA.objects.get(id=int(value))
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