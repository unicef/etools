from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from rest_framework import serializers

from et2f.models import AirlineCompany, DSARegion, Currency
from funds.models import Grant
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
        fields = ('id', 'name')


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ('id', 'name')


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ('id', 'name')


class DSARegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DSARegion
        fields = ('id', 'name', 'dsa_amount_usd', 'dsa_amount_60plus_usd', 'dsa_amount_local',
                  'dsa_amount_60plus_local', 'room_rate')


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grant
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
    wbs = ResultSerializer(many=True)
    grants = GrantSerializer(many=True)