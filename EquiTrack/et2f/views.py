from __future__ import unicode_literals

from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.db.models.query_utils import Q
from django.http.response import HttpResponse, Http404
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import list_route, detail_route
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


def state_transition(transition_name):
    @detail_route(methods=['post', 'put', 'patch'])
    def func(self, request, *args, **kwargs):
        kwargs['transition_name'] = transition_name
        return self.update(request, *args, **kwargs)
    func.__name__ = str(transition_name)
    return func


class TravelViewSet(mixins.ListModelMixin,
                    mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelDetailsSerializer
    pagination_class = PageNumberPagination
    permission_classes = (IsAdminUser,)

    _search_fields = ('id', 'reference_number', 'traveller__first_name', 'traveller__last_name', 'purpose',
                      'section__name', 'office__name', 'supervisor__first_name', 'supervisor__last_name')

    def get_serializer_context(self):
        context = super(TravelViewSet, self).get_serializer_context()
        try:
            obj = self.get_object()
            context['permission_matrix'] = PermissionMatrix(obj, self.request.user)
        except AssertionError:
            pass

        return context

    def get_queryset(self):
        queryset = super(TravelViewSet, self).get_queryset()
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        serializer = TravelListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        transition_name = kwargs.pop('transition_name', None)
        
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer, transition_name)
        
        return Response(serializer.data)
    
    def perform_update(self, serializer, transition_name=None):
        super(TravelViewSet, self).perform_update(serializer)

        instance = serializer.instance
        if transition_name:
            transition = getattr(instance, transition_name)
            transition()
            instance.save()

    @list_route(methods=['get'])
    def export(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        dataset = TravelListExporter().export(queryset)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ModelExportPartners.csv"'
        response.write(dataset.csv)

        return response

    # State changes
    submit_for_approval = state_transition('submit_for_approval')
    approve = state_transition('approve')
    reject = state_transition('reject')
    cancel = state_transition('cancel')
    restore = state_transition('restore')
    send_for_payment = state_transition('send_for_payment')
    mark_as_done = state_transition('mark_as_done')
    submit_certificate = state_transition('submit_certificate')
    approve_cetificate = state_transition('approve_cetificate')
    reject_certificate = state_transition('reject_certificate')
    mark_as_certified = state_transition('submit_for_approval')
    mark_as_completed = state_transition('mark_as_completed')


class StaticDataViewSet(mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = StaticDataSerializer

    def list(self, request, *args, **kwargs):
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


class PermissionMatrixViewSet(mixins.ListModelMixin,
                              viewsets.GenericViewSet):
    serializer_class = PermissionMatrixSerializer

    def list(self, request, *args, **kwargs):
        permissions = TravelPermission.objects.all()
        serializer = self.get_serializer(permissions)
        return Response(serializer.data, status.HTTP_200_OK)


class CurrentUserViewSet(mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = CurrentUserSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status.HTTP_200_OK)