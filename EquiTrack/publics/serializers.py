from __future__ import unicode_literals

from rest_framework import serializers

from publics.models import Country, DSARegion, BusinessArea, BusinessRegion, Currency, AirlineCompany, WBS, Grant,\
    Fund, TravelExpenseType


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name', 'long_name', 'business_area', 'vision_code', 'iso_2', 'iso_3', 'currency', 'valid_from',
                  'valid_to')
        
        
class DSARegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DSARegion
        fields = ('id', 'country', 'area_name', 'area_code', 'dsa_amount_usd', 'dsa_amount_60plus_usd',
                  'dsa_amount_local', 'dsa_amount_60plus_local', 'room_rate', 'finalization_date', 'eff_date',
                  'unique_id', 'unique_name', 'label')


class BusinessRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessRegion
        fields = ('name', 'code')


class BusinessAreaSerializer(serializers.ModelSerializer):
    region = BusinessRegionSerializer()

    class Meta:
        model = BusinessArea
        fields = ('id', 'name', 'code', 'region')


class CurrencySerializer(serializers.ModelSerializer):
    iso_4217 = serializers.CharField(source='code', read_only=True)
    exchange_to_dollar = serializers.SerializerMethodField()

    class Meta:
        model = Currency
        fields = ('id', 'name', 'iso_4217')

    def get_exchange_to_dollar(self, obj):
        return obj.exchange_rates.order_by('valid_from').last().x_rate

class AirlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirlineCompany
        fields = ('id', 'name', 'code')


class WBSSerializer(serializers.ModelSerializer):
    class Meta:
        model = WBS
        fields = ('id', 'name', 'business_area')


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
    vendor_number = serializers.CharField()
    unique = serializers.SerializerMethodField()

    class Meta:
        model = TravelExpenseType
        fields = ('id', 'name', 'vendor_number', 'unique')

    def get_unique(self, obj):
        return obj.is_travel_agent


class PublicStaticDataSerializer(serializers.Serializer):
    currencies = CurrencySerializer(many=True)
    airlines = AirlineSerializer(many=True)
    dsa_regions = DSARegionSerializer(many=True)
    countries = CountrySerializer(many=True)
    business_areas = BusinessAreaSerializer(many=True)
    wbs = WBSSerializer(many=True)
    grants = GrantSerializer(many=True)
    funds = FundSerializer(many=True)
    expense_types = ExpenseTypeSerializer(many=True)
    travel_types = serializers.ListField(child=serializers.CharField())
    travel_modes = serializers.ListField(child=serializers.CharField())

    class Meta:
        fields = ('currencies', 'airlines', 'dsa_regions', 'countries', 'business_areas', 'wbs', 'grants', 'funds',
                  'expense_types', 'travel_types', 'travel_modes')


class WBSGrantFundParameterSerializer(serializers.Serializer):
    business_area = serializers.PrimaryKeyRelatedField(queryset=BusinessArea.objects.all())


class WBSGrantFundSerializer(serializers.Serializer):
    wbs = WBSSerializer(many=True)
    grants = GrantSerializer(many=True)
    funds = FundSerializer(many=True)

    class Meta:
        fields = ('wbs', 'grant', 'fund')
