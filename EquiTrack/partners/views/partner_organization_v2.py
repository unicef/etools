import operator
import functools
import datetime
from decimal import Decimal

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
    CreateAPIView,
    ListAPIView)

from EquiTrack.mixins import ExportModelMixin
from EquiTrack.renderers import CSVFlatRenderer
from EquiTrack.utils import get_data_from_insight
from EquiTrack.validation_mixins import ValidatorViewMixin

from partners.models import (
    PartnerStaffMember,
    PartnerOrganization,
    Assessment,
    PlannedEngagement
)
from partners.permissions import ListCreateAPIMixedPermission
from partners.serializers.exports.partner_organization import (
    AssessmentExportFlatSerializer,
    AssessmentExportSerializer,
    PartnerOrganizationExportFlatSerializer,
    PartnerOrganizationExportSerializer,
    PartnerStaffMemberExportFlatSerializer,
    PartnerStaffMemberExportSerializer,
)
from partners.serializers.partner_organization_v2 import (
    AssessmentDetailSerializer,
    PartnerOrganizationListSerializer,
    PartnerOrganizationDetailSerializer,
    PartnerOrganizationCreateUpdateSerializer,
    PartnerStaffMemberCreateUpdateSerializer,
    PartnerStaffMemberDetailSerializer,
    PartnerOrganizationHactSerializer,
    MinimalPartnerOrganizationListSerializer,
    PlannedEngagementNestedSerializer,
    PlannedEngagementSerializer)
from partners.views.helpers import set_tenant_or_fail
from t2f.models import TravelActivity
from partners.permissions import PartnershipManagerRepPermission, PartnershipManagerPermission
from partners.filters import PartnerScopeFilter
from partners.exports_v2 import (
    PartnerOrganizationCSVRenderer,
    PartnerOrganizationHactCsvRenderer,
)


