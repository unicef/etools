import operator
import functools
import logging

from rest_framework import status

from django.db import transaction
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from rest_framework_csv import renderers as r
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    DestroyAPIView,
)

from EquiTrack.renderers import CSVFlatRenderer
from EquiTrack.mixins import ExportModelMixin, QueryStringFilterMixin
from EquiTrack.validation_mixins import ValidatorViewMixin
from partners.models import (
    Agreement,
    AgreementAmendment,
)
from partners.serializers.exports.agreements import (
    AgreementAmendmentExportSerializer,
    AgreementAmendmentExportFlatSerializer,
    AgreementExportSerializer,
    AgreementExportFlatSerializer,
)
from partners.serializers.agreements_v2 import (
    AgreementAmendmentListSerializer,
    AgreementListSerializer,
    AgreementCreateUpdateSerializer,
    AgreementDetailSerializer,
    AgreementAmendmentCreateUpdateSerializer
)

from partners.filters import PartnerScopeFilter
from partners.permissions import PartnershipManagerRepPermission, PartnershipManagerPermission

from partners.exports_v2 import AgreementCSVRenderer
from partners.validation.agreements import AgreementValid


class AgreementListAPIView(QueryStringFilterMixin, ExportModelMixin, ValidatorViewMixin, ListCreateAPIView):
    """
    Create new Agreements.
    Returns a list of Agreements.
    """
    serializer_class = AgreementListSerializer
    filter_backends = (PartnerScopeFilter,)
    permission_classes = (PartnershipManagerPermission,)
    renderer_classes = (
        r.JSONRenderer,
        AgreementCSVRenderer,
        CSVFlatRenderer,
    )

    SERIALIZER_MAP = {
        'amendments': AgreementAmendmentCreateUpdateSerializer
    }

    def get_serializer_class(self, format=None):
        """
        Use restricted field set for listing
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return AgreementExportSerializer
                if query_params.get("format") == 'csv_flat':
                    return AgreementExportFlatSerializer
            return AgreementListSerializer
        elif self.request.method == "POST":
            return AgreementCreateUpdateSerializer
        return super(AgreementListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = Agreement.view_objects

        if self.request.query_params:
            queries = []

            filters = (
                ('agreement_type', 'agreement_type__in'),
                ('status', 'status__in'),
                ('partner_name', 'partner__name__in'),
                ('start', 'start__gt'),
                ('end', 'end__lte'),
            )
            search_terms = ['partner__name__icontains', 'agreement_number__icontains']
            queries.extend(self.filter_params(filters))
            queries.append(self.search_params(search_terms))

            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
            else:
                q = q.all()
        return q

    def list(self, request, partner_pk=None, format=None):
        """
            Checks for format query parameter
            :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(AgreementListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', 'csv_flat']:
                response['Content-Disposition'] = "attachment;filename=agreements.csv"

        return response

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        related_fields = ['amendments']
        serializer = self.my_create(request, related_fields, **kwargs)
        instance = serializer.instance

        validator = AgreementValid(instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError({'errors': validator.errors})

        headers = self.get_success_headers(serializer.data)
        if getattr(serializer.instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(
            AgreementDetailSerializer(instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers)


class AgreementDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Agreement.objects.all()
    serializer_class = AgreementDetailSerializer
    permission_classes = (PartnershipManagerPermission,)

    SERIALIZER_MAP = {
        'amendments': AgreementAmendmentCreateUpdateSerializer
    }

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            return AgreementDetailSerializer
        elif self.request.method in ["PATCH"]:
            return AgreementCreateUpdateSerializer
        return super(AgreementDetailAPIView, self).get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['amendments']
        instance, old_instance, serializer = self.my_update(request, related_fields, **kwargs)

        validator = AgreementValid(instance, old=old_instance, user=request.user)

        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()

        return Response(AgreementDetailSerializer(instance, context=self.get_serializer_context()).data)


class AgreementAmendmentListAPIView(ExportModelMixin, ListAPIView):
    """Returns a list of Agreement Amendments"""
    serializer_class = AgreementAmendmentListSerializer
    filter_backends = (PartnerScopeFilter,)
    permission_classes = (PartnershipManagerPermission, )
    renderer_classes = (
        r.JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self, format=None):
        """
        Use restricted field set for listing
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return AgreementAmendmentExportSerializer
            if query_params.get("format") == 'csv_flat':
                return AgreementAmendmentExportFlatSerializer
        return AgreementAmendmentListSerializer

    def get_queryset(self, format=None):
        q = AgreementAmendment.view_objects
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "agreement_number" in query_params.keys():
                queries.append(Q(agreement__agreement_number=query_params.get("agreement_number")))
            if "search" in query_params.keys():
                queries.append(
                    Q(number__icontains=query_params.get("search")) |
                    Q(agreement__agreement_number__icontains=query_params.get("search"))
                )

            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
            else:
                q = q.all()
        return q

    def list(self, request, partner_pk=None, format=None):
        """
            Checks for format query parameter
            :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(AgreementAmendmentListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', 'csv_flat']:
                response['Content-Disposition'] = "attachment;filename=agreement_amendments.csv"

        return response


class AgreementAmendmentDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            amendment = AgreementAmendment.objects.get(id=int(kwargs['pk']))
        except AgreementAmendment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if amendment.signed_amendment or amendment.signed_date:
            raise ValidationError("Cannot delete a signed amendment")
        else:
            amendment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class AgreementDeleteView(DestroyAPIView):
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            agreement = Agreement.objects.get(id=int(kwargs['pk']))
        except Agreement.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if agreement.status != Agreement.DRAFT or \
                agreement.interventions.count():
            raise ValidationError("Cannot delete an agreement that is not Draft or has PDs associated with it")
        else:
            agreement.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
