from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from et2f.models import AirlineCompany, TravelActivity
from locations.models import Location
from partners.models import PartnerOrganization, PCA
from reports.models import Result
from users.models import Office, Section
from .models import Travel, IteneraryItem, Expense, Deduction, CostAssignment, Clearances, Currency


class IteneraryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IteneraryItem
        fields = ('origin', 'destination', 'departure_date', 'arrival_date', 'dsa_region', 'overnight_travel',
                  'mode_of_travel', 'airline')


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ('type', 'document_currency', 'account_currency', 'amount')


class DeductionSerializer(serializers.ModelSerializer):
    day_of_the_week = serializers.CharField(read_only=True)

    class Meta:
        model = Deduction
        fields = ('date', 'breakfast', 'lunch', 'dinner', 'accomodation', 'no_dsa', 'day_of_the_week')


class CostAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostAssignment
        fields = ('wbs', 'share', 'grant')


class ClearancesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clearances
        fields = ('medical_clearance', 'security_clearance', 'security_course')


class TravelActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelActivity
        fields = ('travel_type', 'partner', 'partnership', 'result', 'location')


class TravelDetailsSerializer(serializers.ModelSerializer):
    itinerary = IteneraryItemSerializer(many=True)
    expenses = ExpenseSerializer(many=True)
    deductions = DeductionSerializer(many=True)
    cost_assignments = CostAssignmentSerializer(many=True)
    clearances = ClearancesSerializer(required=False)
    activities = TravelActivitySerializer(many=True)

    class Meta:
        model = Travel
        fields = ('reference_number', 'supervisor', 'office', 'end_date', 'section', 'international_travel',
                  'traveller', 'start_date', 'ta_required', 'purpose', 'id', 'itinerary', 'expenses', 'deductions',
                  'cost_assignments', 'clearances', 'status', 'activities')

    def create(self, validated_data):
        itinerary = validated_data.pop('itinerary', [])
        expenses = validated_data.pop('expenses', [])
        deductions = validated_data.pop('deductions', [])
        cost_assignments = validated_data.pop('cost_assignments', [])
        clearances = validated_data.pop('clearances', {})
        activities = validated_data.pop('activities', [])

        instance = super(TravelDetailsSerializer, self).create(validated_data)

        def create_related_models(model, data):
            instances = []
            for d in data:
                d['travel'] = instance
                instances.append(model(**d))

            model.objects.bulk_create(itinerary)

        # Reverse FK and M2M relations
        create_related_models(IteneraryItem, itinerary)
        create_related_models(Expense, expenses)
        create_related_models(Deduction, deductions)
        create_related_models(CostAssignment, cost_assignments)
        create_related_models(TravelActivity, activities)
        create_related_models(IteneraryItem, itinerary)

        # O2O relations
        clearances['travel'] = instance
        Clearances.objects.create(**clearances)

        return instance

    def update(self, instance, validated_data):
        itinerary = validated_data.pop('itinerary', [])
        expenses = validated_data.pop('expenses', [])
        deductions = validated_data.pop('deductions', [])
        cost_assignments = validated_data.pop('cost_assignments', [])
        clearances = validated_data.pop('clearances', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class TravelListSerializer(TravelDetailsSerializer):
    traveller = serializers.CharField(source='traveller.get_full_name')
    attachment_count = serializers.IntegerField(source='attachments')

    class Meta(TravelDetailsSerializer.Meta):
        fields = ('id', 'reference_number', 'traveller', 'purpose', 'start_date', 'end_date', 'status', 'created',
                  'section', 'office', 'supervisor', 'ta_required', 'ta_reference_number', 'approval_date', 'is_driver',
                  'attachment_count')


class TravelListParameterSerializer(serializers.Serializer):
    _SORTABLE_FIELDS = tuple(TravelListSerializer.Meta.fields)

    sort_by = serializers.CharField(default=_SORTABLE_FIELDS[0])
    reverse = serializers.BooleanField(required=False, default=False)
    search = serializers.CharField(required=False, default='')
    show_hidden = serializers.BooleanField(required=False, default=False)

    def validate_sort_by(self, value):
        if value not in self._SORTABLE_FIELDS:
            valid_values = ', '.join(self._SORTABLE_FIELDS)
            raise ValidationError('Invalid sorting option. Valid values are {}'.format(valid_values))
        return value


# SERIALIZERS FOR STATIC DATA

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