import copy
import datetime
import functools
import logging
import operator

from django.db import connection, transaction, utils
from django.db.models import Q
from django.http import Http404
from django.utils.translation import gettext as _

from etools_validator.mixins import ValidatorViewMixin
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    get_object_or_404,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.status import is_success
from rest_framework.views import APIView
from rest_framework_csv import renderers as r
from unicef_restlib.views import QueryStringFilterMixin
from unicef_vision.exceptions import VisionException

from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.funds.serializers import FRsSerializer
from etools.applications.funds.tasks import sync_single_delegated_fr
from etools.applications.governments.exports import GDDCSVRenderer
from etools.applications.governments.filters import (
    GDDEditableByFilter,
    GDDFilter,
    PartnerNameOrderingFilter,
    PartnerScopeFilter,
    ShowAmendmentsFilter,
)
from etools.applications.governments.models import (
    EWPActivity,
    EWPOutput,
    GDD,
    GDDActivity,
    GDDAmendment,
    GDDAttachment,
    GDDKeyIntervention,
    GDDReportingRequirement,
    GDDResultLink,
    GDDRisk,
    GDDSpecialReportingRequirement,
    GDDSupplyItem,
    GovernmentEWP,
)
from etools.applications.governments.permissions import (
    AmendmentSessionOnlyDeletePermission,
    gdd_field_is_editable_permission,
    GDDAmendmentIsNotCompleted,
    GDDPermission,
    GDDPermissions,
    IsGDDBudgetOwnerPermission,
    PartnershipManagerPermission,
    UserIsNotPartnerStaffMemberPermission,
    UserIsUnicefFocalPoint,
)
from etools.applications.governments.serializers.amendments import GDDAmendmentCUSerializer
from etools.applications.governments.serializers.exports.gdd import (
    GDDAmendmentExportFlatSerializer,
    GDDAmendmentExportSerializer,
    GDDExportFlatSerializer,
    GDDExportSerializer,
)
from etools.applications.governments.serializers.gdd import (
    GDDCreateUpdateSerializer,
    GDDDetailSerializer,
    GDDListSerializer,
    GDDResultLinkSimpleCUSerializer,
    GDDSupplyItemSerializer,
    GDDSupplyItemUploadSerializer,
    MinimalGDDListSerializer,
    RiskSerializer,
)
from etools.applications.governments.serializers.helpers import (
    GDDAttachmentSerializer,
    GDDBudgetCUSerializer,
    GDDPlannedVisitsCUSerializer,
    GDDReportingRequirementCreateSerializer,
    GDDReportingRequirementListSerializer,
    GDDSpecialReportingRequirementSerializer,
)
from etools.applications.governments.serializers.result_structure import (
    EWPSyncListResultSerializer,
    EWPSyncUpdateResultSerializer,
    GDDActivityCreateSerializer,
    GDDDetailResultsStructureSerializer,
    GDDKeyInterventionCUSerializer,
    GDDResultCUSerializer,
)
from etools.applications.governments.tasks import send_gdd_amendment_added_notification
from etools.applications.governments.validation.gdds import GDDValid
from etools.applications.governments.views.gdd_snapshot import FullGDDSnapshotDeleteMixin
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


class DetailedGDDResponseMixin:
    detailed_gdd_methods = ['post', 'put', 'patch']
    detailed_gdd_serializer = GDDDetailSerializer

    def get_gdd(self):
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.method.lower() in self.detailed_gdd_methods and is_success(response.status_code):
            response.data['gdd'] = self.detailed_gdd_serializer(
                instance=self.get_gdd(),
                context=self.get_serializer_context(),
            ).data
        return response


class GDDListBaseView(ValidatorViewMixin, ListCreateAPIView):
    def get_queryset(self):
        qs = GDD.objects.frs_qs()
        return qs


class GDDListAPIView(QueryStringFilterMixin, ExportModelMixin, GDDListBaseView):
    """
    Create new GDDS.
    Returns a list of GDDs.
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
        ('lead_section', 'lead_section__in'),
        ('sections', 'sections__in'),
        # ('cluster', 'result_links__key_interventions__applied_indicators__cluster_indicator_title__icontains'),
        ('status', 'status__in'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('start', 'start__gte'),
        ('end', 'end__lte'),
        ('end_after', 'end__gte'),
        ('office', 'offices__in'),
        ('location', 'result_links__gdd_key_interventions__applied_indicators__locations__name__icontains'),
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
        Add a new gdd
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
                filename = f"GDD_budget_as_of_{today}_{country.country_short_code}"
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
    Retrieve and Update GDD
    """
    queryset = GDD.objects.detail_qs().all()
    permission_classes = (IsAuthenticated, GDDPermission)

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


