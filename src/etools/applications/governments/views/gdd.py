import datetime
import functools
import logging
import operator

from django.db import connection, transaction
from django.db.models import Q
from django.http import Http404
from django.utils.translation import gettext as _

from etools_validator.mixins import ValidatorViewMixin
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.governments.exports import GDDCSVRenderer
from etools.applications.governments.filters import (
    GDDEditableByFilter,
    PartnerNameOrderingFilter,
    PartnerScopeFilter,
    ShowAmendmentsFilter,
)
from etools.applications.governments.models import GDD
from etools.applications.governments.permissions import GDDPermission, PartnershipManagerPermission
from etools.applications.governments.serializers.exports import GDDExportFlatSerializer, GDDExportSerializer
from etools.applications.governments.serializers.gdd import (
    GDDCreateUpdateSerializer,
    GDDDetailSerializer,
    GDDListSerializer,
    MinimalGDDListSerializer,
    RiskSerializer,
)
from etools.applications.governments.serializers.helpers import GDDBudgetCUSerializer, GDDPlannedVisitsCUSerializer
from etools.applications.governments.serializers.result_structure import (
    GDDDetailResultsStructureSerializer,
    GDDResultCUSerializer,
)
from etools.applications.governments.validation.gdds import GDDValid
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import Country
from etools.applications.utils.pagination import AppendablePageNumberPagination
from etools.libraries.djangolib.fields import CURRENCY_LIST


class GDDBaseViewMixin:
    # TODO need to set correct permissions
    # see ch21937
    permission_classes = [IsAuthenticated]

    def is_partner_staff(self):
        """
        Flag indicator shows whether authenticated user is a partner staff
        based on profile organization relationship_type
        """
        is_staff = self.request.user.is_authenticated and self.request.user.profile.organization and \
            'partner' in self.request.user.profile.organization.relationship_types
        if not is_staff and not self.request.user.is_unicef_user():
            raise PermissionDenied()

        return is_staff

    def current_partner(self):
        """List of partners the user is associated with"""
        if not self.is_partner_staff():
            return None
        return PartnerOrganization.objects.filter(
            organization=self.request.user.profile.organization,
            organization__realms__user=self.request.user,
            organization__realms__is_active=True,
        ).first()

    def get_gdd(self, pd_pk):
        try:
            if not self.is_partner_staff():
                return GDD.objects.detail_qs().get(pk=pd_pk)
            return self.gdds().get(pk=pd_pk)
        except GDD.DoesNotExist:
            return None

    def get_gdd_or_404(self, pd_pk):
        pd = self.get_gdd(pd_pk)
        if pd is None:
            raise Http404
        return pd

    def gdds(self):
        """List of PDs user associated with"""
        if not self.is_partner_staff():
            return []
        return GDD.objects.filter(
            partner_focal_points__email=self.request.user.email,
        )

    def offices(self):
        """List of Offices user associated with"""
        if not self.is_partner_staff():
            return []
        return GDD.objects.filter(
            partner_focal_points__email=self.request.user.email,
        )


class GDDMixin(GDDBaseViewMixin):
    def get_partner_staff_qs(self, qs):
        return qs.filter(
            partner=self.current_partner(),
            date_sent_to_partner__isnull=False,
        )

    def get_queryset(self, format=None):
        qs = super().get_queryset()
        if self.request.user.is_unicef_user():
            return qs
        # if partner, limit to interventions that they are associated with
        if self.is_partner_staff():
            return self.get_partner_staff_qs(qs)
        return qs.none()


class GDDListBaseView(ValidatorViewMixin, ListCreateAPIView):
    def get_queryset(self):
        qs = GDD.objects.frs_qs()
        return qs


