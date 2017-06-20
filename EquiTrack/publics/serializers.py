from __future__ import unicode_literals

from django.utils.timezone import now
from django.utils.translation import ugettext

from rest_framework import serializers, ISO_8601
from rest_framework.exceptions import ValidationError

from publics.models import Country, BusinessArea, BusinessRegion, Currency, AirlineCompany, WBS, Grant, Fund,\
    TravelExpenseType, DSARate, DSARegion


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name', 'long_name', 'business_area', 'vision_code', 'iso_2', 'iso_3', 'currency', 'valid_from',
                  'valid_to')


class DSARegionsParameterSerializer(serializers.Serializer):
    values_at = serializers.DateField(format=ISO_8601, required=False, default=now)


class DSARateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DSARate
        fields = ('dsa_amount_usd', 'dsa_amount_60plus_usd', 'dsa_amount_local', 'dsa_amount_60plus_local',
                  'effective_from_date')


class DSARegionSerializer(serializers.ModelSerializer):
    country = serializers.IntegerField(source='country.id', read_only=True)
    long_name = serializers.CharField(source='label')

    class Meta:
        model = DSARegion
        fields = ('id', 'country', 'area_name', 'area_code', 'unique_id', 'unique_name', 'label', 'long_name')

    def to_representation(self, instance):
        ret = super(DSARegionSerializer, self).to_representation(instance)

        values_at = self.context.get('values_at', now())
        rate = instance.rates.get(effective_from_date__lte=values_at, effective_to_date__gte=values_at)

        rate_serializer = DSARateSerializer(rate, context=self.context)
        rate_data = rate_serializer.data

        # Rate data is updated to give bigger priority to dsa region serializer data
        rate_data.update(ret)
        return rate_data


class BusinessRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessRegion
        fields = ('name', 'code')


class BusinessAreaSerializer(serializers.ModelSerializer):
    region = BusinessRegionSerializer()

    class Meta:
        model = BusinessArea
        fields = ('id', 'name', 'code', 'region', 'default_currency')


class CurrencySerializer(serializers.ModelSerializer):
    # TODO rename_field: use 'code' instead
    iso_4217 = serializers.CharField(source='code', read_only=True)
    exchange_to_dollar = serializers.SerializerMethodField()

    class Meta:
        model = Currency
        fields = ('id', 'name', 'code', 'iso_4217', 'exchange_to_dollar')

    def get_exchange_to_dollar(self, obj):
        exchange_rate = obj.exchange_rates.order_by('valid_from').last()
        if exchange_rate:
            return exchange_rate.x_rate
        return None


class AirlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirlineCompany
        fields = ('id', 'name', 'code')


class WBSSerializer(serializers.ModelSerializer):
    class Meta:
        model = WBS
        fields = ('id', 'name', 'business_area', 'grants')


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grant
        fields = ('id', 'name', 'funds')


class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ('id', 'name')


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
    countries = CountrySerializer(many=True)
    business_areas = BusinessAreaSerializer(many=True)
    expense_types = ExpenseTypeSerializer(many=True)
    travel_types = serializers.ListField(child=serializers.CharField())
    travel_modes = serializers.ListField(child=serializers.CharField())

    class Meta:
        fields = ('currencies', 'airlines', 'countries', 'business_areas', 'expense_types',
                  'travel_types', 'travel_modes')


class WBSGrantFundParameterSerializer(serializers.Serializer):
    business_area = serializers.PrimaryKeyRelatedField(queryset=BusinessArea.objects.all(), required=False)

    def to_internal_value(self, data):
        ret = super(WBSGrantFundParameterSerializer, self).to_internal_value(data)
        if 'business_area' not in ret:
            default_business_area_code = self.context['request'].user.profile.country.business_area_code
            default_business_area = BusinessArea.objects.get(code=default_business_area_code)
            ret['business_area'] = default_business_area
        return ret


class GhostDataPKSerializer(serializers.Serializer):
    values = serializers.ListField(child=serializers.IntegerField(min_value=1, required=True), required=True,
                                   allow_empty=False)


class MultiGhostDataSerializer(GhostDataPKSerializer):
    category = serializers.CharField(required=True)

    def validate_category(self, value):
        if 'available_categories' not in self.context:
            return value

        if value not in self.context['available_categories']:
            raise ValidationError(ugettext('Invalid category'))

        return value
