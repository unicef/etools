import csv
import datetime
import functools
import operator

from django.conf import settings
from django.db import connection
from django.http import HttpResponse

from easy_pdf.rendering import render_to_pdf_response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.governments.exports import GDDLocationCSVRenderer, GDDXLSRenderer
from etools.applications.governments.models import GDD, GDDKeyIntervention
from etools.applications.governments.permissions import GDDPermission, PartnershipManagerPermission
from etools.applications.governments.serializers.exports.gdd import GDDLocationExportSerializer
from etools.applications.governments.views.gdd import GDDMixin
from etools.applications.reports.models import Indicator
from etools.applications.users.models import Country
from etools.libraries.djangolib.utils import get_current_site


class GDDResultsExportView(QueryStringFilterMixin, ListAPIView):

    def get(self, request, *args, **kwargs):

        fieldnames = {
            'partner': 'Partner Name',
            'vendor_number': 'Vendor Number',
            'vendor': 'Vendor',
            'int_status': 'GPD status',
            'int_start_date': 'GPD start date',
            'int_end_date': 'GPD end date',
            'country_programme': 'Country Programme',
            'int_ref': 'GPD ref',
            'int_locations': 'Locations',
            'ind_result': 'CP Output',
            'ind_key_interventions': 'Key Interventions',
            'ind_ram_indicators': 'RAM indicators',
        }

        today = '{:%Y_%m_%d}'.format(datetime.date.today())
        country_code = self.request.tenant.country_short_code
        filename = f'GPD_result_as_of_{today}_{country_code}'

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

        writer = csv.DictWriter(response, fieldnames)
        writer.writerow(fieldnames)

        gdds = self.get_gdds()

        for gdd in gdds:
            gdd_dict = dict(
                partner=str(gdd.partner),
                vendor_number=str(gdd.partner.vendor_number),
                vendor=gdd.partner.organization.organization_type,
                int_status=gdd.get_status_display(),
                int_start_date=gdd.start, int_end_date=gdd.end,
                country_programme=str(gdd.country_programme),
                int_ref=gdd.number.replace(',', '-'),
                int_locations=','.join([location.name for location in gdd.flat_locations.all()])
            )
            ki_qs = GDDKeyIntervention.objects.filter(result_link__gdd=gdd)
            if ki_qs.exists():
                for ki in ki_qs:
                    ki_dict = {
                        'ind_result': ki.result_link.cp_output.cp_output.name,
                        'ind_key_interventions': ki.ewp_key_intervention.cp_key_intervention.name if ki.ewp_key_intervention else '',
                        'ind_ram_indicators': ', '.join([ri.name for ri in Indicator.objects.filter(gddresultlink=ki.result_link).all()])
                    }
                    export_dict = {**gdd_dict, **ki_dict}
                    writer.writerow(export_dict)
            else:
                writer.writerow(gdd_dict)

        return response

    def get_gdds(self):
        qs = GDD.objects.select_related('partner')

        if self.request.query_params:
            queries = []
            filters = (
                ('partners', 'partner__in'),
                ('agreements', 'agreement__in'),
                ('document_type', 'document_type__in'),
                ('country_programme', 'country_programme'),
                ('start', 'start__gte'),
                ('end', 'end__lte'),
                ('office', 'offices__in'),
                ('status', 'status__in'),
                ('unicef_focal_points', 'unicef_focal_points__in'),
            )

            search_terms = ('title__icontains', 'partner__organization__name__icontains', 'number__icontains')
            queries.extend(self.filter_params(filters))
            queries.append(self.search_params(search_terms))

            if queries:
                expression = functools.reduce(operator.and_, queries)
                qs = qs.filter(expression)

        return qs


class GDDLocation:
    """Helper: we'll use one of these per row of output in GDDLocationListAPIView"""
    def __init__(self, gdd, location, section):
        self.gdd = gdd
        self.selected_location = location
        self.section = section

    @property
    def sort_key(self):
        return (
            self.gdd.number,
            self.section.name if self.section else '',
            self.selected_location.name if self.selected_location else '',
        )


class GDDLocationsExportView(QueryStringFilterMixin, ListAPIView):

    serializer_class = GDDLocationExportSerializer
    queryset = GDD.objects.all()
    permission_classes = (PartnershipManagerPermission,)
    renderer_classes = (
        JSONRenderer,
        GDDLocationCSVRenderer,
    )

    filters = (
        ('status', 'status__in'),
        ('sections', 'sections__in'),
        ('office', 'offices__in'),
        ('country_programme', 'country_programme__in'),
        ('donors', 'frs__fr_items__donor__in'),
        ('grants', 'frs__fr_items__grant_number__in'),
        ('results', 'result_links__cp_output__in'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('gdds', 'pk__in'),
        ('cp_outputs', 'result_links__cp_output__cp_output__in'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('start', 'start__gte'),
        ('end', 'end__lte'),
        ('end_after', 'end__gte'),
        ('partners', 'partner__in'),
        ('agreements', 'agreement__in'),
    )

    def list(self, request, *args, **kwargs):
        rows = []
        for gdd in self.get_queryset():
            # We want to do a separate row for each gdd/location/sector combination,
            # but if the gdd has no locations or no sectors, we still want
            # to include it in the results.
            sections = gdd.combined_sections or [None]
            locations = gdd.flat_locations.all() or [None]

            for section in sections:
                for loc in locations:
                    rows.append(GDDLocation(gdd=gdd, location=loc, section=section))

        rows = sorted(rows, key=operator.attrgetter('sort_key'))
        serializer = self.get_serializer(instance=rows, many=True)
        response = Response(serializer.data)

        query_params = self.request.query_params
        if query_params.get("format") == 'csv':
            country = Country.objects.get(schema_name=connection.schema_name)
            today = '{:%Y_%m_%d}'.format(datetime.date.today())
            filename = f"GPD_locations_as_of_{today}_{country.country_short_code}"
            response['Content-Disposition'] = "attachment;filename=%s.csv" % filename

        return response


class GDDPDFView(GDDMixin, RetrieveAPIView):
    queryset = GDD.objects.detail_qs().all()
    permission_classes = (IsAuthenticated, GDDPermission)

    def get(self, request, *args, **kwargs):
        gdd = self.get_gdd_or_404(self.kwargs.get("pk"))
        gdd = self.get_queryset().get(pk=gdd.pk)
        font_path = settings.PACKAGE_ROOT + '/assets/fonts/'

        data = {
            "domain": 'https://{}'.format(get_current_site().domain),
            "gdd": gdd,
            "gdd_offices": [o.name for o in gdd.offices.all()],
            "gdd_locations": [location.name for location in gdd.flat_locations.all()],
            "font_path": font_path,
        }

        return render_to_pdf_response(request, "gdd/detail.html", data, filename=f'{str(gdd)}.pdf')


class GDDXLSView(GDDMixin, RetrieveAPIView):
    queryset = GDD.objects.detail_qs().all()
    permission_classes = (IsAuthenticated, GDDPermission,)

    def get(self, request, *args, **kwargs):
        gdd = self.get_gdd_or_404(self.kwargs.get("pk"))
        gdd = self.get_queryset().get(pk=gdd.pk)

        return HttpResponse(content=GDDXLSRenderer(gdd).render(), headers={
            'Content-Disposition': 'attachment;filename={}.xlsx'.format(str(gdd))
        })
