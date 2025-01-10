import functools
import operator

from django.db.models import Case, CharField, F, When
from django.db.transaction import atomic

from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FileUploadParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_csv import renderers
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.t2f.filters import (
    travel_list,
    TravelActivityInterventionFilter,
    TravelActivityPartnerFilter,
    TravelRelatedModelFilter,
)
from etools.applications.t2f.helpers.clone_travel import CloneTravelHelper
from etools.applications.t2f.helpers.permission_matrix import FakePermissionMatrix, PermissionMatrix
from etools.applications.t2f.models import Travel, TravelActivity, TravelAttachment, TravelType
from etools.applications.t2f.serializers.travel import (
    CloneOutputSerializer,
    CloneParameterSerializer,
    TravelActivityByPartnerSerializer,
    TravelAttachmentSerializer,
    TravelDetailsSerializer,
    TravelListSerializer,
)
from etools.applications.t2f.views import run_transition, T2FPagePagination


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

    _transition_name_mapping = {'save_and_submit': Travel.SUBMIT_FOR_APPROVAL}

    @atomic
    def create(self, request, *args, **kwargs):
        raise ValidationError('Creation is not allowed')
        # if 'transition_name' in kwargs:
        #     transition_name = kwargs['transition_name']
        #     request.data['transition_name'] = self._transition_name_mapping.get(transition_name, transition_name)
        #
        # serializer = TravelDetailsSerializer(data=request.data, context=self.get_serializer_context())
        # serializer.is_valid(raise_exception=True)
        # self.perform_create(serializer)
        # headers = self.get_success_headers(serializer.data)
        # return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # def perform_create(self, serializer):
    #     super().perform_create(serializer)
    #     run_transition(serializer)


class TravelDetailsViewSet(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelDetailsSerializer
    pagination_class = PageNumberPagination
    permission_classes = (IsAdminUser,)
    lookup_url_kwarg = 'travel_pk'

    def get_serializer_context(self):
        context = super().get_serializer_context()

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
        return super().partial_update(request, *args, **kwargs)

    @atomic
    def perform_update(self, serializer):
        super().perform_update(serializer)
        run_transition(serializer)

    @atomic
    def clone_for_secondary_traveler(self, request, *args, **kwargs):
        traveler = self._get_traveler_for_cloning()
        helper = CloneTravelHelper(self.get_object())
        clone = helper.clone_for_secondary_traveler(traveler)
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
        context = super().get_serializer_context()
        # TODO: figure out a better solution for this:
        # Hack to prevent swagger from crashing
        if 'travel_pk' not in self.kwargs:
            return context
        # TODO filter out the travels which cannot be edited (permission check)
        queryset = Travel.objects.all()
        travel = get_object_or_404(queryset, pk=self.kwargs['travel_pk'])
        context['travel'] = travel
        return context


class TravelActivityViewSet(QueryStringFilterMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAdminUser,)
    serializer_class = TravelActivityByPartnerSerializer
    filter_backends = (TravelActivityPartnerFilter,)
    lookup_url_kwarg = 'partner_organization_pk'
    filters = (
        ('year', 'travels__end_date__year'),
        ('status', 'travels__status'),
        ('travel_type', 'travel_type__in'),
    )

    def get_queryset(self):
        qs = TravelActivity.objects.prefetch_related('travels', 'primary_traveler', 'locations')

        query_params = self.request.query_params
        if query_params:
            queries = []
            queries.extend(self.filter_params())
            if queries:
                expression = functools.reduce(operator.and_, queries)
                qs = qs.filter(expression)

        qs = qs.annotate(status=Case(When(travels__traveler=F('primary_traveler'),
                                          then=F('travels__status')), output_field=CharField()))\
            .annotate(reference_number=Case(When(travels__traveler=F('primary_traveler'),
                                                 then=F('travels__reference_number')), output_field=CharField()))\
            .annotate(trip_id=Case(When(travels__traveler=F('primary_traveler'),
                                        then=F('travels__id')), output_field=CharField()))\
            .distinct('id')
        qs = qs.exclude(status__in=[Travel.CANCELLED, Travel.REJECTED, Travel.PLANNED])

        qs = qs.filter(travel_type__in=[TravelType.SPOT_CHECK, TravelType.PROGRAMME_MONITORING])
        return qs


class TravelActivityPerInterventionViewSet(QueryStringFilterMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAdminUser,)
    serializer_class = TravelActivityByPartnerSerializer
    filter_backends = (TravelActivityInterventionFilter,)
    lookup_url_kwarg = 'partnership_pk'

    filters = (
        ('year', 'travels__end_date__year'),
    )

    def get_queryset(self):
        qs = TravelActivity.objects.prefetch_related('travels', 'primary_traveler', 'locations')

        query_params = self.request.query_params
        if query_params:
            queries = []
            queries.extend(self.filter_params())
            if queries:
                expression = functools.reduce(operator.and_, queries)
                qs = qs.filter(expression)

        qs = qs.annotate(status=Case(When(travels__traveler=F('primary_traveler'),
                                          then=F('travels__status')), output_field=CharField()))\
            .annotate(reference_number=Case(When(travels__traveler=F('primary_traveler'),
                                                 then=F('travels__reference_number')), output_field=CharField()))\
            .annotate(trip_id=Case(When(travels__traveler=F('primary_traveler'),
                                        then=F('travels__id')), output_field=CharField()))\
            .distinct('id')
        qs = qs.exclude(status__in=[Travel.CANCELLED, Travel.REJECTED, Travel.PLANNED])
        return qs
