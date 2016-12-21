from __future__ import unicode_literals

from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http.response import HttpResponse
from django_fsm import TransitionNotAllowed

from rest_framework import generics, viewsets, mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from t2f.filters import SearchFilter, ShowHiddenFilter, SortFilter, FilterBoxFilter, TravelAttachmentFilter
from locations.models import Location
from partners.models import PartnerOrganization, PCA
from reports.models import Result
from users.models import Office, Section

from t2f.exports import TravelListExporter
from t2f.models import Travel, Currency, AirlineCompany, DSARegion, TravelPermission, Fund, ExpenseType, WBS, Grant, \
    TravelAttachment, TravelType, ModeOfTravel
from t2f.serializers import TravelListSerializer, TravelDetailsSerializer, TravelAttachmentSerializer, \
    CloneParameterSerializer, CloneOutputSerializer
from t2f.serializers.static_data import StaticDataSerializer
from t2f.serializers.permission_matrix import PermissionMatrixSerializer
from t2f.helpers import PermissionMatrix, CloneTravelHelper


class TravelPagePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('page_count', self.page.paginator.num_pages),
            ('data', data),
            ('total_count', self.page.paginator.object_list.count()),
        ]))


def run_transition(serializer):
    transition_name = serializer.transition_name
    if transition_name:
        instance = serializer.instance
        transition = getattr(instance, transition_name)
        try:
            transition()
        except TransitionNotAllowed as exc:
            raise ValidationError(exc.message)
        instance.save()


class TravelListViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelListSerializer
    pagination_class = TravelPagePagination
    permission_classes = (IsAdminUser,)
    filter_backends = (SearchFilter, ShowHiddenFilter, SortFilter, FilterBoxFilter)

    _transition_name_mapping = {'save_and_submit': 'submit_for_approval'}

    def create(self, request, *args, **kwargs):
        if 'transition_name' in kwargs:
            transition_name = kwargs['transition_name']
            request.data['transition_name'] = self._transition_name_mapping.get(transition_name, transition_name)

        serializer = TravelDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        super(TravelListViewSet, self).perform_create(serializer)
        run_transition(serializer)

    def export(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        dataset = TravelListExporter().export(queryset)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ModelExportPartners.csv"'
        response.write(dataset.csv)

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

        # TODO simon: this is a dirty fix. Swagger fails because it will not populate self.kwargs with the required
        # arguments to fetch the object. Would be lovely to find a nicer solution.
        try:
            obj = self.get_object()
            context['permission_matrix'] = PermissionMatrix(obj, self.request.user)
        except AssertionError:
            pass

        return context

    def partial_update(self, request, *args, **kwargs):
        if 'transition_name' in kwargs:
            request.data['transition_name'] = kwargs['transition_name']
        return super(TravelDetailsViewSet, self).partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        super(TravelDetailsViewSet, self).perform_update(serializer)
        run_transition(serializer)

    def clone_for_secondary_traveler(self, request, *args, **kwargs):
        traveler = self._get_traveler_for_cloning()
        helper = CloneTravelHelper(self.get_object())
        clone = helper.clone_for_secondary_traveler(traveler)
        serializer = CloneOutputSerializer(clone, context=self.get_serializer_context())
        return Response(serializer.data, status.HTTP_201_CREATED)

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
    filter_backends = (TravelAttachmentFilter,)
    lookup_url_kwarg = 'attachment_pk'

    def get_serializer_context(self):
        context = super(TravelAttachmentViewSet, self).get_serializer_context()
        # TODO filter out the travels which cannot be edited (permission check)
        queryset = Travel.objects.all()
        travel = get_object_or_404(queryset, pk=self.kwargs['travel_pk'])
        context['travel'] = travel
        return context


class StaticDataView(generics.GenericAPIView):
    serializer_class = StaticDataSerializer

    def get(self, request):
        User = get_user_model()
        # TODO: this is not only static data some of the data changes,
        # there should be calls to individual endpoints for:
        # users, partners, partnerships, results, locations, wbs, grants, funds
        data = {'users': User.objects.exclude(first_name='', last_name=''),
                'currencies': Currency.objects.all(),
                'airlines': AirlineCompany.objects.all(),
                'offices': Office.objects.all(),
                'sections': Section.objects.all(),
                'partners': PartnerOrganization.objects.all(),
                'partnerships': PCA.objects.all(),
                'results': Result.objects.all(),
                'locations': Location.objects.all(),
                'dsa_regions': DSARegion.objects.all(),
                'wbs': WBS.objects.all(),
                'grants': Grant.objects.all(),
                'funds': Fund.objects.all(),
                'expense_types': ExpenseType.objects.all(),
                'travel_types': TravelType.objects.all(),
                'travel_modes': ModeOfTravel.objects.all()}

        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)


class PermissionMatrixView(generics.GenericAPIView):
    serializer_class = PermissionMatrixSerializer
    cache_timeout = None

    def get(self, request):
        permission_matrix_data = cache.get('permssion_matrix_data')
        if not permission_matrix_data:
            permissions = TravelPermission.objects.all()
            serializer = self.get_serializer(permissions)
            permission_matrix_data = serializer.data
            cache.set('permssion_matrix_data', permission_matrix_data, self.cache_timeout)
        return Response(permission_matrix_data, status.HTTP_200_OK)
