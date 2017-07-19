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
    CreateAPIView
)

from EquiTrack.utils import get_data_from_insight
from EquiTrack.validation_mixins import ValidatorViewMixin

from partners.models import (
    PartnerStaffMember,
    Intervention,
    PartnerOrganization,
    Assessment,
)
from partners.serializers.dashboards import InterventionDashSerializer
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

class InterventionPartnershipDashView(ListCreateAPIView):
    """InterventionDashView
    Returns a list of Interventions.
    """
    serializer_class = InterventionDashSerializer
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        q = Intervention.objects.all()
        return q
