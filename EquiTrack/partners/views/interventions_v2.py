import operator
import functools
import logging
import copy

from django.db import transaction
from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework_csv import renderers as r

from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    DestroyAPIView,
)

from EquiTrack.mixins import ExportModelMixin
from EquiTrack.renderers import CSVFlatRenderer
from EquiTrack.validation_mixins import ValidatorViewMixin
from partners.models import (
    Intervention,
    InterventionPlannedVisits,
    InterventionAttachment,
    InterventionAmendment,
    InterventionResultLink,
    InterventionReportingPeriod,
    InterventionSectorLocationLink,
)
from partners.serializers.exports.interventions import (
    InterventionAmendmentExportSerializer,
    InterventionAmendmentExportFlatSerializer,
    InterventionExportSerializer,
    InterventionExportFlatSerializer,
    InterventionIndicatorExportSerializer,
    InterventionIndicatorExportFlatSerializer,
    InterventionResultExportSerializer,
    InterventionResultExportFlatSerializer,
    InterventionSectorLocationLinkExportSerializer,
    InterventionSectorLocationLinkExportFlatSerializer,
)
from partners.serializers.interventions_v2 import (
    InterventionListSerializer,
    InterventionDetailSerializer,
    InterventionCreateUpdateSerializer,
    InterventionBudgetCUSerializer,
    InterventionAttachmentSerializer,
    InterventionAmendmentCUSerializer,
    InterventionIndicatorSerializer,
    InterventionResultCUSerializer,
    InterventionResultSerializer,
    InterventionListMapSerializer,
    MinimalInterventionListSerializer,
    InterventionResultLinkSimpleCUSerializer,
    InterventionReportingPeriodSerializer,
    InterventionSectorLocationCUSerializer,
    PlannedVisitsCUSerializer,
)
from partners.exports_v2 import InterventionCSVRenderer
from partners.filters import (
    AppliedIndicatorsFilter,
    InterventionFilter,
    InterventionResultLinkFilter,
    PartnerScopeFilter,
)
from partners.validation.interventions import InterventionValid
from partners.permissions import PartnershipManagerRepPermission, PartnershipManagerPermission
from reports.models import LowerResult, AppliedIndicator
from reports.serializers.v2 import LowerResultSimpleCUSerializer, AppliedIndicatorSerializer


class InterventionListAPIView(ExportModelMixin, ValidatorViewMixin, ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        InterventionCSVRenderer,
        CSVFlatRenderer,
    )

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'planned_visits': PlannedVisitsCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'amendments': InterventionAmendmentCUSerializer,
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
            'planned_visits',
            'attachments',
            'amendments',
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
        q = Intervention.objects.detail_qs().all()
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
                    return Intervention.objects.detail_qs().filter(id__in=ids)
            if query_params.get("my_partnerships", "").lower() == "true":
                queries.append(Q(unicef_focal_points__in=[self.request.user.id]) |
                               Q(unicef_signatory=self.request.user))
            if "document_type" in query_params.keys():
                queries.append(Q(document_type=query_params.get("document_type")))
            if "country_programme" in query_params.keys():
                queries.append(Q(agreement__country_programme=query_params.get("country_programme")))
            if "section" in query_params.keys():
                queries.append(Q(sections__pk=query_params.get("section")))
            if "cluster" in query_params.keys():
                queries.append(Q(
                    result_links__ll_results__applied_indicators__cluster_indicator_title__icontains=query_params
                    .get("cluster")))
            if "status" in query_params.keys():
                queries.append(Q(status__in=query_params.get("status").split(',')))
            if "unicef_focal_points" in query_params.keys():
                queries.append(Q(unicef_focal_points__in=[query_params.get("unicef_focal_points")]))
            if "start" in query_params.keys():
                queries.append(Q(start__gte=query_params.get("start")))
            if "end" in query_params.keys():
                queries.append(Q(end__lte=query_params.get("end")))
            if "office" in query_params.keys():
                queries.append(Q(offices__in=[query_params.get("office")]))
            if "location" in query_params.keys():
                queries.append(Q(result_links__ll_results__applied_indicators__locations__name__icontains=query_params
                                 .get("location")))
            if "search" in query_params.keys():
                queries.append(
                    Q(title__icontains=query_params.get("search")) |
                    Q(agreement__partner__name__icontains=query_params.get("search")) |
                    Q(number__icontains=query_params.get("search"))
                )
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
                response['Content-Disposition'] = "attachment;filename=interventions.csv"

        return response


