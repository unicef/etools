import operator
import functools
import logging

from django.db import transaction
from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework_csv import renderers as r

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    DestroyAPIView,
    ListAPIView,
)

from EquiTrack.validation_mixins import ValidatorViewMixin

from partners.models import (
    InterventionBudget,
    Intervention,
    InterventionPlannedVisits,
    InterventionAttachment,
    InterventionAmendment,
    InterventionSectorLocationLink,
    InterventionResultLink
)
from partners.serializers.interventions_v2 import (
    InterventionListSerializer,
    InterventionDetailSerializer,
    InterventionCreateUpdateSerializer,
    InterventionExportSerializer,
    InterventionBudgetCUSerializer,
    PlannedVisitsCUSerializer,
    InterventionAttachmentSerializer,
    InterventionAmendmentCUSerializer,
    InterventionSectorLocationCUSerializer,
    InterventionResultCUSerializer,
    InterventionListMapSerializer,
    MinimalInterventionListSerializer,
)
from partners.exports_v2 import InterventionCvsRenderer
from partners.filters import PartnerScopeFilter, InterventionScopeFilter
from partners.validation.interventions import InterventionValid
from partners.permissions import PartneshipManagerRepPermission
from reports.models import Sector
from reports.serializers.v1 import SectorSerializer


class InterventionListAPIView(ValidatorViewMixin, ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (r.JSONRenderer, InterventionCvsRenderer)

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'planned_visits': PlannedVisitsCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'amendments': InterventionAmendmentCUSerializer,
        'sector_locations': InterventionSectorLocationCUSerializer,
        'result_links': InterventionResultCUSerializer
    }

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return InterventionExportSerializer
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
        # TODO: rename these
        # supplies = request.data.pop("supplies", [])
        # distributions = request.data.pop("distributions", [])

        # TODO: add supplies, distributions
        related_fields = [
            'planned_budget',
            'planned_visits',
            'attachments',
            'amendments',
            'sector_locations',
            'result_links'
        ]
        nested_related_names = ['ll_results']
        serializer = self.my_create(request,
                                    related_fields,
                                    snapshot=True,
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
            if "sector" in query_params.keys():
                queries.append(Q(sector_locations__sector__id=query_params.get("sector")))
            if "status" in query_params.keys():
                queries.append(Q(status=query_params.get("status")))
            if "unicef_focal_points" in query_params.keys():
                queries.append(Q(unicef_focal_points__in=[query_params.get("unicef_focal_points")]))
            if "start" in query_params.keys():
                queries.append(Q(start__gte=query_params.get("start")))
            if "end" in query_params.keys():
                queries.append(Q(end__lte=query_params.get("end")))
            if "office" in query_params.keys():
                queries.append(Q(offices__in=[query_params.get("office")]))
            if "location" in query_params.keys():
                queries.append(Q(sector_locations__locations__name__icontains=query_params.get("location")))
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
            if query_params.get("format") == 'csv':
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

        return Intervention.objects.detail_qs().filter(unicef_focal_points__in=[self.request.user])


class InterventionDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Intervention.objects.detail_qs().all()
    serializer_class = InterventionDetailSerializer
    permission_classes = (IsAdminUser,)

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'planned_visits': PlannedVisitsCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'amendments': InterventionAmendmentCUSerializer,
        'sector_locations': InterventionSectorLocationCUSerializer,
        'result_links': InterventionResultCUSerializer
    }

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        if self.request.method in ["PATCH", "PUT"]:
            return InterventionCreateUpdateSerializer
        return super(InterventionDetailAPIView, self).get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['planned_budget', 'planned_visits',
                          'attachments', 'amendments',
                          'sector_locations', 'result_links']
        nested_related_names = ['ll_results']
        instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            snapshot=True, **kwargs)

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
    permission_classes = (PartneshipManagerRepPermission,)

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
            return Response(status=status.HTTP_204_NO_CONTENT)


class InterventionAttachmentDeleteView(DestroyAPIView):
    permission_classes = (PartneshipManagerRepPermission,)

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
            return Response(status=status.HTTP_204_NO_CONTENT)


class InterventionResultLinkDeleteView(DestroyAPIView):
    permission_classes = (PartneshipManagerRepPermission,)

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
            return Response(status=status.HTTP_204_NO_CONTENT)


class InterventionAmendmentDeleteView(DestroyAPIView):
    permission_classes = (PartneshipManagerRepPermission,)

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


class InterventionSectorListView(ListAPIView):
    queryset = InterventionSectorLocationLink.objects.all()
    filter_backends = (InterventionScopeFilter, )
    serializer_class = SectorSerializer

    def filter_queryset(self, queryset):
        queryset = super(InterventionSectorListView, self).filter_queryset(queryset)
        print queryset
        return Sector.objects.filter(id__in=queryset.values_list('sector_id', flat=True))


class InterventionSectorLocationLinkDeleteView(DestroyAPIView):
    permission_classes = (PartneshipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            intervention_sector_location = InterventionSectorLocationLink.objects.get(id=int(kwargs['pk']))
        except InterventionSectorLocationLink.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if intervention_sector_location.intervention.status in [Intervention.DRAFT] or \
            request.user in intervention_sector_location.intervention.unicef_focal_points.all() or \
            request.user.groups.filter(name__in=['Partnership Manager',
                                                 'Senior Management Team']).exists():
            intervention_sector_location.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError("You do not have permissions to delete a sector location")


class InterventionListMapView(ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListMapSerializer
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        q = Intervention.objects.detail_qs()\
            .filter(sector_locations__isnull=False).exclude(sector_locations__locations=None)\
            .prefetch_related('sector_locations__locations')
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "country_programme" in query_params.keys():
                queries.append(Q(agreement__country_programme=query_params.get("country_programme")))
            if "sector" in query_params.keys():
                queries.append(Q(sector_locations__sector__id=query_params.get("sector")))
            if "status" in query_params.keys():
                queries.append(Q(status=query_params.get("status")))
            if "partner" in query_params.keys():
                queries.append(Q(agreement__partner=query_params.get("partner")))
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression).distinct()

        return q
