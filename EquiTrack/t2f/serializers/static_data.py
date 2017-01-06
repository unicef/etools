from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from rest_framework import serializers

from t2f.models import AirlineCompany, DSARegion, Currency, Fund, ExpenseType, WBS, Grant, TravelType, ModeOfTravel
from locations.models import Location
from partners.models import PartnerOrganization, PCA
from reports.models import Result
from users.models import Office, Section


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')

    class Meta:
        model = get_user_model()
        fields = ('id', 'full_name')


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ('id', 'name', 'iso_4217')


class AirlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirlineCompany
        fields = ('id', 'name', 'code')


class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = ('id', 'name')


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ('id', 'name')


class PartnerOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name')


class PartnershipSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title')

    class Meta:
        model = PCA
        fields = ('id', 'name', 'partner')


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ('id', 'name')


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ('id', 'name')


class DSARegionSerializer(serializers.ModelSerializer):
    name = serializers.CharField()

    class Meta:
        model = DSARegion
        fields = ('id', 'name', 'country', 'region', 'dsa_amount_usd', 'dsa_amount_60plus_usd', 'dsa_amount_local',
                  'dsa_amount_60plus_local', 'room_rate')


class WBSSerializer(serializers.ModelSerializer):
    class Meta:
        model = WBS
        fields = ('id', 'name')


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grant
        fields = ('id', 'name', 'wbs')


class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ('id', 'name', 'grant')


class ExpenseTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title')

    class Meta:
        model = ExpenseType
        fields = ('id', 'name')


class ModeOfTravelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeOfTravel
        fields = ('id', 'name')


class TravelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelType
        fields = ('id', 'name')


class StaticDataSerializer(serializers.Serializer):
    users = UserSerializer(many=True)
    currencies = CurrencySerializer(many=True)
    airlines = AirlineSerializer(many=True)
    offices = OfficeSerializer(many=True)
    sections = SectionSerializer(many=True)
    partners = PartnerOrganizationSerializer(many=True)
    partnerships = PartnershipSerializer(many=True)
    results = ResultSerializer(many=True)
    locations = LocationSerializer(many=True)
    dsa_regions = DSARegionSerializer(many=True)
    wbs = WBSSerializer(many=True)
    grants = GrantSerializer(many=True)
    funds = FundSerializer(many=True)
    expense_types = ExpenseTypeSerializer(many=True)
    travel_types = TravelTypeSerializer(many=True)
    travel_modes = ModeOfTravelSerializer(many=True)
