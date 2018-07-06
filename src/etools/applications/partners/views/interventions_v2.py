import copy
import datetime
import functools
import logging
import operator

from django.contrib.contenttypes.models import ContentType
from django.db import transaction, connection
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAdminUser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv import renderers as r
from unicef_snapshot.models import Activity

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.EquiTrack.mixins import ExportModelMixin, QueryStringFilterMixin
from etools.applications.EquiTrack.renderers import CSVFlatRenderer
from etools.applications.partners.exports_v2 import (
    InterventionCSVRenderer,
    InterventionLocationCSVRenderer,
)
from etools.applications.partners.filters import (
    AppliedIndicatorsFilter,
    InterventionFilter,
    InterventionResultLinkFilter,
    PartnerScopeFilter,
)
from etools.applications.partners.models import (
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionReportingPeriod,
    InterventionResultLink,
    InterventionSectorLocationLink,
)
from etools.applications.partners.permissions import (
    PartnershipManagerPermission,
    PartnershipManagerRepPermission,
)
from etools.applications.partners.serializers.exports.interventions import (
    InterventionAmendmentExportFlatSerializer,
    InterventionAmendmentExportSerializer,
    InterventionExportFlatSerializer,
    InterventionExportSerializer,
    InterventionIndicatorExportFlatSerializer,
    InterventionIndicatorExportSerializer,
    InterventionResultExportFlatSerializer,
    InterventionResultExportSerializer,
    InterventionSectorLocationLinkExportFlatSerializer,
    InterventionSectorLocationLinkExportSerializer,
)
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionAmendmentCUSerializer,
    InterventionAttachmentSerializer,
    InterventionBudgetCUSerializer,
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionIndicatorSerializer,
    InterventionListMapSerializer,
    InterventionListSerializer,
    InterventionReportingPeriodSerializer,
    InterventionReportingRequirementCreateSerializer,
    InterventionReportingRequirementListSerializer,
    InterventionResultCUSerializer,
    InterventionResultLinkSimpleCUSerializer,
    InterventionResultSerializer,
    InterventionSectorLocationCUSerializer,
    MinimalInterventionListSerializer,
    InterventionLocationExportSerializer)
from etools.applications.partners.validation.interventions import InterventionValid
from etools.applications.reports.models import (
    AppliedIndicator,
    LowerResult,
    ReportingRequirement,
)
from etools.applications.reports.serializers.v2 import (
    AppliedIndicatorSerializer,
    LowerResultSimpleCUSerializer,
)
from etools.applications.users.models import Country
from etools_validator.mixins import ValidatorViewMixin


class InterventionListBaseView(ValidatorViewMixin, ListCreateAPIView):
    def get_queryset(self):
        qs = Intervention.objects.frs_qs()
        return qs


