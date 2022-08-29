import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.db.models import OuterRef, Q, Subquery

from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin, SafeTenantViewSetMixin

from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.users import views as v1, views_v2 as v2
from etools.applications.users.serializers_v3 import (
    CountryDetailSerializer,
    ExternalUserSerializer,
    MinimalUserDetailSerializer,
    MinimalUserSerializer,
    ProfileRetrieveUpdateSerializer,
)
from etools.applications.utils.pagination import AppendablePageNumberPagination

logger = logging.getLogger(__name__)


class ChangeUserCountryView(v1.ChangeUserCountryView):
    """Stub for ChangeUserCountryView"""


class MyProfileAPIView(v1.MyProfileAPIView):
    serializer_class = ProfileRetrieveUpdateSerializer


class UsersDetailAPIView(RetrieveAPIView):
    """
    Retrieve a User in the current country
    """
    queryset = get_user_model().objects.all()
    serializer_class = MinimalUserDetailSerializer

    def retrieve(self, request, pk=None):
        """
        Returns a UserProfile object for this PK
        """
        data = {}
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except get_user_model().DoesNotExist:
            pass

        return Response(
            data,
            status=status.HTTP_200_OK
        )


class UsersListAPIView(PMPBaseViewMixin, QueryStringFilterMixin, ListAPIView):
    """
    Gets a list of Unicef Staff users in the current country.
    Country is determined by the currently logged in user.
    """
    model = get_user_model()
    queryset = get_user_model().objects.all().select_related('profile').prefetch_related('realm_set')
    serializer_class = MinimalUserSerializer
    permission_classes = (IsAuthenticated, )
    pagination_class = AppendablePageNumberPagination
    search_terms = ('email__icontains', 'first_name__icontains', 'middle_name__icontains', 'last_name__icontains')

    filters = (
        ('group', 'realm_set__group__name__in'),
        ('is_active', 'is_active'),
    )

    def get_queryset(self, pk=None):
        qs = super().get_queryset()
        # note that if user_ids is set we do not filter by current tenant,
        # I guess this is the expected behavior
        user_ids = self.request.query_params.get("values", None)
        if user_ids:
            try:
                user_ids = [int(x) for x in user_ids.split(",")]
            except ValueError:
                raise ValidationError("Query parameter values are not integers")
            else:
                qs = qs.filter(id__in=user_ids)

        if self.is_partner_staff():
            emails = []
            for p in self.partners():
                emails += p.staff_members.values_list("email", flat=True)
            qs = qs.filter(email__in=emails)
        elif self.request.user.is_staff:
            qs = qs.filter(
                profile__country=self.request.user.profile.country,
                is_staff=True,
            )
        else:
            raise PermissionDenied

        return qs.prefetch_related(
            'profile',
            'realm_set',
            'user_permissions',
        ).order_by("first_name")


class CountryView(v2.CountryView):
    serializer_class = CountryDetailSerializer


class ExternalUserViewSet(
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet,
):
    model = get_user_model()
    queryset = get_user_model().objects.exclude(
        Q(email__endswith="@unicef.org") | Q(is_staff=True) | Q(is_superuser=True) |
        Q(partner_staff_member__isnull=False)).all()
    serializer_class = ExternalUserSerializer
    permission_classes = (IsAdminUser, )

    def get_queryset(self):
        from etools.applications.audit.purchase_order.models import AuditorStaffMember
        from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember

        qs = self.queryset.filter(
            realm_set__country__schema_name=connection.schema_name,
        )

        # exclude user if connected with TPMPartnerStaffMember,
        # and/or AuditorStaffMember
        tpm_staff = TPMPartnerStaffMember.objects.filter(
            user__pk=OuterRef("pk"),
        )
        audit_staff = AuditorStaffMember.objects.filter(
            user__pk=OuterRef("pk"),
        )
        qs = qs.exclude(
            pk__in=Subquery(tpm_staff.values("user_id"))
        ).exclude(
            pk__in=Subquery(audit_staff.values("user_id"))
        )

        return qs