class GDDSyncResultsStructure(RetrieveUpdateAPIView):
    queryset = EWPOutput.objects.select_related("workplan", "cp_output")
    permission_classes = (IsAuthenticated, GDDPermission)

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return EWPSyncUpdateResultSerializer
        return EWPSyncListResultSerializer

    def get_object(self):
        return get_object_or_404(GDD.objects.detail_qs().all(), pk=self.kwargs.get('pk'))

    def get(self, request, *args, **kwargs):
        gpd = self.get_object()
        partner_ewp_activities = EWPActivity.objects.filter(partners__in=[gpd.partner or gpd.agreement.partner])
        partner_ewps = GovernmentEWP.objects.filter(ewp_activities__in=partner_ewp_activities).distinct()

        qs = EWPOutput.objects.filter(workplan__in=partner_ewps)
        return Response(self.get_serializer(qs, many=True).data)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object(), data=request.data, partial=True, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(status=status.HTTP_200_OK)


class GDDResultLinkListCreateView(ListCreateAPIView):

    serializer_class = GDDResultLinkSimpleCUSerializer
    permission_classes = (PartnershipManagerPermission,)
    queryset = GDDResultLink.objects.select_related('cp_output', 'cp_output__cp_output')

    def create(self, request, *args, **kwargs):
        raw_data = copy.deepcopy(request.data)
        raw_data['gdd'] = kwargs.get('pk', None)

        serializer = self.get_serializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class GDDResultLinkUpdateView(FullGDDSnapshotDeleteMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = GDDResultLinkSimpleCUSerializer
    permission_classes = (PartnershipManagerPermission,
                          IsReadAction | (IsEditAction & gdd_field_is_editable_permission('key_interventions')),)
    filter_backends = (GDDFilter,)
    renderer_classes = (JSONRenderer,)
    queryset = GDDResultLink.objects.all()

    @functools.cache
    def get_gdd(self):
        return GDD.objects.filter(pk=self.kwargs.get('gdd_pk')).first()

    def get_root_object(self):
        return self.get_gdd()

    def delete(self, request, *args, **kwargs):
        # make sure there are no indicators added to this LLO
        obj = self.get_object()
        if obj.gdd_key_interventions.exists():
            raise ValidationError(_('This CP Output cannot be removed from this GDD because there are nested'
                                  ' Results, please remove all Document Results to continue'))
        return super().delete(request, *args, **kwargs)


class GDDKeyInterventionViewMixin(DetailedGDDResponseMixin):
    queryset = GDDKeyIntervention.objects.select_related('result_link').order_by('id')
    serializer_class = GDDKeyInterventionCUSerializer
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & gdd_field_is_editable_permission('key_interventions')),
        AmendmentSessionOnlyDeletePermission,
    ]

    def get_root_object(self):
        return GDD.objects.filter(pk=self.kwargs.get('pk')).first()

    def get_gdd(self):
        return self.get_root_object()

    def get_serializer(self, *args, **kwargs):
        kwargs['gdd'] = self.get_root_object()
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(result_link__gdd=self.get_root_object())


class GDDKeyInterventionListCreateView(GDDKeyInterventionViewMixin, ListCreateAPIView):
    pass


class GDDKeyInterventionDetailUpdateView(
    GDDKeyInterventionViewMixin,
    FullGDDSnapshotDeleteMixin,
    RetrieveUpdateDestroyAPIView,
):
    def get_root_object(self):
        return GDD.objects.filter(pk=self.kwargs.get('gdd_pk')).first()

    def perform_destroy(self, instance):
        # do cleanup if pd output is still not associated to cp output
        result_link = instance.result_link
        if instance.gdd_activities.exists():
            raise ValidationError("Before deleting the Key Intervention,"
                                  " you must delete the activities associated to ensure integrity")
        instance.delete()
        if not result_link.gdd_key_interventions.exists():
            result_link.delete()


