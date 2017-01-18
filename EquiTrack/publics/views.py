from __future__ import unicode_literals

from rest_framework import viewsets, mixins, generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from publics.models import Country, DSARegion, Currency, AirlineCompany, WBS, Grant, Fund, ExpenseType, BusinessArea
from publics.serialziers import CountrySerializer, DSARegionSerializer, PublicStaticDataSerializer
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
        # TODO: this is not only static data some of the data changes,
        # there should be calls to individual endpoints for:
        # users, partners, partnerships, results, locations, wbs, grants, funds

        country = request.user.profile.country
        dsa_regions = DSARegion.objects.filter(area_code=country.business_area_code)

        data = {'currencies': Currency.objects.all(),
                'airlines': AirlineCompany.objects.all(),
                'dsa_regions': dsa_regions,
                'countries': Country.objects.all(),
                'business_areas': BusinessArea.objects.all(),
                'wbs': WBS.objects.all(),
                'grants': Grant.objects.all(),
                'funds': Fund.objects.all(),
                'expense_types': ExpenseType.objects.all(),
                'travel_types': [c[0] for c in TravelType.CHOICES],
                'travel_modes': [c[0] for c in ModeOfTravel.CHOICES]}

        serializer = self.get_serializer(data)
        return Response(serializer.data, status.HTTP_200_OK)
