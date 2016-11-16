from __future__ import unicode_literals

from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.db.models.query_utils import Q
from django.http.response import HttpResponse

from rest_framework import generics, viewsets, mixins, status
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination as _PageNumberPagination
from rest_framework.response import Response

from funds.models import Grant
from locations.models import Location
from partners.models import PartnerOrganization, PCA
from reports.models import Result, ResultType
from users.models import Office, Section

from et2f import TripStatus
from et2f.exports import TravelListExporter
from et2f.models import Travel, Currency, AirlineCompany, DSARegion, TravelPermission, Fund, ExpenseType
from et2f.serializers import TravelListSerializer, TravelDetailsSerializer, TravelListParameterSerializer, \
    CurrentUserSerializer
from et2f.serializers.static_data import StaticDataSerializer
from et2f.serializers.permission_matrix import PermissionMatrixSerializer
from et2f.helpers import PermissionMatrix


class PageNumberPagination(_PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

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
        transition()
        instance.save()


class TravelListViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelListSerializer
    pagination_class = PageNumberPagination
    permission_classes = (IsAdminUser,)

    _search_fields = ('id', 'reference_number', 'traveller__first_name', 'traveller__last_name', 'purpose',
                      'section__name', 'office__name', 'supervisor__first_name', 'supervisor__last_name')

    _transition_name_mapping = {'save_and_submit': 'submit_for_approval'}

    def get_queryset(self):
        queryset = super(TravelListViewSet, self).get_queryset()
        parameter_serializer = TravelListParameterSerializer(data=self.request.GET)
        if not parameter_serializer.is_valid():
            return queryset

        # Searching
        search_str = parameter_serializer.data['search']
        if search_str:
            q = Q()
            for field_name in self._search_fields:
                constructed_field_name = '{}__iexact'.format(field_name)
                q |= Q(**{constructed_field_name: search_str})
            queryset = queryset.filter(q)

        # Hide hidden travels
        show_hidden = parameter_serializer.data['show_hidden']
        if not show_hidden:
            q = Q(hidden=True) | Q(status=TripStatus.CANCELLED)
            queryset = queryset.exclude(q)

        # Sorting
        prefix = '-' if parameter_serializer.data['reverse'] else ''
        sort_by = '{}{}'.format(prefix, parameter_serializer.data['sort_by'])
        return queryset.order_by(sort_by)

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

    def get_serializer_context(self):
        context = super(TravelDetailsViewSet, self).get_serializer_context()

        obj = self.get_object()
        context['permission_matrix'] = PermissionMatrix(obj, self.request.user)

        return context

    def partial_update(self, request, *args, **kwargs):
        if 'transition_name' in kwargs:
            request.data['transition_name'] = kwargs['transition_name']
        return super(TravelDetailsViewSet, self).partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        super(TravelDetailsViewSet, self).perform_update(serializer)
        run_transition(serializer)


class StaticDataView(generics.GenericAPIView):
    serializer_class = StaticDataSerializer

    def get(self, request):
        User = get_user_model()

        wbs_qs = Result.objects.filter(result_type__name=ResultType.ACTIVITY, hidden=False)

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
                'wbs': wbs_qs,
                'grants': Grant.objects.all(),
                'funds': Fund.objects.all(),
                'expense_types': ExpenseType.objects.all()}

        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)


class PermissionMatrixView(generics.GenericAPIView):
    serializer_class = PermissionMatrixSerializer

    def get(self, request):
        permissions = TravelPermission.objects.all()
        serializer = self.get_serializer(permissions)
        return Response(serializer.data, status.HTTP_200_OK)


class CurrentUserView(generics.GenericAPIView):
    serializer_class = CurrentUserSerializer

    def get(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status.HTTP_200_OK)