class GDDActivityMixinView(DetailedGDDResponseMixin):
    queryset = GDDActivity.objects.prefetch_related('items', 'time_frames').order_by('id')
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & gdd_field_is_editable_permission('key_interventions')),
        AmendmentSessionOnlyDeletePermission,
    ]
    serializer_class = GDDActivityCreateSerializer

    def get_root_object(self):
        return GDD.objects.filter(pk=self.kwargs.get('gdd_pk')).first()

    def get_gdd(self):
        return self.get_root_object()

    def get_parent_object(self):
        if not hasattr(self, '_result'):
            self._result = GDDKeyIntervention.objects.filter(
                result_link__gdd_id=self.kwargs.get('gdd_pk'),
                pk=self.kwargs.get('key_intervention_pk')
            ).first()
        return self._result

    def get_serializer(self, *args, **kwargs):
        kwargs['gdd'] = self.get_root_object()
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(key_intervention=self.get_parent_object())


class GDDActivityCreateView(GDDActivityMixinView, CreateAPIView):

    def perform_create(self, serializer):
        serializer.save(key_intervention=self.get_parent_object())


class GDDActivityDetailUpdateView(GDDActivityMixinView, RetrieveUpdateDestroyAPIView):
    pass


class GDDSupplyItemMixin(GDDMixin, DetailedGDDResponseMixin):
    queryset = GDDSupplyItem.objects.all()
    serializer_class = GDDSupplyItemSerializer
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & gdd_field_is_editable_permission('supply_items'))
    ]

    def get_partner_staff_qs(self, qs):
        return qs.filter(
            gdd__partner=self.current_partner(),
            gdd__date_sent_to_partner__isnull=False,
        ).distinct()

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        return qs.filter(gdd=self.get_gdd())

    def get_root_object(self):
        return self.get_gdd()

    def get_gdd(self):
        return super().get_gdd(self.kwargs.get("gdd_pk"))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['gdd'] = self.get_gdd()
        return context


class GDDSupplyItemListCreateView(GDDSupplyItemMixin, ListCreateAPIView):
    def get_serializer(self, *args, **kwargs):
        if kwargs.get("data"):
            kwargs["data"]["gdd"] = self.get_gdd()
        return super().get_serializer(*args, **kwargs)


class GDDSupplyItemRetrieveUpdateView(GDDSupplyItemMixin, RetrieveUpdateDestroyAPIView):
    """View for retrieve/update/destroy of gdd Supply Item"""


class GDDSupplyItemUploadView(GDDMixin, APIView):
    serializer_class = GDDSupplyItemUploadSerializer

    def post(self, request, *args, **kwargs):
        gdd = self.get_gdd_or_404(self.kwargs.get("gdd_pk"))
        serializer = GDDSupplyItemUploadSerializer(data=request.data)
        # validate csv uploaded file
        if not serializer.is_valid():
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

        # processing of file not in validator as we want to extra the data
        # and use in later process
        try:
            file_data = serializer.extract_file_data()
        except ValidationError as err:
            return Response(
                {"supply_items_file": err.detail},
                status.HTTP_400_BAD_REQUEST,
            )
        if not file_data:
            return Response(
                {"supply_items_file": _("No valid data found in the file.")},
                status.HTTP_400_BAD_REQUEST,
            )

        # update all supply items related to gdd
        for title, unit_number, unit_price, product_number in file_data:
            # check if supply item exists
            supply_qs = GDDSupplyItem.objects.filter(
                gdd=gdd,
                title=title,
                unit_price=unit_price,
                provided_by=GDDSupplyItem.PROVIDED_BY_UNICEF,
            )
            if supply_qs.exists():
                item = supply_qs.get()
                item.unit_number += unit_number
                item.save()
            else:
                try:
                    GDDSupplyItem.objects.create(
                        gdd=gdd,
                        title=title,
                        unit_number=unit_number,
                        unit_price=unit_price,
                        unicef_product_number=product_number,
                        provided_by=GDDSupplyItem.PROVIDED_BY_UNICEF,
                    )
                except utils.DataError as err:
                    return Response(
                        {"supply_items_file": f"{product_number}:  {str(err)}"},
                        status.HTTP_400_BAD_REQUEST,
                    )
        # make sure we get the correct totals
        gdd.refresh_from_db()
        return Response(
            GDDDetailSerializer(
                gdd,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class GDDRiskDeleteView(FullGDDSnapshotDeleteMixin, DestroyAPIView):
    queryset = GDDRisk.objects
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & gdd_field_is_editable_permission('risks'))
    ]

    @functools.cache
    def get_root_object(self):
        return GDD.objects.filter(pk=self.kwargs.get('gdd_pk')).first()

    def get_gdd(self):
        return self.get_root_object()

    def get_queryset(self):
        return super().get_queryset().filter(gdd=self.get_root_object())