class InterventionListAPIView(QueryStringFilterMixin, ExportModelMixin, InterventionListBaseView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        InterventionCSVRenderer,
        CSVFlatRenderer,
    )

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'result_links': InterventionResultCUSerializer
    }

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return InterventionExportSerializer
                if query_params.get("format") == 'csv_flat':
                    return InterventionExportFlatSerializer
            if "verbosity" in query_params.keys():
                if query_params.get("verbosity") == 'minimal':
                    return MinimalInterventionListSerializer
        if self.request.method == "POST":
            return InterventionCreateUpdateSerializer
        return super(InterventionListAPIView, self).get_serializer_class()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Add a new Intervention
        :return: JSON
        """
        related_fields = [
            'planned_budget',
            'attachments',
            'result_links'
        ]
        nested_related_names = ['ll_results']
        serializer = self.my_create(request,
                                    related_fields,
                                    nested_related_names=nested_related_names,
                                    **kwargs)

        instance = serializer.instance

        validator = InterventionValid(instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        headers = self.get_success_headers(serializer.data)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
        return Response(
            InterventionDetailSerializer(instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self, format=None):
        q = super(InterventionListAPIView, self).get_queryset()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "values" in query_params.keys():
                # Used for ghost data - filter in all(), and return straight away.
                try:
                    ids = [int(x) for x in query_params.get("values").split(",")]
                except ValueError:
                    raise ValidationError("ID values must be integers")
                else:
                    return q.filter(id__in=ids)
            if query_params.get("my_partnerships", "").lower() == "true":
                queries.append(Q(unicef_focal_points__in=[self.request.user.id]) |
                               Q(unicef_signatory=self.request.user))

            filters = (
                ('document_type', 'document_type__in'),
                ('cp_outputs', 'agreement__country_programme__in'),
                ('sections', 'sections__in'),
                ('cluster', 'result_links__ll_results__applied_indicators__cluster_indicator_title__icontains'),
                ('status', 'status__in'),
                ('unicef_focal_points', 'unicef_focal_points__in'),
                ('start', 'start__gte'),
                ('end', 'end__lte'),
                ('office', 'offices__in'),
                ('location', 'result_links__ll_results__applied_indicators__locations__name__icontains'),
            )
            search_terms = ['title__icontains', 'agreement__partner__name__icontains', 'number__icontains']
            queries.extend(self.filter_params(filters))
            queries.append(self.search_params(search_terms))

            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q

    def list(self, request):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(InterventionListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', "csv_flat"]:
                country = Country.objects.get(schema_name=connection.schema_name)
                today = '{:%Y_%m_%d}'.format(datetime.date.today())
                filename = f"PD_budget_as_of_{today}_{country.country_short_code}"
                response['Content-Disposition'] = f"attachment;filename={filename}.csv"

        return response


class InterventionListDashView(InterventionListBaseView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)

    def get_queryset(self):
        q = super(InterventionListDashView, self).get_queryset()
        # if Partnership Manager get all
        if self.request.user.groups.filter(name='Partnership Manager').exists():
            return q.all()

        return q.filter(
            unicef_focal_points__in=[self.request.user],
            status__in=[Intervention.ACTIVE]
        )


class InterventionDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Intervention.objects.detail_qs().all()
    serializer_class = InterventionDetailSerializer
    permission_classes = (PartnershipManagerPermission,)

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'result_links': InterventionResultCUSerializer
    }

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        if self.request.method in ["PATCH", "PUT"]:
            return InterventionCreateUpdateSerializer
        return super(InterventionDetailAPIView, self).get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['planned_budget',
                          'attachments',
                          'result_links']
        nested_related_names = ['ll_results']
        instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )

        validator = InterventionValid(instance, old=old_instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(InterventionDetailSerializer(instance, context=self.get_serializer_context()).data)


class InterventionAttachmentDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            intervention_attachment = InterventionAttachment.objects.get(id=int(kwargs['pk']))
        except InterventionAttachment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if intervention_attachment.intervention.status in [Intervention.DRAFT] or \
            request.user in intervention_attachment.intervention.unicef_focal_points.all() or \
            request.user.groups.filter(name__in=['Partnership Manager',
                                                 'Senior Management Team']).exists():
            intervention_attachment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("You do not have permissions to delete an attachment")


class InterventionResultListAPIView(ExportModelMixin, ListAPIView):
    """
    Returns a list of InterventionResultLinks.
    """
    serializer_class = InterventionResultSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return InterventionResultExportSerializer
            if query_params.get("format") == 'csv_flat':
                return InterventionResultExportFlatSerializer
        return super(InterventionResultListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = InterventionResultLink.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(intervention__number__icontains=query_params.get("search")) |
                    Q(cp_output__name__icontains=query_params.get("search")) |
                    Q(cp_output__code__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
        return q


class InterventionIndicatorListAPIView(ExportModelMixin, ListAPIView):
    """
    Returns a list of InterventionResultLink Indicators.
    """
    serializer_class = InterventionIndicatorSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return InterventionIndicatorExportSerializer
            if query_params.get("format") == 'csv_flat':
                return InterventionIndicatorExportFlatSerializer
        return super(InterventionIndicatorListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = InterventionResultLink.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(intervention__number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        if query_params.get("format") in ['csv', "csv_flat"]:
            res = []
            for i in q.all():
                res = res + list(i.ram_indicators.all())
            return res

        return q


class InterventionResultLinkDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            intervention_result = InterventionResultLink.objects.get(id=int(kwargs['pk']))
        except InterventionResultLink.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if intervention_result.intervention.status in [Intervention.DRAFT] or \
            request.user in intervention_result.intervention.unicef_focal_points.all() or \
            request.user.groups.filter(name__in=['Partnership Manager',
                                                 'Senior Management Team']).exists():
            intervention_result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("You do not have permissions to delete a result")


class InterventionAmendmentListAPIView(ExportModelMixin, ValidatorViewMixin, ListCreateAPIView):
    """
    Returns a list of InterventionAmendments.
    """
    serializer_class = InterventionAmendmentCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return InterventionAmendmentExportSerializer
            if query_params.get("format") == 'csv_flat':
                return InterventionAmendmentExportFlatSerializer
        return super(InterventionAmendmentListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = InterventionAmendment.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(intervention__number__icontains=query_params.get("search")) |
                    Q(amendment_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
        return q

    def create(self, request, *args, **kwargs):
        raw_data = request.data
        raw_data['intervention'] = kwargs.get('intervention_pk', None)
        serializer = self.get_serializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class InterventionAmendmentDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            intervention_amendment = InterventionAmendment.objects.get(id=int(kwargs['pk']))
        except InterventionAmendment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if intervention_amendment.intervention.status in [Intervention.DRAFT] or \
            request.user in intervention_amendment.intervention.unicef_focal_points.all() or \
            request.user.groups.filter(name__in=['Partnership Manager',
                                                 'Senior Management Team']).exists():
            intervention_amendment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("You do not have permissions to delete an amendment")


class InterventionSectorLocationLinkListAPIView(ExportModelMixin, ListAPIView):
    """
    Returns a list of InterventionSectorLocationLinks.
    """
    serializer_class = InterventionSectorLocationCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return InterventionSectorLocationLinkExportSerializer
            if query_params.get("format") == 'csv_flat':
                return InterventionSectorLocationLinkExportFlatSerializer
        return super(InterventionSectorLocationLinkListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = InterventionSectorLocationLink.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(intervention__number__icontains=query_params.get("search")) |
                    Q(sector__name__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        if query_params.get("format") in ['csv', "csv_flat"]:
            res = []
            for i in q.all():
                res = res + list(i.locations.all())
            return res

        return q


class InterventionListMapView(ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListMapSerializer
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        q = Intervention.objects.prefetch_related("flat_locations")

        query_params = self.request.query_params

        if query_params:
            queries = []
            if "country_programme" in query_params.keys():
                queries.append(Q(agreement__country_programme=query_params.get("country_programme")))
            if "section" in query_params.keys():
                if tenant_switch_is_active("prp_mode_off"):
                    sq = Q(sections__pk=query_params.get("section"))
                else:
                    sq = Q(result_links__ll_results__applied_indicators__section__pk=query_params.get("section"))
                queries.append(sq)
            if "status" in query_params.keys():
                queries.append(Q(status=query_params.get("status")))
            if "partner" in query_params.keys():
                queries.append(Q(agreement__partner=query_params.get("partner")))
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression).distinct()

        return q


class InterventionLowerResultListCreateView(ListCreateAPIView):

    serializer_class = LowerResultSimpleCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionResultLinkFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = LowerResult.objects.all()

    def create(self, request, *args, **kwargs):
        raw_data = request.data
        raw_data['result_link'] = kwargs.get('result_link_pk', None)

        serializer = self.get_serializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class InterventionLowerResultUpdateView(RetrieveUpdateDestroyAPIView):

    serializer_class = LowerResultSimpleCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionResultLinkFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = LowerResult.objects.all()

    def delete(self, request, *args, **kwargs):
        # make sure there are no indicators added to this LLO
        obj = self.get_object()
        if obj.applied_indicators.exists():
            raise ValidationError(u'This PD Output has indicators related, please remove the indicators first')
        return super(InterventionLowerResultUpdateView, self).delete(request, *args, **kwargs)


class InterventionResultLinkListCreateView(ListCreateAPIView):

    serializer_class = InterventionResultLinkSimpleCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = InterventionResultLink.objects.all()

    def create(self, request, *args, **kwargs):
        raw_data = copy.deepcopy(request.data)
        raw_data['intervention'] = kwargs.get('intervention_pk', None)

        serializer = self.get_serializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class InterventionResultLinkUpdateView(RetrieveUpdateDestroyAPIView):

    serializer_class = InterventionResultLinkSimpleCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = InterventionResultLink.objects.all()

    def delete(self, request, *args, **kwargs):
        # make sure there are no indicators added to this LLO
        obj = self.get_object()
        if obj.ll_results.exists():
            raise ValidationError(u'This CP Output cannot be removed from this Intervention because there are nested'
                                  u' Results, please remove all Document Results to continue')
        return super(InterventionResultLinkUpdateView, self).delete(request, *args, **kwargs)


class InterventionReportingPeriodListCreateView(ListCreateAPIView):
    serializer_class = InterventionReportingPeriodSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = InterventionReportingPeriod.objects


class InterventionReportingPeriodDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = InterventionReportingPeriodSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = InterventionReportingPeriod.objects


class InterventionIndicatorsListView(ListCreateAPIView):
    serializer_class = AppliedIndicatorSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (AppliedIndicatorsFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = AppliedIndicator.objects.all()

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        raw_data = copy.deepcopy(request.data)
        raw_data['lower_result'] = kwargs.get('lower_result_pk', None)

        # if this is not a cluster indicator Automatically create / get the indicator blueprint
        serializer = self.get_serializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class InterventionIndicatorsUpdateView(RetrieveUpdateDestroyAPIView):

    serializer_class = AppliedIndicatorSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (AppliedIndicatorsFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = AppliedIndicator.objects.all()

    def delete(self, request, *args, **kwargs):
        ai = self.get_object()
        intervention = ai.lower_result.result_link.intervention
        if not intervention.status == Intervention.DRAFT:
            raise ValidationError(u'Deleting an indicator is only possible in status Draft.')
        return super(InterventionIndicatorsUpdateView, self).delete(request, *args, **kwargs)


class InterventionLocation(object):
    """Helper: we'll use one of these per row of output in InterventionLocationListAPIView"""
    def __init__(self, intervention, location, section):
        self.intervention = intervention
        self.selected_location = location
        self.section = section

    @property
    def sort_key(self):
        return (
            self.intervention.number,
            self.section.name if self.section else '',
            self.selected_location.name if self.selected_location else '',
        )


