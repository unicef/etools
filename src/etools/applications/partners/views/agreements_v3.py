from django.db import transaction

from rest_framework import status
from rest_framework.response import Response

from etools.applications.partners.serializers.agreements_v2 import (
    AgreementCreateUpdateSerializer,
    AgreementDetailSerializer,
    AgreementListSerializer,
)
from etools.applications.partners.views.agreements_v2 import AgreementDetailAPIView, AgreementListAPIView
from etools.applications.partners.views.v3 import PMPBaseViewMixin


class PMPAgreementViewMixin(PMPBaseViewMixin):
    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to agreements that they are associated with
        if self.is_partner_staff():
            qs = qs.filter(partner__in=self.partners())
        return qs


class PMPAgreementListCreateAPIView(
        PMPAgreementViewMixin,
        AgreementListAPIView,
):
    filters = AgreementListAPIView.filters + [
        ('partner_id', 'partner__pk'),
    ]

    def get_serializer_class(self, format=None):
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") in ['csv', 'csv_flat']:
                    return self.get_serializer(query_params.get("format"))
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
        super().update(self, request, *args, **kwargs)
        return Response(
            AgreementDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
        )
