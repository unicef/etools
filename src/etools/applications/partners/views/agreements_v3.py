from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.partners.permissions import PMPAgreementPermission
from etools.applications.partners.serializers.agreements_v2 import (
    AgreementCreateUpdateSerializer,
    AgreementDetailSerializer,
    AgreementListSerializer,
)
from etools.applications.partners.views.agreements_v2 import AgreementDetailAPIView, AgreementListAPIView
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.libraries.djangolib.views import ExternalModuleFilterMixin


class PMPAgreementViewMixin(
        PMPBaseViewMixin,
        ExternalModuleFilterMixin,
):
    module2filters = {
        "pmp": ["partner__staff_members__user"],
    }

    def get_queryset(self, format=None):
        return super().get_queryset(module="pmp")


class PMPAgreementListCreateAPIView(
        PMPAgreementViewMixin,
        AgreementListAPIView,
):
    permission_classes = (IsAuthenticated, PMPAgreementPermission)
    filters = AgreementListAPIView.filters + [
        ('partner_id', 'partner__pk'),
    ]

    def get_serializer_class(self, format=None):
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") in ['csv', 'csv_flat']:
                    return AgreementListSerializer
        elif self.request.method == "POST":
            return AgreementCreateUpdateSerializer
        return AgreementListSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            AgreementDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers)


class PMPAgreementDetailUpdateAPIView(
        PMPAgreementViewMixin,
        AgreementDetailAPIView,
):
    def get_serializer_class(self, format=None):
        if self.request.method in ["PATCH"]:
            return AgreementCreateUpdateSerializer
        return AgreementDetailSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            AgreementDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
        )
