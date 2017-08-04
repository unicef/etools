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

from EquiTrack.utils import get_data_from_insight
from EquiTrack.validation_mixins import ValidatorViewMixin

from partners.models import (
    PartnerStaffMember,
    Intervention,
    PartnerOrganization,
    Assessment,
)
from partners.serializers.partner_organization_v2 import (
    PartnerOrganizationExportSerializer,
    PartnerOrganizationListSerializer,
    PartnerOrganizationDetailSerializer,
    PartnerOrganizationCreateUpdateSerializer,
    PartnerStaffMemberCreateUpdateSerializer,
    PartnerStaffMemberDetailSerializer,
    PartnerOrganizationHactSerializer,
    AssessmentDetailSerializer,
    MinimalPartnerOrganizationListSerializer,
)
from t2f.models import TravelActivity
from partners.permissions import PartneshipManagerRepPermission, PartneshipManagerPermission
from partners.filters import PartnerScopeFilter
from partners.exports_v2 import PartnerOrganizationCsvRenderer


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
            if "verbosity" in query_params.keys():
                if query_params.get("verbosity") == 'minimal':
                    return MinimalPartnerOrganizationListSerializer
        if self.request.method == "POST":
            return PartnerOrganizationCreateUpdateSerializer
        return super(PartnerOrganizationListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = PartnerOrganization.objects.all()
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
                    if query_params.get("format", None) == 'csv':
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
    # parser_classes = (FormParser, MultiPartParser)

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
            snapshot=True, **kwargs)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(PartnerOrganizationDetailSerializer(instance).data)


class PartnerOrganizationHactAPIView(ListCreateAPIView):

    """
    Create new Partners.
    Returns a list of Partners.
    """
    permission_classes = (IsAdminUser,)
    queryset = PartnerOrganization.objects.filter(total_ct_cp__gt=0).all()
    serializer_class = PartnerOrganizationHactSerializer


class PartnerStaffMemberListAPIVIew(ListCreateAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)


class PartnerAuthorizedOfficersListAPIVIew(ListAPIView):
    """
    Returns a list of all signed officers for Partner
    """
    queryset = PartnerStaffMember.objects.filter(signed_interventions__isnull=False).distinct()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter, )


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


class PartnerOrganizationAddView(CreateAPIView):
    """
        Create new Partners.
        Returns a list of Partners.
        """
    serializer_class = PartnerOrganizationCreateUpdateSerializer
    permission_classes = (PartneshipManagerPermission,)

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
            po_serializer = self.get_serializer(data=partner_org)
            po_serializer.is_valid(raise_exception=True)
            po_serializer.save()

            headers = self.get_success_headers(po_serializer.data)
            return Response(po_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PartnerOrganizationDeleteView(DestroyAPIView):
    permission_classes = (PartneshipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            partner = PartnerOrganization.objects.get(id=int(kwargs['pk']))
        except PartnerOrganization.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if partner.agreements.count() > 0:
            raise ValidationError("This partner has agreements associated to it")
        elif TravelActivity.objects.filter(partner=partner).count() > 0:
            raise ValidationError("This partner has trips associated to it")
        else:
            partner.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