class GDDReportingRequirementView(GDDMixin, APIView):
    serializer_create_class = GDDReportingRequirementCreateSerializer
    serializer_list_class = GDDReportingRequirementListSerializer
    permission_classes = (PartnershipManagerPermission, )
    renderer_classes = (JSONRenderer, )

    def get_data(self):
        return {
            "reporting_requirements": GDDReportingRequirement.objects.filter(
                gdd=self.gdd,
                report_type=self.report_type,
            ).all()
        }

    def get_object(self, pk):
        return get_object_or_404(GDD, pk=pk)

    def get(self, request, gdd_pk, report_type, format=None):
        self.gdd = self.get_object(gdd_pk)
        self.report_type = report_type
        return Response(
            self.serializer_list_class(self.get_data()).data
        )

    def post(self, request, gdd_pk, report_type, format=None):
        self.gdd = self.get_object(gdd_pk)
        self.report_type = report_type
        self.request.data["report_type"] = self.report_type
        # TODO: [e4] remove this whenever a better validation is decided on. This is out of place but needed as a hotfix
        # take into consideration the reporting requirements edit rights on the gdd
        # move this into permissions when time allows

        ps = GDD.permission_structure()
        gdd_permissions = GDDPermissions(
            user=request.user, instance=self.gdd, permission_structure=ps
        ).get_permissions()

        serializer = self.serializer_create_class(
            data=self.request.data,
            context={
                "user": request.user,
                "gdd": self.gdd,
                "gdd_permissions": gdd_permissions
            }
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                self.serializer_list_class(self.get_data()).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GDDSpecialReportingRequirementListCreateView(ListCreateAPIView):
    serializer_class = GDDSpecialReportingRequirementSerializer
    permission_classes = (PartnershipManagerPermission, )
    renderer_classes = (JSONRenderer, )
    queryset = GDDSpecialReportingRequirement.objects.all()

    def create(self, request, *args, **kwargs):
        request.data["gdd"] = kwargs.get('gdd_pk', None)
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return GDDSpecialReportingRequirement.objects.filter(gdd=self.kwargs.get("gdd_pk"))


class GDDSpecialReportingRequirementUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    serializer_class = GDDSpecialReportingRequirementSerializer
    permission_classes = (PartnershipManagerPermission,)
    renderer_classes = (JSONRenderer,)
    queryset = GDDSpecialReportingRequirement.objects.all()

    def destroy(self, request, *args, **kwargs):
        if self.get_object().due_date < datetime.date.today():
            raise ValidationError(
                _("Cannot delete special reporting requirements in the past.")
            )
        return super().destroy(request, *args, **kwargs)


class GDDAutoTransitionsMixin:
    @staticmethod
    def perform_auto_transitions(gdd, user):
        validator = GDDValid(gdd, old=gdd, user=user, disable_rigid_check=True)
        validator.total_validation


class GDDAttachmentListCreateView(GDDAutoTransitionsMixin, DetailedGDDResponseMixin, ListCreateAPIView):
    serializer_class = GDDAttachmentSerializer
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & gdd_field_is_editable_permission('attachments')),
    ]
    queryset = GDDAttachment.objects.all()

    def get_root_object(self):
        if not hasattr(self, '_gdd'):
            self._gdd = GDD.objects.filter(pk=self.kwargs.get('gdd_pk')).first()
        return self._gdd

    def get_queryset(self):
        return super().get_queryset().filter(gdd=self.get_root_object())

    @transaction.atomic
    def perform_create(self, serializer):
        gdd = self.get_root_object()
        serializer.save(gdd=gdd)
        self.perform_auto_transitions(gdd, self.request.user)

    def get_gdd(self):
        return self.get_root_object()


class GDDAttachmentUpdateDeleteView(GDDAutoTransitionsMixin, DetailedGDDResponseMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = GDDAttachmentSerializer
    queryset = GDDAttachment.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & gdd_field_is_editable_permission('attachments')),
    ]

    def get_root_object(self):
        if not hasattr(self, '_gdd'):
            self._gdd = GDD.objects.filter(pk=self.kwargs.get('gdd_pk')).first()
        return self._gdd

    def get_queryset(self):
        return super().get_queryset().filter(gdd=self.get_root_object())

    def get_gdd(self):
        return self.get_root_object()

    @transaction.atomic
    def perform_update(self, serializer):
        super().perform_update(serializer)
        self.perform_auto_transitions(self.get_root_object(), self.request.user)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()

        if obj.gdd.status != GDD.DRAFT:
            raise ValidationError(_("Deleting an attachment can only be done in Draft status"))
        return super().delete(request, *args, **kwargs)