class PartnerOrganizationListAPIView(ExportModelMixin, ListCreateAPIView):
    """
    Create new Partners.
    Returns a list of Partners.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationListSerializer
    permission_classes = (ListCreateAPIMixedPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        PartnerOrganizationCSVRenderer,
        CSVFlatRenderer
    )

    def get_serializer_class(self, format=None):
        """
        Use restricted field set for listing
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return PartnerOrganizationExportSerializer
            if query_params.get("format") == 'csv_flat':
                return PartnerOrganizationExportFlatSerializer
        if "verbosity" in query_params.keys():
            if query_params.get("verbosity") == 'minimal':
                return MinimalPartnerOrganizationListSerializer
        return super(PartnerOrganizationListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = PartnerOrganization.objects.all()
        query_params = self.request.query_params
        workspace = query_params.get('workspace', None)
        if workspace:
            set_tenant_or_fail(workspace)

        if query_params:
            queries = []

            if "values" in query_params.keys():
                # Used for ghost data - filter in all(), and return straight away.
                try:
                    ids = [int(x) for x in query_params.get("values").split(",")]
                except ValueError:
                    raise ValidationError("ID values must be integers")
                else:
                    return PartnerOrganization.objects.filter(id__in=ids)
            if "partner_type" in query_params.keys():
                queries.append(Q(partner_type=query_params.get("partner_type")))
            if "cso_type" in query_params.keys():
                queries.append(Q(cso_type=query_params.get("cso_type")))
            if "hidden" in query_params.keys():
                hidden = None
                if query_params.get("hidden").lower() == "true":
                    hidden = True
                    # return all partners when exporting and hidden=true
                    if query_params.get("format", None) in ['csv', 'csv_flat']:
                        hidden = None
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
            if query_params.get("format") in ['csv', 'csv_flat']:
                response['Content-Disposition'] = "attachment;filename=partner.csv"

        return response


class PartnerOrganizationDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update PartnerOrganization.
    """
    queryset = PartnerOrganization.objects.select_related('planned_engagement')
    serializer_class = PartnerOrganizationDetailSerializer
    permission_classes = (IsAdminUser,)
    # parser_classes = (FormParser, MultiPartParser)

    SERIALIZER_MAP = {
        'assessments': AssessmentDetailSerializer,
        'staff_members': PartnerStaffMemberCreateUpdateSerializer,
        'planned_engagement': PlannedEngagementNestedSerializer
    }

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerOrganizationCreateUpdateSerializer
        else:
            return super(PartnerOrganizationDetailAPIView, self).get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['assessments', 'staff_members', 'planned_engagement']

        instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            **kwargs)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(PartnerOrganizationDetailSerializer(instance).data)


class PartnerOrganizationHactAPIView(ListAPIView):

    """
    Create new Partners.
    Returns a list of Partners.
    """
    permission_classes = (IsAdminUser,)
    queryset = PartnerOrganization.objects.select_related('planned_engagement').prefetch_related(
        'staff_members', 'assessments').filter(Q(reported_cy__gt=0) | Q(total_ct_cy__gt=0))
    serializer_class = PartnerOrganizationHactSerializer
    renderer_classes = (r.JSONRenderer, PartnerOrganizationHactCsvRenderer)

    def list(self, request, format=None):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(PartnerOrganizationHactAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=hact_dashboard.csv"
        return response


class PlannedEngagementAPIView(ListAPIView):

    """
    Returns a list of Planned Engagements.
    """
    permission_classes = (IsAdminUser,)
    queryset = PlannedEngagement.objects.all()
    serializer_class = PlannedEngagementSerializer


class PartnerStaffMemberListAPIVIew(ExportModelMixin, ListAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return PartnerStaffMemberExportSerializer
            if query_params.get("format") == 'csv_flat':
                return PartnerStaffMemberExportFlatSerializer
        return super(PartnerStaffMemberListAPIVIew, self).get_serializer_class()


class PartnerOrganizationAssessmentListView(ExportModelMixin, ListAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = Assessment.objects.all()
    serializer_class = AssessmentDetailSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return AssessmentExportSerializer
            if query_params.get("format") == 'csv_flat':
                return AssessmentExportFlatSerializer
        return super(PartnerOrganizationAssessmentListView, self).get_serializer_class()


class PartnerOrganizationAssessmentDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

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


class PartnerOrganizationAddView(CreateAPIView):
    """
        Create new Partners.
        Returns a list of Partners.
        """
    serializer_class = PartnerOrganizationCreateUpdateSerializer
    permission_classes = (PartnershipManagerPermission,)

    # TODO: let's aim to standardize where mapping goes
    MAPPING = {
        'vendor_number': "VENDOR_CODE",
        'name': "VENDOR_NAME",
        'partner_type': 'PARTNER_TYPE_DESC',
        'cso_type': 'CSO_TYPE',
        'core_values_assessment_date': "CORE_VALUE_ASSESSMENT_DT",
        'rating': 'RISK_RATING',
        'type_of_assessment': "TYPE_OF_ASSESSMENT",
        'last_assessment_date': "DATE_OF_ASSESSMENT",
        'address': "STREET",
        'postal_code': "POSTAL_CODE",
        'city': "CITY",
        'country': "COUNTRY",
        'phone_number': 'PHONE_NUMBER',
        'email': "EMAIL",
        'total_ct_cp': "TOTAL_CASH_TRANSFERRED_CP",
        'total_ct_cy': "TOTAL_CASH_TRANSFERRED_CY",
        'deleted_flag': "MARKED_FOR_DELETION",
        'blocked': "POSTING_BLOCK",
    }

    cso_type_mapping = {
        "International NGO": u'International',
        "National NGO": u'National',
        "Community based organization": u'Community Based Organization',
        "Academic Institution": u'Academic Institution'
    }

    type_mapping = {
        "BILATERAL / MULTILATERAL": u'Bilateral / Multilateral',
        "CIVIL SOCIETY ORGANIZATION": u'Civil Society Organization',
        "GOVERNMENT": u'Government',
        "UN AGENCY": u'UN Agency',
    }

    def get_value_for_field(self, field, value):
        if field in ['core_values_assessment_date', 'last_assessment_date']:
            return datetime.datetime.strptime(value, '%d-%b-%y').date()
        if field in ['partner_type']:
            return self.type_mapping[value]
        if field in ['cso_type']:
            return self.cso_type_mapping[value]
        if field in ['total_ct_cp', 'total_ct_cy']:
            return Decimal(value.replace(",", ""))
        return value

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        vendor = self.request.query_params.get('vendor', None)
        if vendor is None:
            return Response({"error": "No vendor number provided for Partner Organization"},
                            status=status.HTTP_400_BAD_REQUEST)

        valid_response, response = get_data_from_insight('GetPartnerDetailsInfo_json/{vendor_code}',
                                                         {"vendor_code": vendor})
        if not valid_response:
            return Response({"error": response}, status=status.HTTP_400_BAD_REQUEST)

        partner_resp = response["ROWSET"]["ROW"]
        try:
            partner_org = PartnerOrganization.objects.get(vendor_number=partner_resp[self.MAPPING['vendor_number']])
            # TODO standardize error keys and abstract error messages where possible
            return Response({"error": 'Partner Organization already exists with this vendor number'},
                            status=status.HTTP_400_BAD_REQUEST)
        except PartnerOrganization.DoesNotExist:
            partner_org = {
                k: self.get_value_for_field(
                    k,
                    partner_resp[v]) if v in partner_resp.keys() else None for k,
                v in self.MAPPING.items()}
            partner_org['vision_synced'] = True
            partner_org['deleted_flag'] = True if self.MAPPING['deleted_flag'] in partner_resp.keys() else False
            partner_org['blocked'] = True if self.MAPPING['blocked'] in partner_resp.keys() else False
            po_serializer = self.get_serializer(data=partner_org)
            po_serializer.is_valid(raise_exception=True)
            po_serializer.save()

            headers = self.get_success_headers(po_serializer.data)
            return Response(po_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PartnerOrganizationDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            partner = PartnerOrganization.objects.get(id=int(kwargs['pk']))
        except PartnerOrganization.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if partner.agreements.exclude(status='draft').count() > 0:
            raise ValidationError("There was a PCA/SSFA signed with this partner or a transaction was performed "
                                  "against this partner. The Partner record cannot be deleted")
        elif TravelActivity.objects.filter(partner=partner).count() > 0:
            raise ValidationError("This partner has trips associated to it")
        elif partner.total_ct_cp > 0:
            raise ValidationError("This partner has cash transactions associated to it")
        else:
            partner.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
