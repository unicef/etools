from django.db.models.query_utils import Q

from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from etools.applications.publics.models import (
    AirlineCompany,
    BusinessArea,
    Country,
    Currency,
    DSARegion,
    TravelExpenseType,
)
from etools.applications.publics.serializers import (
    AirlineSerializer,
    BusinessAreaSerializer,
    CountrySerializer,
    CurrencySerializer,
    DSARegionSerializer,
    DSARegionsParameterSerializer,
    ExpenseTypeSerializer,
    GhostDataPKSerializer,
    MultiGhostDataSerializer,
    PublicStaticDataSerializer,
)
from etools.applications.t2f.models import ModeOfTravel, TravelType


class GhostDataMixin(object):
    def missing(self, request):
        parameter_serializer = GhostDataPKSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset()
        model = queryset.model

        obj = model.admin_objects.filter(id__in=parameter_serializer.data['values'])
        serializer = self.get_serializer(obj, many=True)
        return Response(serializer.data, status.HTTP_200_OK)


class CountryViewSet(mixins.ListModelMixin,
                     GhostDataMixin,
                     viewsets.GenericViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (IsAdminUser,)


class StaticDataView(GhostDataMixin,
                     viewsets.GenericViewSet):
    serializer_class = PublicStaticDataSerializer

    def list(self, request):
        country = request.user.profile.country
        currencies = Currency.objects.all().prefetch_related('exchange_rates')
        business_areas = BusinessArea.objects.all().select_related('region')

        expense_type_q = Q(travel_agent__isnull=True)
        expense_type_q |= Q(travel_agent__country__business_area__code=country.business_area_code)
        expense_types = TravelExpenseType.objects.select_related('travel_agent').filter(expense_type_q)

        data = {'currencies': currencies,  # Moved
                'business_areas': business_areas,  # Moved
                'expense_types': expense_types,  # Moved

                # These should stay here since all of them are 'static'
                'airlines': self.get_airlines_queryset(),
                'countries': self.get_country_queryset(),
                'travel_types': [c[0].lower() for c in TravelType.CHOICES],
                'travel_modes': [c[0].lower() for c in ModeOfTravel.CHOICES]}

        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)

    def missing(self, request):
        context = {'allowed_categories': ['airlines', 'countries']}
        parameter_serializer = MultiGhostDataSerializer(data=request.GET, context=context)
        parameter_serializer.is_valid(raise_exception=True)

        category = parameter_serializer.data['category']

        if category == 'airlines':
            queryset = self.get_airlines_queryset()
            serializer_class = AirlineSerializer
        elif category == 'countries':
            queryset = self.get_country_queryset()
            serializer_class = CountrySerializer
        else:
            raise ValueError('Invalid category')

        model = queryset.model

        obj = model.admin_objects.filter(id__in=parameter_serializer.data['values'])
        serializer = serializer_class(obj, many=True, context=self.get_serializer_context())
        return Response(serializer.data, status.HTTP_200_OK)

    def get_airlines_queryset(self):
        return AirlineCompany.objects.all()

    def get_country_queryset(self):
        return Country.objects.all()


class DSARegionsView(GhostDataMixin,
                     viewsets.GenericViewSet):
    serializer_class = DSARegionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()

        parameter_serializer = DSARegionsParameterSerializer(data=self.request.GET)
        if parameter_serializer.is_valid():
            context['values_at'] = parameter_serializer.validated_data['values_at']

        return context

    def get_queryset(self):
        workspace = self.request.user.profile.country
        dsa_regions = DSARegion.objects.filter(country__business_area__code=workspace.business_area_code)

        parameter_serializer = DSARegionsParameterSerializer(data=self.request.GET)
        if parameter_serializer.is_valid():
            dsa_regions = dsa_regions.active_at(parameter_serializer.validated_data['values_at'])
        else:
            dsa_regions = dsa_regions.active()

        return dsa_regions.select_related('country')

    def list(self, request):
        dsa_regions = self.get_queryset()
        serializer = self.get_serializer(dsa_regions, many=True)
        return Response(serializer.data, status.HTTP_200_OK)


class BusinessAreasView(GhostDataMixin,
                        viewsets.GenericViewSet):
    serializer_class = BusinessAreaSerializer

    def list(self, request):
        business_areas = BusinessArea.objects.all().select_related('region')
        serializer = self.get_serializer(business_areas, many=True)
        return Response(serializer.data, status.HTTP_200_OK)


class CurrenciesView(GhostDataMixin,
                     viewsets.GenericViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer

    def list(self, request):
        currencies = self.get_queryset()
        serializer = self.get_serializer(currencies, many=True)
        return Response(serializer.data, status.HTTP_200_OK)


class ExpenseTypesView(GhostDataMixin,
                       viewsets.GenericViewSet):
    serializer_class = ExpenseTypeSerializer

    def get_queryset(self):
        workspace = self.request.user.profile.country
        expense_type_q = Q(travel_agent__isnull=True)
        expense_type_q |= Q(travel_agent__country__business_area__code=workspace.business_area_code)
        expense_types = TravelExpenseType.objects.select_related('travel_agent').filter(expense_type_q)
        return expense_types

    def list(self, request):
        expense_types = self.get_queryset()
        serializer = self.get_serializer(expense_types, many=True)
        return Response(serializer.data, status.HTTP_200_OK)


class AirlinesView(GhostDataMixin,
                   viewsets.GenericViewSet):
    queryset = AirlineCompany.objects.all()
    serializer_class = AirlineSerializer

    def list(self, request):
        expense_types = self.get_queryset()
        serializer = self.get_serializer(expense_types, many=True)
        return Response(serializer.data, status.HTTP_200_OK)
