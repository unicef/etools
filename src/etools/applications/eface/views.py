from django.contrib.auth import get_user_model
from django.db import transaction

from django_filters.rest_framework import DjangoFilterBackend
from etools_validator.mixins import ValidatorViewMixin
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, SafeTenantViewSetMixin

from etools.applications.eface.filters import EFaceFormFilterSet
from etools.applications.eface.models import EFaceForm
from etools.applications.eface.permissions import IsPartnerFocalPointPermission, IsUNICEFFocalPointPermission
from etools.applications.eface.serializers import EFaceFormListSerializer, EFaceFormSerializer, FormUserSerializer
from etools.applications.eface.validation.validator import EFaceFormValid
from etools.applications.field_monitoring.permissions import IsEditAction, IsListAction, IsObjectAction, IsReadAction
from etools.applications.partners.permissions import UserIsPartnerStaffMemberPermission, UserIsStaffPermission


class EFaceBaseViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]


class EFaceFormsViewSet(
    EFaceBaseViewSet,
    ValidatorViewMixin,
    viewsets.ModelViewSet,
):
    """
    Retrieve and Update Agreement.
    """
    queryset = EFaceForm.objects.select_related('intervention').order_by('id')
    serializer_class = EFaceFormSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)
    filter_class = EFaceFormFilterSet
    ordering_fields = (
        'created', 'status',
    )
    search_fields = ('reference_number',)
    pagination_class = DynamicPageNumberPagination
    serializer_action_classes = {
        'list': EFaceFormListSerializer,
    }
    permission_classes = EFaceBaseViewSet.permission_classes + [
        IsReadAction |
        (IsEditAction & IsListAction & UserIsPartnerStaffMemberPermission) |
        (IsEditAction & (IsObjectAction & (IsPartnerFocalPointPermission | IsUNICEFFocalPointPermission)))
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        if 'UNICEF User' not in [g.name for g in self.request.user.groups.all()]:
            queryset = queryset.filter(intervention__partner_focal_points__user=self.request.user).distinct()

        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        related_fields = []
        nested_related_names = []
        serializer = self.my_create(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )
        instance = serializer.instance

        validator = EFaceFormValid(instance, user=request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

        headers = self.get_success_headers(serializer.data)

        return Response(
            self.get_serializer_class()(instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = []
        nested_related_names = []
        instance, old_instance, _serializer = self.my_update(
            request,
            related_fields,
            nested_related_names=nested_related_names,
            **kwargs
        )

        validator = EFaceFormValid(instance, old=old_instance, user=request.user)
        if not validator.is_valid:
            raise ValidationError(validator.errors)

        return Response(self.get_serializer_class()(instance, context=self.get_serializer_context()).data)


class UsersViewSet(EFaceBaseViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = FormUserSerializer
    permission_classes = EFaceBaseViewSet.permission_classes + [UserIsStaffPermission]

    def get_queryset(self, pk=None):
        qs = super().get_queryset()

        return qs.filter(
            profile__country=self.request.user.profile.country,
            is_staff=True,
        ).prefetch_related('profile').order_by("first_name")