class GDDFRsView(APIView):
    """
    Returns the FRs requested with the values query param,
    The get endpoint in this view is meant to validate / validate and
    import FRs in order to be able to associate them with gdds.
    """
    permission_classes = (IsAdminUser,)

    def get(self, request, format=None):
        values = request.query_params.get("values", '').split(",")

        if not values[0]:
            return self.bad_request('Values are required')

        if len(values) > len(set(values)):
            return self.bad_request('You have duplicate records of the same FR, please make sure to add'
                                    ' each FR only one time')
        qs = FundsReservationHeader.objects.filter(fr_number__in=values)
        not_found = set(values) - set(qs.values_list('fr_number', flat=True))
        if not_found:
            nf = list(not_found)
            nf.sort()
            with transaction.atomic():
                for delegated_fr in nf:
                    # try to get this FR from vision
                    try:
                        sync_single_delegated_fr(request.user.profile.country.business_area_code, delegated_fr)
                    except VisionException as e:
                        return self.bad_request('The FR {} could not be found in eTools and could not be synced '
                                                'from Vision. {}'.format(delegated_fr, e))

            qs._result_cache = None
        gdd_id = request.query_params.get("gdd", None)
        if gdd_id:
            qs = qs.filter(Q(gdd_id=gdd_id) | Q(gdd__isnull=True) & Q(intervention__isnull=True))
            not_found = set(values) - set(qs.values_list('fr_number', flat=True))
            if not_found:
                frs_not_found = FundsReservationHeader.objects.filter(fr_number__in=not_found)
                errors = [f'FR #{0} is already being used by Document ref '
                          f'[{fr.intervention if fr.intervention else fr.gdd}]' for fr in frs_not_found]
                return self.bad_request(', '.join(errors))
        else:
            qs = qs.filter(gdd_id__isnull=True, intervention__isnull=True)

        if qs.count() != len(values):
            return self.bad_request('One or more of the FRs are already used or could not be found in eTools.')

        all_frs_vendor_numbers = [fr.vendor_code for fr in qs.all()]
        if len(set(all_frs_vendor_numbers)) != 1:
            return self.bad_request('The FRs selected relate to various partners, please make sure to select '
                                    'FRs that relate to the PD/SPD Partner')

        if gdd_id is not None:
            try:
                gdd = GDD.objects.get(pk=gdd_id)
            except GDD.DoesNotExist:
                return self.bad_request('Digital Document could not be found')
            else:
                if gdd.partner.vendor_number != all_frs_vendor_numbers[0]:
                    return self.bad_request('The vendor number of the selected implementing partner in eTools '
                                            'does not match the vendor number entered in the FR in VISION. '
                                            'Please correct the vendor number to continue.')

        serializer = FRsSerializer(qs)

        return Response(serializer.data)

    def bad_request(self, error_message):
        return Response(data={'error': _(error_message)}, status=status.HTTP_400_BAD_REQUEST)


class GDDAmendmentListAPIView(ExportModelMixin, ValidatorViewMixin, ListCreateAPIView):
    """
    Returns a list of InterventionAmendments.
    """
    serializer_class = GDDAmendmentCUSerializer
    permission_classes = (PartnershipManagerPermission, UserIsNotPartnerStaffMemberPermission)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )

    def get_serializer_class(self):
        """
        Use different serializers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return GDDAmendmentExportSerializer
            if query_params.get("format") == 'csv_flat':
                return GDDAmendmentExportFlatSerializer
        return super().get_serializer_class()

    def get_queryset(self, format=None):
        q = GDDAmendment.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(intervention__number__icontains=query_params.get("search")) |
                    Q(amendment_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
        return q

    def create(self, request, *args, **kwargs):
        raw_data = request.data.copy()
        raw_data['gdd'] = kwargs.get('gdd_pk', None)
        serializer = self.get_serializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        if tenant_switch_is_active('gdd_amendment_notifications_on'):
            send_gdd_amendment_added_notification.delay(connection.schema_name, serializer.instance.gdd)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class GDDAmendmentDeleteView(FullGDDSnapshotDeleteMixin, DestroyAPIView):
    permission_classes = (
        IsAuthenticated,
        GDDAmendmentIsNotCompleted,
        UserIsUnicefFocalPoint | IsGDDBudgetOwnerPermission,
    )
    queryset = GDDAmendment.objects.all()

    def get_gdd(self):
        return self.get_root_object()

    @functools.cache
    def get_root_object(self):
        return get_object_or_404(GDD.objects, amendments=self.kwargs.get('pk'))
