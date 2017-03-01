from __future__ import unicode_literals

from decimal import Decimal

from django.conf import settings
from django.db.transaction import atomic

from rest_framework import generics, viewsets, mixins, status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from rest_framework_csv import renderers

from publics.models import TravelExpenseType
from t2f.filters import TravelRelatedModelFilter, TravelActivityPartnerFilter
from t2f.filters import travel_list, action_points
from t2f.serializers.export import TravelListExportSerializer, FinanceExportSerializer, TravelAdminExportSerializer, \
    InvoiceExportSerializer

from t2f.models import Travel, TravelAttachment, ActionPoint, IteneraryItem, InvoiceItem, TravelActivity
from t2f.serializers.travel import TravelListSerializer, TravelDetailsSerializer, TravelAttachmentSerializer, \
    CloneParameterSerializer, CloneOutputSerializer, ActionPointSerializer, TravelActivityByPartnerSerializer
from t2f.helpers.permission_matrix import PermissionMatrix, FakePermissionMatrix
from t2f.helpers.clone_travel import CloneTravelHelper
from t2f.views import T2FPagePagination, run_transition


class TravelListViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelListSerializer
    pagination_class = T2FPagePagination
    permission_classes = (IsAdminUser,)
    filter_backends = (travel_list.TravelSearchFilter,
                       travel_list.ShowHiddenFilter,
                       travel_list.TravelSortFilter,
                       travel_list.TravelFilterBoxFilter)
    renderer_classes = (renderers.JSONRenderer, renderers.CSVRenderer)

    _transition_name_mapping = {'save_and_submit': 'submit_for_approval'}

    @atomic
    def create(self, request, *args, **kwargs):
        if 'transition_name' in kwargs:
            transition_name = kwargs['transition_name']
            request.data['transition_name'] = self._transition_name_mapping.get(transition_name, transition_name)

        serializer = TravelDetailsSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        super(TravelListViewSet, self).perform_create(serializer)
        run_transition(serializer)

    def export(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serialzier = TravelListExportSerializer(queryset, many=True, context=self.get_serializer_context())

        response = Response(data=serialzier.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="TravelListExport.csv"'
        return response

    def export_finances(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serialzier = FinanceExportSerializer(queryset, many=True, context=self.get_serializer_context())

        response = Response(data=serialzier.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="TravelListExport.csv"'
        return response

    def export_travel_admins(self, request, *args, **kwargs):
        travel_queryset = self.filter_queryset(self.get_queryset())
        queryset = IteneraryItem.objects.filter(travel__in=travel_queryset).order_by('travel__reference_number')
        queryset = queryset.prefetch_related('airlines')
        serialzier = TravelAdminExportSerializer(queryset, many=True, context=self.get_serializer_context())

        response = Response(data=serialzier.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="TravelListExport.csv"'
        return response

    def export_invoices(self, request, *args, **kwargs):
        travel_queryset = self.filter_queryset(self.get_queryset())
        queryset = InvoiceItem.objects.filter(invoice__travel__in=travel_queryset).order_by('invoice__travel__reference_number')
        serialzier = InvoiceExportSerializer(queryset, many=True, context=self.get_serializer_context())

        response = Response(data=serialzier.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="TravelListExport.csv"'
        return response


class TravelDetailsViewSet(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelDetailsSerializer
    pagination_class = PageNumberPagination
    permission_classes = (IsAdminUser,)
    lookup_url_kwarg = 'travel_pk'

    def get_serializer_context(self):
        context = super(TravelDetailsViewSet, self).get_serializer_context()

        # This will prevent Swagger error because it will not populate self.kwargs with the required arguments to fetch
        # the object.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg in self.kwargs:
            obj = self.get_object()
            context['permission_matrix'] = PermissionMatrix(obj, self.request.user)
        else:
            context['permission_matrix'] = FakePermissionMatrix(self.request.user)

        return context

    @atomic
    def partial_update(self, request, *args, **kwargs):
        if 'transition_name' in kwargs:
            request.data['transition_name'] = kwargs['transition_name']
        return super(TravelDetailsViewSet, self).partial_update(request, *args, **kwargs)

    @atomic
    def perform_update(self, serializer):
        super(TravelDetailsViewSet, self).perform_update(serializer)

        # If invoicing is enabled, do the treshold check, otherwise it will result an infinite process loop
        if not settings.DISABLE_INVOICING and serializer.transition_name == 'send_for_payment' \
                and self.check_treshold(serializer.instance):
            serializer.transition_name = 'submit_for_approval'

        run_transition(serializer)

        # If invoicing is turned off, jump to sent_for_payment when someone approves the travel
        if serializer.transition_name == 'approve' and settings.DISABLE_INVOICING:
            serializer.transition_name = 'send_for_payment'
            run_transition(serializer)

    def check_treshold(self, travel):
        expenses = {'user': Decimal(0),
                    'travel_agent': Decimal(0)}

        for expense in travel.expenses.all():
            if expense.type.vendor_number == TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER:
                expenses['user'] += expense.amount
            elif expense.type.vendor_number:
                expenses['travel_agent'] += expense.amount

        traveler_delta = 0
        travel_agent_delta = 0
        if travel.approved_cost_traveler:
            traveler_delta = expenses['user'] - travel.approved_cost_traveler
            if travel.currency.code != 'USD':
                exchange_rate = travel.currency.exchange_rates.all().last()
                traveler_delta *= exchange_rate.x_rate

        if travel.approved_cost_travel_agencies:
            travel_agent_delta = expenses['travel_agent'] - travel.approved_cost_travel_agencies

        workspace = self.request.user.profile.country
        if workspace.threshold_tre_usd and traveler_delta > workspace.threshold_tre_usd:
            return True

        if workspace.threshold_tae_usd and travel_agent_delta > workspace.threshold_tae_usd:
            return True

        return False

    @atomic
    def clone_for_secondary_traveler(self, request, *args, **kwargs):
        traveler = self._get_traveler_for_cloning()
        helper = CloneTravelHelper(self.get_object())
        clone = helper.clone_for_secondary_traveler(traveler)
        serializer = CloneOutputSerializer(clone, context=self.get_serializer_context())
        return Response(serializer.data, status.HTTP_201_CREATED)

    @atomic
    def clone_for_driver(self, request, *args, **kwargs):
        traveler = self._get_traveler_for_cloning()
        helper = CloneTravelHelper(self.get_object())
        clone = helper.clone_for_driver(traveler)
        serializer = CloneOutputSerializer(clone, context=self.get_serializer_context())
        return Response(serializer.data, status.HTTP_201_CREATED)

    def _get_traveler_for_cloning(self):
        parameter_serializer = CloneParameterSerializer(data=self.request.data)
        parameter_serializer.is_valid(raise_exception=True)
        traveler = parameter_serializer.validated_data['traveler']
        return traveler


class TravelAttachmentViewSet(mixins.ListModelMixin,
                              mixins.CreateModelMixin,
                              mixins.DestroyModelMixin,
                              viewsets.GenericViewSet):
    queryset = TravelAttachment.objects.all()
    serializer_class = TravelAttachmentSerializer
    parser_classes = (FormParser, MultiPartParser, FileUploadParser)
    permission_classes = (IsAdminUser,)
    filter_backends = (TravelRelatedModelFilter,)
    lookup_url_kwarg = 'attachment_pk'

    def get_serializer_context(self):
        context = super(TravelAttachmentViewSet, self).get_serializer_context()
        # TODO: figure out a better solution for this:
        # Hack to prevent swagger from crashing
        if 'travel_pk' not in self.kwargs:
            return context
        # TODO filter out the travels which cannot be edited (permission check)
        queryset = Travel.objects.all()
        travel = get_object_or_404(queryset, pk=self.kwargs['travel_pk'])
        context['travel'] = travel
        return context


class TravelActivityViewSet(mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = TravelActivity.objects.all()
    permission_classes = (IsAdminUser,)
    serializer_class = TravelActivityByPartnerSerializer
    filter_backends = (TravelActivityPartnerFilter,)
    lookup_url_kwarg = 'partner_organization_pk'


class ActionPointViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         viewsets.GenericViewSet):
    queryset = ActionPoint.objects.all()
    serializer_class = ActionPointSerializer
    pagination_class = T2FPagePagination
    permission_classes = (IsAdminUser,)
    filter_backends = (action_points.ActionPointSearchFilter,
                       action_points.ActionPointSortFilter,
                       action_points.ActionPointFilterBoxFilter)
    lookup_url_kwarg = 'action_point_pk'