class InterventionLocationListAPIView(ListAPIView):
    """
    API to export a list of intervention locations.

    Example desired output:

    "Partner","PD Ref Number","Partnership","Status","Location","Section","CP output","Start Date","End Date","Name of UNICEF Focal Point","Hyperlink"
    "Partner 1.1.1.1.1","Ref#1","Partnership 1.1.1.1.1.1.1","Active","Location 1.1.1.1.1","Section 1.1.1","CP output 1.1.1.1","DD/MM/YYYY","DD/MM/YYYY","Name1, Name2","http://xxxxxx"

    """
    serializer_class = InterventionLocationExportSerializer
    queryset = Intervention.objects.all()
    permission_classes = (PartnershipManagerPermission,)
    renderer_classes = (
        JSONRenderer,
        InterventionLocationCSVRenderer,
    )

    def list(self, request, *args, **kwargs):
        rows = []
        for intervention in self.get_queryset():
            # We want to do a separate row for each intervention/location/sector combination,
            # but if the intervention has no locations or no sectors, we still want
            # to include it in the results.
            sections = intervention.combined_sections or [None]
            locations = intervention.flat_locations.all() or [None]

            for section in sections:
                for loc in locations:
                    rows.append(InterventionLocation(intervention=intervention, location=loc, section=section))

        rows = sorted(rows, key=operator.attrgetter('sort_key'))
        serializer = self.get_serializer(instance=rows, many=True)
        response = Response(serializer.data)

        query_params = self.request.query_params
        if query_params.get("format") in ['csv', 'csv_flat']:
            country = Country.objects.get(schema_name=connection.schema_name)
            today = '{:%Y_%m_%d}'.format(datetime.date.today())
            filename = f"PD_locations_as_of_{today}_{country.country_short_code}"
            response['Content-Disposition'] = "attachment;filename=%s.csv" % filename

        return response


class InterventionDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            intervention = Intervention.objects.get(id=int(kwargs['pk']))
        except Intervention.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if intervention.status != Intervention.DRAFT:
            raise ValidationError("Cannot delete a PD or SSFA that is not Draft")

        if intervention.travel_activities.count():
            raise ValidationError("Cannot delete a PD or SSFA that has Planned Trips")

        else:
            # get the history of this PD and make sure it wasn't manually moved back to draft before allowing deletion
            act = Activity.objects.filter(target_object_id=intervention.id,
                                          target_content_type=ContentType.objects.get_for_model(intervention))
            historical_statuses = set(a.data.get('status', Intervention.DRAFT) for a in act.all())
            if len(historical_statuses) > 1 or \
                    (len(historical_statuses) == 1 and historical_statuses.pop() != Intervention.DRAFT):
                raise ValidationError("Cannot delete a PD or SSFA that was manually moved back to Draft")
            else:
                intervention.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)


class InterventionReportingRequirementView(APIView):
    serializer_create_class = InterventionReportingRequirementCreateSerializer
    serializer_list_class = InterventionReportingRequirementListSerializer
    permission_classes = (PartnershipManagerPermission, )
    renderer_classes = (JSONRenderer, )

    def get_data(self):
        return {
            "reporting_requirements": ReportingRequirement.objects.filter(
                intervention=self.intervention,
                report_type=self.report_type,
            ).all()
        }

    def get_object(self, pk):
        return get_object_or_404(Intervention, pk=pk)

    def get(self, request, intervention_pk, report_type, format=None):
        self.intervention = self.get_object(intervention_pk)
        self.report_type = report_type
        return Response(
            self.serializer_list_class(self.get_data()).data
        )

    def post(self, request, intervention_pk, report_type, format=None):
        self.intervention = self.get_object(intervention_pk)
        self.report_type = report_type
        self.request.data["report_type"] = self.report_type
        serializer = self.serializer_create_class(
            data=self.request.data,
            context={
                "intervention": self.intervention,
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                self.serializer_list_class(self.get_data()).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