class InterventionListDashView(ValidatorViewMixin, ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)

    def get_queryset(self):
        # if Partnership Manager get all
        if self.request.user.groups.filter(name='Partnership Manager').exists():
            return Intervention.objects.detail_qs().all()

        return Intervention.objects.detail_qs().filter(unicef_focal_points__in=[self.request.user],
                                                       status__in=[Intervention.ACTIVE])


class InterventionDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Intervention.objects.detail_qs().all()
    serializer_class = InterventionDetailSerializer
    permission_classes = (PartnershipManagerPermission,)

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'planned_visits': PlannedVisitsCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'amendments': InterventionAmendmentCUSerializer,
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
        related_fields = ['planned_budget', 'planned_visits',
                          'attachments', 'amendments',
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


class InterventionPlannedVisitsDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            intervention_planned_visit = InterventionPlannedVisits.objects.get(id=int(kwargs['pk']))
        except InterventionPlannedVisits.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if intervention_planned_visit.intervention.status in [Intervention.DRAFT] or \
            request.user in intervention_planned_visit.intervention.unicef_focal_points.all() or \
            request.user.groups.filter(name__in=['Partnership Manager',
                                                 'Senior Management Team']).exists():
            intervention_planned_visit.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("You do not have permissions to delete a planned visit")


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
        r.JSONRenderer,
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
        r.JSONRenderer,
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


class InterventionAmendmentListAPIView(ExportModelMixin, ValidatorViewMixin, ListAPIView):
    """
    Returns a list of InterventionAmendments.
    """
    serializer_class = InterventionAmendmentCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
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
        r.JSONRenderer,
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
        q = Intervention.objects.detail_qs()
        # TODO: remember to add back the location filter after the PRP integration related structural changes are final
        # .filter(sector_locations__isnull=False).exclude(sector_locations__locations=None)\
        # .prefetch_related('sector_locations__locations')

        query_params = self.request.query_params

        if query_params:
            queries = []
            if "country_programme" in query_params.keys():
                queries.append(Q(agreement__country_programme=query_params.get("country_programme")))
            if "section" in query_params.keys():
                queries.append(Q(sections__pk=query_params.get("section")))
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
    renderer_classes = (r.JSONRenderer,)
    queryset = LowerResult.objects.all()

    def create(self, request, *args, **kwargs):
        raw_data = copy.deepcopy(request.data)
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
    renderer_classes = (r.JSONRenderer,)
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
    renderer_classes = (r.JSONRenderer,)
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
    renderer_classes = (r.JSONRenderer,)
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
    renderer_classes = (r.JSONRenderer,)
    queryset = InterventionReportingPeriod.objects


class InterventionReportingPeriodDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = InterventionReportingPeriodSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (InterventionFilter,)
    renderer_classes = (r.JSONRenderer,)
    queryset = InterventionReportingPeriod.objects


class InterventionIndicatorsListView(ListCreateAPIView):
    serializer_class = AppliedIndicatorSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (AppliedIndicatorsFilter,)
    renderer_classes = (r.JSONRenderer,)
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
    renderer_classes = (r.JSONRenderer,)
    queryset = AppliedIndicator.objects.all()

    def delete(self, request, *args, **kwargs):
        # make sure there are no indicators added to this LLO
        raise ValidationError(u'Deleting an indicator is temporarily disabled..')
