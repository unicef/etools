import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db import connection, transaction
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import QueryStringFilterMixin, SafeTenantViewSetMixin

from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.organizations.models import Organization
from etools.applications.partners.permissions import user_group_permission
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.users import views as v1, views_v2 as v2
from etools.applications.users.mixins import GroupEditPermissionMixin
from etools.applications.users.models import Country, IPAdmin, IPAuthorizedOfficer, IPEditor, Realm
from etools.applications.users.permissions import IsActiveInRealm, IsPartnershipManager
from etools.applications.users.serializers import SimpleGroupSerializer, SimpleOrganizationSerializer
from etools.applications.users.serializers_v3 import (
    CountryDetailSerializer,
    ExternalUserSerializer,
    MinimalUserDetailSerializer,
    MinimalUserSerializer,
    ProfileRetrieveUpdateSerializer,
    UserRealmCreateSerializer,
    UserRealmRetrieveSerializer,
    UserRealmUpdateSerializer,
)
from etools.applications.utils.pagination import AppendablePageNumberPagination

logger = logging.getLogger(__name__)


class ChangeUserCountryView(v1.ChangeUserCountryView):
    """Stub for ChangeUserCountryView"""


class ChangeUserOrganizationView(APIView):
    """
    Allows a user to switch organization context if they have access to more than one
    """

    ERROR_MESSAGES = {
        'organization_does_not_exist': 'The organization that you are attempting to switch to does not exist',
        'access_to_organization_denied': 'You do not have access to the organization you are trying to switch to'
    }

    next_param = 'next'

    permission_classes = (IsAuthenticated, )

    def get_organization_id(self):
        return self.request.data.get('organization', None) or self.request.query_params.get('organization', None)

    def get_organization(self):
        organization_id = self.get_organization_id()
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            raise DjangoValidationError(
                self.ERROR_MESSAGES['organization_does_not_exist'],
                code='organization_does_not_exist'
            )
        return organization

    def change_organization(self):
        user = self.request.user
        organization = self.get_organization()

        if organization == user.profile.organization:
            return

        if organization not in user.profile.organizations_available.all():
            raise DjangoValidationError(self.ERROR_MESSAGES['access_to_organization_denied'],
                                        code='access_to_organization_denied')

        user.profile.organization = organization
        user.profile.save(update_fields=['organization'])

    def get_redirect_url(self):
        return self.request.GET.get(self.next_param, '/')

    def get(self, request, *args, **kwargs):
        try:
            self.change_organization()
        except DjangoValidationError as err:
            return HttpResponseForbidden(str(err))

        return HttpResponseRedirect(self.get_redirect_url())

    def post(self, request, format=None):
        try:
            self.change_organization()
        except DjangoValidationError as err:
            if err.code == 'access_to_organization_denied':
                status_code = status.HTTP_403_FORBIDDEN
            else:
                status_code = status.HTTP_400_BAD_REQUEST
            return Response(str(err), status=status_code)

        return Response(status=status.HTTP_204_NO_CONTENT)


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
    queryset = get_user_model().objects.all().select_related('profile').prefetch_related('realms')
    serializer_class = MinimalUserSerializer
    permission_classes = (IsAuthenticated, )
    pagination_class = AppendablePageNumberPagination
    search_terms = ('email__icontains', 'first_name__icontains', 'middle_name__icontains', 'last_name__icontains')

    filters = (
        ('group', 'realms__group__name__in'),
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
        ).order_by("first_name")


class CountryView(v2.CountryView):
    serializer_class = CountryDetailSerializer


class PartnerOrganizationListView(ListAPIView):
    """
    Gets a list of organizations from partners given a country id for
    the Partnership Manager currently logged in.
    """
    model = Organization
    serializer_class = SimpleOrganizationSerializer
    permission_classes = (IsAuthenticated, IsPartnershipManager)

    def get_root_object(self):
        return get_object_or_404(Country, pk=self.kwargs.get('country_pk'))

    def get_queryset(self):
        country = self.get_root_object()

        if not self.request.user.is_partnership_manager:
            return self.model.objects.none()
        # returns only Partner Organizations that are not marked for deletion
        return self.model.objects\
            .filter(partner__isnull=False, partner__deleted_flag=False, realms__country=country)\
            .distinct()


class GroupPermissionsViewSet(GroupEditPermissionMixin, APIView):
    """
    Returns a list of allowed User Groups and the user add permission for Access Management Portal (AMP)
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        response_data = {
            "groups": SimpleGroupSerializer(self.get_user_allowed_groups(), many=True).data,
            "can_add_user": self.can_add_user()
        }
        return Response(response_data)


class UserRealmViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    model = get_user_model()
    serializer_class = UserRealmRetrieveSerializer

    pagination_class = DynamicPageNumberPagination
    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)

    search_fields = ('first_name', 'last_name', 'email', 'profile__job_title')
    filter_fields = ('is_active', )
    ordering_fields = ('first_name', 'last_name', 'email', 'last_login')

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = (
                IsAuthenticated, IsActiveInRealm)
        if self.action == 'create':
            self.permission_classes = (
                IsAuthenticated,
                user_group_permission(IPAdmin.name, IPAuthorizedOfficer.name) | IsPartnershipManager)
        if self.action == 'partial_update':
            self.permission_classes = (
                IsAuthenticated,
                user_group_permission(
                    IPEditor.name, IPAdmin.name,
                    IPAuthorizedOfficer.name, UNICEFAuditFocalPoint.name) | IsPartnershipManager
            )
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserRealmCreateSerializer
        if self.request.method == "PATCH":
            return UserRealmUpdateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        organization_id = self.request.query_params.get('organization_id')
        if organization_id:
            if self.request.user.is_partnership_manager:
                organization = get_object_or_404(Organization, pk=organization_id)
            else:
                return self.model.objects.none()
        else:
            organization = self.request.user.profile.organization

        context_realms_qs = Realm.objects.filter(
            country=connection.tenant,
            organization=organization,
        )
        return self.model.objects \
            .filter(realms__in=context_realms_qs) \
            .prefetch_related(Prefetch('realms', queryset=context_realms_qs))\
            .distinct()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(UserRealmRetrieveSerializer(instance=serializer.instance).data,
                        status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        instance = get_object_or_404(self.model, **filter_kwargs)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(UserRealmRetrieveSerializer(instance=serializer.instance).data)


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
        from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember

        qs = self.queryset.filter(realms__country=connection.tenant)

        # exclude user if connected with TPMPartnerStaffMember,
        # and/or AuditorStaffMember
        tpm_staff = TPMPartnerStaffMember.objects.filter(
            user__pk=OuterRef("pk"),
        )
        audit_staff = get_user_model().objects.filter(
            pk=OuterRef("pk"),
            realms__country=connection.tenant,
            realms__organization__auditorfirm__isnull=False,
        )
        qs = qs.exclude(
            pk__in=Subquery(tpm_staff.values("user_id"))
        ).exclude(
            pk__in=Subquery(audit_staff.values("pk"))
        )

        return qs
