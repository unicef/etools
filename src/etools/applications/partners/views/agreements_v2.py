import functools
import logging
import operator

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext as _

from etools_validator.mixins import ValidatorViewMixin
from rest_framework import status
from rest_framework.generics import DestroyAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework_csv import renderers as r
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.partners.exports_v2 import AgreementCSVRenderer
from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.models import Agreement, AgreementAmendment
from etools.applications.partners.permissions import PartnershipManagerPermission, PartnershipManagerRepPermission
from etools.applications.partners.serializers.agreements_v2 import (
    AgreementAmendmentCreateUpdateSerializer,
    AgreementAmendmentListSerializer,
    AgreementCreateUpdateSerializer,
    AgreementDetailSerializer,
    AgreementListSerializer,
)
from etools.applications.partners.serializers.exports.agreements import (
    AgreementAmendmentExportFlatSerializer,
    AgreementAmendmentExportSerializer,
    AgreementExportFlatSerializer,
    AgreementExportSerializer,
)
from etools.applications.partners.utils import send_agreement_suspended_notification
from etools.applications.partners.validation.agreements import AgreementValid


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

    filters = [
        ('agreement_type', 'agreement_type__in'),
        ('cpStructures', 'country_programme__in'),
        ('status', 'status__in'),
        ('partner_name', 'partner__name__in'),
        ('start', 'start__gt'),
        ('end', 'end__lte'),
        ('special_conditions_pca', 'special_conditions_pca'),
    ]
    search_terms = ('partner__name__icontains', 'agreement_number__icontains')

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
        return super().get_serializer_class()

    def get_queryset(self, format=None):
        q = Agreement.view_objects

        if self.request.query_params:
            queries = []

            queries.extend(self.filter_params())
            queries.append(self.search_params())

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
        response = super().list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', 'csv_flat']:
                response['Content-Disposition'] = "attachment;filename=agreements.csv"

        return response

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        related_fields = ['amendments']
        serializer = self.my_create(request, related_fields, **kwargs)
        self.instance = serializer.instance

        validator = AgreementValid(self.instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError({'errors': validator.errors})

        self.headers = self.get_success_headers(serializer.data)
        if getattr(serializer.instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            self.instance = self.get_object()

        return Response(
            AgreementDetailSerializer(self.instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers)


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
        return super().get_serializer_class()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['amendments']
        self.instance, old_instance, serializer = self.my_update(
            request,
            related_fields,
            **kwargs,
        )

        validator = AgreementValid(
            self.instance,
            old=old_instance,
            user=request.user,
        )

        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        if getattr(self.instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            self.instance = self.get_object()

        # if agreement becomes suspended, send notification
        if self.instance.status == self.instance.SUSPENDED and self.instance.status != old_instance.status:
            send_agreement_suspended_notification(self.instance, request.user)

        return Response(
            AgreementDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
        )


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
        response = super().list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', 'csv_flat']:
                response['Content-Disposition'] = "attachment;filename=agreement_amendments.csv"

        return response


class AgreementAmendmentDeleteView(DestroyAPIView):
    # todo: permission_classes are ignored here. see comments in InterventionAmendmentDeleteView.delete
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            amendment = AgreementAmendment.objects.get(id=int(kwargs['pk']))
        except AgreementAmendment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if amendment.signed_amendment or amendment.signed_date:
            raise ValidationError(_("Cannot delete a signed amendment"))
        else:
            amendment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class AgreementDeleteView(DestroyAPIView):
    # todo: permission_classes are ignored here. see comments in InterventionAmendmentDeleteView.delete
    permission_classes = (PartnershipManagerRepPermission,)

    def delete(self, request, *args, **kwargs):
        try:
            agreement = Agreement.objects.get(id=int(kwargs['pk']))
        except Agreement.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if agreement.status != Agreement.DRAFT or \
                agreement.interventions.count():
            raise ValidationError(_("Cannot delete an agreement that is not Draft or has PDs/SSFAs associated with it"))
        else:
            agreement.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