class GDDListAPIView(QueryStringFilterMixin, ExportModelMixin, GDDListBaseView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = GDDListSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter, ShowAmendmentsFilter)
    renderer_classes = (
        JSONRenderer,
        GDDCSVRenderer,
        CSVFlatRenderer,
    )

    search_terms = ('title__icontains', 'partner__organization__name__icontains', 'number__icontains')
    filters = [
        ('partners', 'partner__in'),
        ('agreements', 'agreement__in'),
        ('document_type', 'document_type__in'),
        ('cp_outputs', 'result_links__cp_output__pk__in'),
        ('country_programme', 'country_programme__in'),
        ('sections', 'sections__in'),
        # ('cluster', 'result_links__key_interventions__applied_indicators__cluster_indicator_title__icontains'),
        ('status', 'status__in'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('start', 'start__gte'),
        ('end', 'end__lte'),
        ('end_after', 'end__gte'),
        ('office', 'offices__in'),
        ('location', 'result_links__gdd_key_interventions__applied_indicators__locations__name__icontains'),
        ('contingency_pd', 'contingency_pd'),
        ('grants', 'frs__fr_items__grant_number__in'),
        ('grants__contains', 'frs__fr_items__grant_number__icontains'),
        ('donors', 'frs__fr_items__donor__icontains'),
        ('budget_owner__in', 'budget_owner__in'),
    ]

    SERIALIZER_MAP = {
        'planned_visits': GDDPlannedVisitsCUSerializer,
        'result_links': GDDResultCUSerializer
    }

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return GDDExportSerializer
                if query_params.get("format") == 'csv_flat':
                    return GDDExportFlatSerializer
            if "verbosity" in query_params.keys():
                if query_params.get("verbosity") == 'minimal':
                    return MinimalGDDListSerializer
        if self.request.method == "POST":
            return GDDCreateUpdateSerializer
        return super().get_serializer_class()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Add a new Intervention
        :return: JSON
        """
        related_fields = [
            'planned_visits',
            'result_links'
        ]
        nested_related_names = ['gdd_key_interventions']

        serializer = self.my_create(request,
                                    related_fields,
                                    nested_related_names=nested_related_names,
                                    **kwargs)

        self.instance = serializer.instance

        validator = GDDValid(self.instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        self.headers = self.get_success_headers(serializer.data)
        if getattr(self.instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            self.instance = self.get_object()
        return Response(
            GDDDetailSerializer(self.instance, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )

    def get_queryset(self, format=None):
        q = super().get_queryset()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "values" in query_params.keys():
                # Used for ghost data - filter in all(), and return straight away.
                try:
                    ids = [int(x) for x in query_params.get("values").split(",")]
                except ValueError:
                    raise ValidationError(_("ID values must be integers"))
                else:
                    return q.filter(id__in=ids)
            if query_params.get("my_partnerships", "").lower() == "true":
                queries.append(Q(unicef_focal_points__in=[self.request.user.id]) |
                               Q(unicef_signatory=self.request.user))

            queries.extend(self.filter_params())
            queries.append(self.search_params())

            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q.order_by('-id')

    def list(self, request):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super().list(request)
        if "format" in query_params.keys():
            if query_params.get("format") in ['csv', "csv_flat"]:
                country = Country.objects.get(schema_name=connection.schema_name)
                today = '{:%Y_%m_%d}'.format(datetime.date.today())
                filename = f"PD_budget_as_of_{today}_{country.country_short_code}"
                response['Content-Disposition'] = f"attachment;filename={filename}.csv"

        return response


class GDDListCreateView(GDDMixin, GDDListAPIView):
    pagination_class = AppendablePageNumberPagination
    permission_classes = (IsAuthenticated, GDDPermission)
    search_terms = (
        'title__icontains',
        'partner__organization__name__icontains',
        'number__icontains',
        'cfei_number__icontains',
    )
    filter_backends = GDDListAPIView.filter_backends + (
        GDDEditableByFilter,
        OrderingFilter,
        PartnerNameOrderingFilter
    )
    ordering_fields = ('number', 'status', 'title', 'start', 'end')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        planned_budget = request.data.get("planned_budget")
        super().create(request, *args, **kwargs)

        # check if setting currency
        if planned_budget and planned_budget.get("currency"):
            currency = planned_budget.get("currency")
            if currency not in CURRENCY_LIST:
                raise ValidationError(f"Invalid currency: {currency}.")
            self.instance.planned_budget.currency = currency
            self.instance.planned_budget.save()

        return Response(
            GDDDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )


class GDDRetrieveUpdateView(GDDMixin, ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = GDD.objects.detail_qs().all()
    permission_classes = (IsAuthenticated, GDDPermission)  # TODO TBD vs PMP

    SERIALIZER_MAP = {
        'planned_visits': GDDPlannedVisitsCUSerializer,
        'result_links': GDDResultCUSerializer,
        'risks': RiskSerializer,
        'planned_budget': GDDBudgetCUSerializer,
    }
    related_fields = [
        'planned_visits',
        'result_links',
        'risks',
        'planned_budget',
    ]
    nested_related_names = [
        'gdd_key_interventions'
    ]
    related_non_serialized_fields = [
        # todo: add other CodedGenericRelation fields. at this moment they're not managed by permissions matrix
        'prc_review_attachment',
        'final_partnership_review',
        'signed_pd_attachment',
    ]

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return GDDCreateUpdateSerializer
        return GDDDetailSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        self.instance, old_instance, serializer = self.my_update(
            request,
            self.related_fields,
            nested_related_names=self.nested_related_names,
            related_non_serialized_fields=self.related_non_serialized_fields,
            **kwargs
        )

        validator = GDDValid(self.instance, old=old_instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        if getattr(self.instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            self.instance = self.get_object()

        context = self.get_serializer_context()
        context['permissions'] = validator.get_permissions(self.instance)
        return Response(
            GDDDetailSerializer(
                self.instance,
                context=context,
            ).data,
        )


class GDDRetrieveResultsStructure(GDDMixin, RetrieveAPIView):
    queryset = GDD.objects.detail_qs()
    serializer_class = GDDDetailResultsStructureSerializer
    permission_classes = (IsAuthenticated, GDDPermission)
