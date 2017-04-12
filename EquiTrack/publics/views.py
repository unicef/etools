from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query_utils import Q
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from publics.models import Country, DSARegion, Currency, AirlineCompany, WBS, Grant, Fund, TravelExpenseType, \
    BusinessArea
from publics.serializers import CountrySerializer, DSARegionSerializer, PublicStaticDataSerializer, \
    WBSGrantFundSerializer, WBSGrantFundParameterSerializer, CurrencySerializer, ExpenseTypeSerializer, \
    BusinessAreaSerializer, GhostDataPKSerializer, MultiGhostDataSerializer, AirlineSerializer
from t2f.models import TravelType, ModeOfTravel


class GhostDataMixin(object):
    def missing(self, request):
        parameter_serializer = GhostDataPKSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset()
        model = queryset.model
        
        try:
            obj = model.admin_objects.get(id=parameter_serializer.data['value'])
        except ObjectDoesNotExist:
            return Response({'non_field_errors': ['Invalid PK value']},
                            status.HTTP_400_BAD_REQUEST)
            
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status.HTTP_200_OK)


class CountryViewSet(mixins.ListModelMixin,
                     GhostDataMixin,
                     viewsets.GenericViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (IsAdminUser,)


class DSARegionViewSet(mixins.ListModelMixin,
                       GhostDataMixin,
                       viewsets.GenericViewSet):
    queryset = DSARegion.objects.all()
    serializer_class = DSARegionSerializer
    permission_classes = (IsAdminUser,)


class StaticDataView(GhostDataMixin,
                     viewsets.GenericViewSet):
    serializer_class = PublicStaticDataSerializer

    def list(self, request):
        country = request.user.profile.country
        dsa_regions = DSARegion.objects.filter(country__business_area__code=country.business_area_code)
        dsa_regions = dsa_regions.select_related('country')

        currencies = Currency.objects.all().prefetch_related('exchange_rates')
        business_areas = BusinessArea.objects.all().select_related('region')

        expense_type_q = Q(travel_agent__isnull=True)
        expense_type_q |= Q(travel_agent__country__business_area__code=country.business_area_code)
        expense_types = TravelExpenseType.objects.select_related('travel_agent').filter(expense_type_q)

        data = {'currencies': currencies, # Moved
                'dsa_regions': dsa_regions, # Moved
                'business_areas': business_areas, # Moved
                'expense_types': expense_types, # Moved

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

        try:
            obj = model.admin_objects.get(id=parameter_serializer.data['value'])
        except ObjectDoesNotExist:
            return Response({'non_field_errors': ['Invalid PK value']},
                            status.HTTP_400_BAD_REQUEST)

        serializer = serializer_class(obj, context=self.get_serializer_context())
        return Response(serializer.data, status.HTTP_200_OK)

    def get_airlines_queryset(self):
        return AirlineCompany.objects.all()

    def get_country_queryset(self):
        return Country.objects.all()


class DSARegionsView(GhostDataMixin,
                     viewsets.GenericViewSet):
    serializer_class = DSARegionSerializer

    def list(self, request):
        workspace = request.user.profile.country

        dsa_regions = DSARegion.objects.filter(country__business_area__code=workspace.business_area_code)
        dsa_regions = dsa_regions.select_related('country')

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
    serializer_class = CurrencySerializer

    def list(self, request):
        currencies = Currency.objects.all()
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


class WBSGrantFundView(GhostDataMixin,
                       viewsets.GenericViewSet):
    serializer_class = WBSGrantFundSerializer

    def list(self, request):
        parameter_serializer = WBSGrantFundParameterSerializer(data=request.GET, context=self.get_serializer_context())
        parameter_serializer.is_valid(raise_exception=True)

        business_area = parameter_serializer.validated_data['business_area']

        wbs_qs = WBS.objects.filter(business_area=business_area).prefetch_related('grants')
        grant_qs = Grant.objects.filter(wbs__in=wbs_qs).prefetch_related('funds')
        funds_qs = Fund.objects.filter(grants__in=grant_qs)
        data = {'wbs': wbs_qs,
                'funds': funds_qs,
                'grants': grant_qs}
        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)
