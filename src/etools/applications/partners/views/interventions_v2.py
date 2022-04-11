import copy
import datetime
import functools
import logging
import operator

from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from etools_validator.mixins import ValidatorViewMixin
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import DestroyAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv import renderers as r
from unicef_restlib.views import QueryStringFilterMixin
from unicef_snapshot.models import Activity

from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.partners.exports_v2 import InterventionCSVRenderer, InterventionLocationCSVRenderer
from etools.applications.partners.filters import (
    AppliedIndicatorsFilter,
    InterventionFilter,
    InterventionResultLinkFilter,
    PartnerScopeFilter,
    ShowAmendmentsFilter,
)
from etools.applications.partners.models import (
    Agreement,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionPlannedVisits,
    InterventionReportingPeriod,
    InterventionResultLink,
)
from etools.applications.partners.permissions import (
    PARTNERSHIP_MANAGER_GROUP,
    PartnershipManagerPermission,
    PartnershipManagerRepPermission,
    SENIOR_MANAGEMENT_GROUP,
    UserIsNotPartnerStaffMemberPermission,
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
)
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionAmendmentCUSerializer,
    InterventionAttachmentSerializer,
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionIndicatorSerializer,
    InterventionListMapSerializer,
    InterventionListSerializer,
    InterventionLocationExportSerializer,
    InterventionRAMIndicatorsListSerializer,
    InterventionReportingPeriodSerializer,
    InterventionReportingRequirementCreateSerializer,
    InterventionReportingRequirementListSerializer,
    InterventionResultCUSerializer,
    InterventionResultLinkSimpleCUSerializer,
    InterventionResultSerializer,
    InterventionToIndicatorsListSerializer,
    MinimalInterventionListSerializer,
    PlannedVisitsCUSerializer,
)
from etools.applications.partners.utils import send_intervention_amendment_added_notification
from etools.applications.partners.validation.interventions import InterventionValid
from etools.applications.reports.models import AppliedIndicator, LowerResult, ReportingRequirement
from etools.applications.reports.serializers.v2 import AppliedIndicatorSerializer, LowerResultSimpleCUSerializer
from etools.applications.users.models import Country


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
    filter_backends = (PartnerScopeFilter, ShowAmendmentsFilter)
    renderer_classes = (
        JSONRenderer,
        InterventionCSVRenderer,
        CSVFlatRenderer,
    )

    search_terms = ('title__icontains', 'agreement__partner__name__icontains', 'number__icontains')
    filters = [
        ('partners', 'agreement__partner__in'),
        ('agreements', 'agreement__in'),
        ('document_type', 'document_type__in'),
        ('cp_outputs', 'result_links__cp_output__pk__in'),
        ('country_programme', 'country_programme__in'),
        ('sections', 'sections__in'),
        ('cluster', 'result_links__ll_results__applied_indicators__cluster_indicator_title__icontains'),
        ('status', 'status__in'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('start', 'start__gte'),
        ('end', 'end__lte'),
        ('end_after', 'end__gte'),
        ('office', 'offices__in'),
        ('location', 'result_links__ll_results__applied_indicators__locations__name__icontains'),
        ('contingency_pd', 'contingency_pd'),
        ('grants', 'frs__fr_items__grant_number__in'),
        ('grants__contains', 'frs__fr_items__grant_number__icontains'),
        ('donors', 'frs__fr_items__donor__icontains'),
        ('budget_owner__in', 'budget_owner__in'),
    ]

    SERIALIZER_MAP = {
        'planned_visits': PlannedVisitsCUSerializer,
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
        return super().get_serializer_class()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Add a new Intervention
        :return: JSON
        """
        related_fields = [
            'planned_visits',
            'result_links'
        ]
        nested_related_names = ['ll_results']

        if request.data.get('document_type') == Intervention.SSFA:
            agreement = Agreement.objects.get(pk=request.data.get('agreement'))
            if agreement and agreement.interventions.count():
                raise ValidationError(
                    'You can only add one SSFA Document for each SSFA Agreement',
                    status.HTTP_400_BAD_REQUEST
                )

        serializer = self.my_create(request,
                                    related_fields,
                                    nested_related_names=nested_related_names,
                                    **kwargs)

        self.instance = serializer.instance

        validator = InterventionValid(self.instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        self.headers = self.get_success_headers(serializer.data)
        if getattr(self.instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            self.instance = self.get_object()
        return Response(
            InterventionDetailSerializer(self.instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )

    def get_queryset(self, format=None):
        q = super().get_queryset()
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

            queries.extend(self.filter_params())
            queries.append(self.search_params())

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
        response = super().list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', "csv_flat"]:
                country = Country.objects.get(schema_name=connection.schema_name)
                today = '{:%Y_%m_%d}'.format(datetime.date.today())
                filename = f"PD_budget_as_of_{today}_{country.country_short_code}"
                response['Content-Disposition'] = f"attachment;filename={filename}.csv"

        return response


class InterventionWithAppliedIndicatorsView(QueryStringFilterMixin, ListAPIView):
    """ Interventions."""
    queryset = Intervention.objects.all()
    serializer_class = InterventionToIndicatorsListSerializer
    permission_classes = (PartnershipManagerPermission,)

    filters = (
        ('sections', 'sections__in'),
        ('status', 'status__in'),
    )

    def get_queryset(self):
        return super().get_queryset().select_related('agreement__partner').prefetch_related(
            'result_links__ll_results__applied_indicators__indicator')


class InterventionListDashView(InterventionListBaseView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)

    def get_queryset(self):
        q = super().get_queryset()
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
        'planned_visits': PlannedVisitsCUSerializer,
        'result_links': InterventionResultCUSerializer
    }
    related_fields = [
        'planned_visits',
        'result_links'
    ]
    nested_related_names = [
        'll_results'
    ]
    related_non_serialized_fields = [
        # todo: add other CodedGenericRelation fields. at this moment they're not managed by permissions matrix
        'prc_review_attachment',
        'final_partnership_review',
        'signed_pd_attachment',
    ]

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        if self.request.method in ["PATCH", "PUT"]:
            return InterventionCreateUpdateSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        self.instance, old_instance, serializer = self.my_update(
            request,
            self.related_fields,
            nested_related_names=self.nested_related_names,
            related_non_serialized_fields=self.related_non_serialized_fields,
            **kwargs
        )

        validator = InterventionValid(self.instance, old=old_instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        if tenant_switch_is_active('intervention_amendment_notifications_on') and \
                old_instance and not self.instance.in_amendment and old_instance.in_amendment:
            send_intervention_amendment_added_notification(self.instance)

        if getattr(self.instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            self.instance = self.get_object()

        return Response(
            InterventionDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
        )


class InterventionAttachmentListCreateView(ListCreateAPIView):

    serializer_class = InterventionAttachmentSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = InterventionAttachment.objects.all()

    def create(self, request, *args, **kwargs):
        request.data.__setitem__("intervention", kwargs.get('intervention_pk', None))

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class InterventionAttachmentUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    serializer_class = InterventionAttachmentSerializer
    queryset = InterventionAttachment.objects.all()
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()

        if obj.intervention.status in [Intervention.DRAFT]:
            return super().delete(request, *args, **kwargs)
        else:
            raise ValidationError("Deleting an attachment can only be done in Draft status")


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
        return super().get_serializer_class()

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
        return super().get_serializer_class()

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


class InterventionAmendmentListAPIView(ExportModelMixin, ValidatorViewMixin, ListCreateAPIView):
    """
    Returns a list of InterventionAmendments.
    """
    serializer_class = InterventionAmendmentCUSerializer
    permission_classes = (PartnershipManagerPermission, UserIsNotPartnerStaffMemberPermission)
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
        return super().get_serializer_class()

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
        raw_data = request.data.copy()
        raw_data['intervention'] = kwargs.get('intervention_pk', None)
        serializer = self.get_serializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class InterventionAmendmentDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission, UserIsNotPartnerStaffMemberPermission)

    def delete(self, request, *args, **kwargs):
        try:
            intervention_amendment = InterventionAmendment.objects.get(id=int(kwargs['pk']))
        except InterventionAmendment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # todo: there are 3 possible checks for permissions: code below + permission_classes + permissions matrix.
        #  should be refined and moved to permissions matrix. in fact, both permissions_classes and
        #  permissions matrix are ignored. in addition to that, they are not synchronized to each other,
        #  for example we ignore amendment mode here PartnershipManagerRepPermission.check_object_permissions
        #  never executed. normally view.check_object_permissions is called
        #  inside GenericAPIView.get_object method which is not used.

        if intervention_amendment.intervention.status in [Intervention.DRAFT] or \
            request.user in intervention_amendment.intervention.unicef_focal_points.all() or \
            request.user.groups.filter(name__in=[PARTNERSHIP_MANAGER_GROUP,
                                                 SENIOR_MANAGEMENT_GROUP]).exists():
            intervention_amendment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("You do not have permissions to delete an amendment")


class InterventionListMapView(QueryStringFilterMixin, ListCreateAPIView):
    """
    Returns a list of Interventions.
    """
    serializer_class = InterventionListMapSerializer
    permission_classes = (IsAdminUser,)

    filters = (
        ('sections', 'sections__in'),
        ('country_programmes', 'country_programme__in'),
        ('status', 'status__in'),
        ('partners', 'agreement__partner__in'),
        ('offices', 'offices__in'),
        ('results', 'result_links__cp_output__in'),
        ('donors', 'frs__fr_items__donor__in'),
        ('grants', 'frs__fr_items__grant_number__in'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('interventions', 'pk__in'),
        ('clusters', 'result_links__ll_results__applied_indicators__cluster_name__icontains'),
    )

    def get_queryset(self):
        qs = Intervention.objects.maps_qs()

        query_params = self.request.query_params

        if query_params:
            queries = []
            queries.extend(self.filter_params())
            queries.append(self.search_params())
            if queries:
                expression = functools.reduce(operator.and_, queries)
                qs = qs.filter(expression).distinct()

        return qs


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
            raise ValidationError('This PD Output has indicators related, please remove the indicators first')
        return super().delete(request, *args, **kwargs)


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
            raise ValidationError('This CP Output cannot be removed from this Intervention because there are nested'
                                  ' Results, please remove all Document Results to continue')
        return super().delete(request, *args, **kwargs)


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
            raise ValidationError('Deleting an indicator is only possible in status Draft.')
        return super().delete(request, *args, **kwargs)


class InterventionLocation:
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


class InterventionLocationListAPIView(QueryStringFilterMixin, ListAPIView):
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

    filters = (
        ('status', 'status__in'),
        ('document_type', 'document_type__in'),
        ('sections', 'sections__in'),
        ('office', 'offices__in'),
        ('country_programmes', 'country_programme__in'),
        ('donors', 'frs__fr_items__donor__in'),
        ('grants', 'frs__fr_items__grant_number__in'),
        ('results', 'result_links__cp_output__in'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('interventions', 'pk__in'),
        ('cp_outputs', 'result_links__cp_output__in'),
        ('cluster', 'result_links__ll_results__applied_indicators__cluster_indicator_title__icontains'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('start', 'start__gte'),
        ('end', 'end__lte'),
        ('end_after', 'end__gte'),
        ('location', 'result_links__ll_results__applied_indicators__locations__name__icontains'),
        ('partners', 'agreement__partner__in'),
        ('agreements', 'agreement__in'),
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
    # todo: permission_classes are ignored here. see comments in InterventionAmendmentDeleteView.delete
    permission_classes = (PartnershipManagerRepPermission,)
    queryset = Intervention.objects

    def delete(self, request, *args, **kwargs):
        intervention = self.get_object()
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

            # do not delete any PDs that have been sent to a partner before
            date_sent_to_partner_qs = Activity.objects.filter(
                target_content_type=ContentType.objects.get_for_model(
                    Intervention,
                ),
                target_object_id=intervention.pk,
                change__has_key="date_sent_to_partner"
            )
            if date_sent_to_partner_qs.exists():
                raise ValidationError("PD has already been sent to Partner.")

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


class InterventionRamIndicatorsView(APIView):

    serializer_class = InterventionRAMIndicatorsListSerializer

    def get(self, request, intervention_pk, cp_output_pk):

        intervention = get_object_or_404(Intervention, pk=intervention_pk)

        data = get_object_or_404(intervention.result_links.prefetch_related('cp_output__result_type', 'ram_indicators'),
                                 cp_output__pk=cp_output_pk)

        return Response(
            self.serializer_class(data).data
        )


class InterventionPlannedVisitsDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerPermission,)

    def delete(self, request, *args, **kwargs):
        intervention = get_object_or_404(
            Intervention,
            pk=int(kwargs['intervention_pk'])
        )
        if intervention.status != Intervention.DRAFT:
            raise ValidationError("Planned visits can only be deleted in Draft status")

        intervention_planned_visit = get_object_or_404(
            InterventionPlannedVisits,
            pk=int(kwargs['pk']),
            intervention=int(kwargs['intervention_pk'])
        )
        self.check_object_permissions(request, intervention_planned_visit)
        intervention_planned_visit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
