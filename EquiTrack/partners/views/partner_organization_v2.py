import json
import operator
import functools

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework_csv import renderers as r
from rest_framework.views import APIView
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    DestroyAPIView,
)

from EquiTrack.stream_feed.actions import create_snapshot_activity_stream

from partners.models import (
    PartnerStaffMember,
    Intervention,
    GovernmentIntervention,
    PartnerOrganization,
    Assessment,
    PartnerType
)
from partners.serializers.partner_organization_v2 import (
    PartnerOrganizationExportSerializer,
    PartnerOrganizationListSerializer,
    PartnerOrganizationDetailSerializer,
    PartnerOrganizationCreateUpdateSerializer,
    PartnerStaffMemberCreateUpdateSerializer,
    PartnerStaffMemberDetailSerializer,
    PartnerOrganizationHactSerializer,
    AssessmentDetailSerializer
)
from partners.serializers.interventions_v2 import (
    InterventionListSerializer,
)
from partners.serializers.government import (
    GovernmentInterventionListSerializer,
)
from partners.permissions import PartneshipManagerRepPermission
from partners.filters import PartnerScopeFilter
from partners.exports_v2 import PartnerOrganizationCsvRenderer

from EquiTrack.parsers import parse_multipart_data
from EquiTrack.validation_mixins import ValidatorViewMixin

class PartnerOrganizationListAPIView(ListCreateAPIView):
    """
    Create new Partners.
    Returns a list of Partners.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (r.JSONRenderer, PartnerOrganizationCsvRenderer)

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return PartnerOrganizationExportSerializer
        if self.request.method == "POST":
            return PartnerOrganizationCreateUpdateSerializer
        return super(PartnerOrganizationListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = PartnerOrganization.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "partner_type" in query_params.keys():
                queries.append(Q(partner_type=query_params.get("partner_type")))
            if "cso_type" in query_params.keys():
                queries.append(Q(cso_type=query_params.get("cso_type")))
            if "hidden" in query_params.keys():
                hidden = None
                if query_params.get("hidden").lower() == "true":
                    hidden = True
                if query_params.get("hidden").lower() == "false":
                    hidden = False
                if hidden is not None:
                    queries.append(Q(hidden=hidden))
            if "search" in query_params.keys():
                queries.append(
                    Q(name__icontains=query_params.get("search")) |
                    Q(vendor_number__icontains=query_params.get("search")) |
                    Q(short_name__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
        return q

    def list(self, request, format=None):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(PartnerOrganizationListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=partner.csv"

        return response

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # TODO: on create we should call the insight API with the vendor number and use that information to populate:
        # get all staff members
        staff_members = request.data.pop('staff_members', None)

        # validate and save partner org
        po_serializer = self.get_serializer(data=request.data)
        po_serializer.is_valid(raise_exception=True)

        partner = po_serializer.save()

        if staff_members:
            for item in staff_members:
                item.update({u"partner": partner.pk})
            staff_members_serializer = PartnerStaffMemberCreateUpdateSerializer(data=staff_members, many=True)
            try:
                staff_members_serializer.is_valid(raise_exception=True)
            except ValidationError as e:
                e.detail = {'staff_members': e.detail}
                raise e

            staff_members = staff_members_serializer.save()

        headers = self.get_success_headers(po_serializer.data)
        return Response(po_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PartnerOrganizationDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update PartnerOrganization.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationDetailSerializer
    permission_classes = (IsAdminUser,)
    #parser_classes = (FormParser, MultiPartParser)

    SERIALIZER_MAP = {
        'assessments': AssessmentDetailSerializer,
        'staff_members': PartnerStaffMemberCreateUpdateSerializer
    }

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerOrganizationCreateUpdateSerializer
        else:
            return super(PartnerOrganizationDetailAPIView, self).get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['assessments', 'staff_members']

        instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            snapshot=True,  **kwargs)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            po_serializer = self.get_serializer(instance)

        return Response(PartnerOrganizationDetailSerializer(instance).data)


class PartnerOrganizationHactAPIView(ListCreateAPIView):

    """
    Create new Partners.
    Returns a list of Partners.
    """
    permission_classes = (IsAdminUser,)
    queryset = PartnerOrganization.objects.filter(
            Q(documents__status__in=[Intervention.ACTIVE, Intervention.IMPLEMENTED]) |
            (Q(partner_type=u'Government') & Q(work_plans__isnull=False))
        ).distinct()
    serializer_class = PartnerOrganizationHactSerializer


class PartnerStaffMemberListAPIVIew(ListCreateAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)


class PartnerOrganizationAssessmentDeleteView(DestroyAPIView):
    permission_classes = (PartneshipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            assessment = Assessment.objects.get(id=int(kwargs['pk']))
        except Assessment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if assessment.completed_date or assessment.report:
            raise ValidationError("Cannot delete a completed assessment")
        else:
            assessment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class PartnerOrganizationOverviewAPIView(APIView):

    def get(self, request, partner_pk=None):
        partner = get_object_or_404(PartnerOrganization, pk=partner_pk)
        hact_min_reqs = partner.hact_min_requirements

        if isinstance(partner.hact_values, str):
            partner.hact_values = json.loads(partner.hact_values)

        partner_data = {
            'risk_rating': partner.rating,
            'prog_visit_done': partner.hact_values.get('programmatic_visits', 0),
            'prog_visit_mr': hact_min_reqs.get('programme_visits', 0),
            'spot_checks_done': partner.hact_values.get('spot_checks', 0),
            'spot_checks_mr': hact_min_reqs.get('spot_checks', 0),
            'audit_done': partner.hact_values.get('audit_done', 0),
            'audit_mr': partner.hact_values.get('audit_mr', 0),
            'total_ct_cp': partner.total_ct_cp,
            'total_ct_cy': partner.total_ct_cy,
            'planned_cash_transfer': partner.hact_values.get('planned_cash_transfer', 0)
        }

        if not partner.partner_type == PartnerType.GOVERNMENT:
            interventions = Intervention.objects.filter(agreement__partner=partner)

            interventions = InterventionListSerializer(interventions, many=True)

        else:
            interventions = GovernmentIntervention.objects.filter(partner=partner)

            interventions = GovernmentInterventionListSerializer(interventions, many=True)

        return Response({
            'partner': partner_data,
            'interventions': interventions.data,
        }, status=status.HTTP_200_OK)
