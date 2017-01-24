from __future__ import unicode_literals

from rest_framework import viewsets, mixins, generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from publics.models import Country, DSARegion, Currency, AirlineCompany, WBS, Grant, Fund, ExpenseType, BusinessArea
from publics.serialziers import CountrySerializer, DSARegionSerializer, PublicStaticDataSerializer, \
    WBSGrantFundSerializer, WBSGrantFundParameterSerializer
from t2f.models import TravelType, ModeOfTravel


class CountryViewSet(mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (IsAdminUser,)


class DSARegionViewSet(mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    queryset = DSARegion.objects.all()
    serializer_class = DSARegionSerializer
    permission_classes = (IsAdminUser,)


class StaticDataView(generics.GenericAPIView):
    serializer_class = PublicStaticDataSerializer

    def get(self, request):
        country = request.user.profile.country
        dsa_regions = DSARegion.objects.filter(country__business_area__code=country.business_area_code)

        data = {'currencies': Currency.objects.all(),
                'airlines': AirlineCompany.objects.all(),
                'dsa_regions': dsa_regions,
                'countries': Country.objects.all(),
                'business_areas': BusinessArea.objects.all(),
                'wbs': WBS.objects.all(),
                'grants': Grant.objects.all(),
                'funds': Fund.objects.all(),
                'expense_types': ExpenseType.objects.all(),
                'travel_types': [c[0].lower() for c in TravelType.CHOICES],
                'travel_modes': [c[0].lower() for c in ModeOfTravel.CHOICES]}

        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)


class WBSGrantFundView(generics.GenericAPIView):
    serializer_class = WBSGrantFundSerializer

    def get(self, request):
        parameter_serialzier = WBSGrantFundParameterSerializer(data=request.GET, context=self.get_serializer_context())
        parameter_serialzier.is_valid(raise_exception=True)

        business_area = parameter_serialzier.validated_data['business_area']

        wbs_qs = WBS.objects.filter(business_area=business_area)
        grant_qs = Grant.objects.filter(wbs__in=wbs_qs)
        funds_qs = Fund.objects.filter(grant__in=grant_qs)
        data = {'wbs': wbs_qs,
                'funds': funds_qs,
                'grants': grant_qs}
        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)
