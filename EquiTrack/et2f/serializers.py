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


class VerboseFieldRepresentationMixin(serializers.Serializer):
    SECTION_PREFIX = 'SECTION'

    # @property
    # def _use_verbose_fields(self):
    #     current = self
    #     while True:
    #         # In case of root serializer many=True
    #         if isinstance(current.parent, serializers.ListSerializer) and current.parent.parent is None:
    #             break
    #
    #         # Root serializer
    #         if current.parent is None:
    #             break
    #
    #         current = current.parent
    #
    #     meta = getattr(current, 'Meta', None)
    #     return getattr(meta, 'use_verbose_fields', True)
    #
    # def _get_self_field_name(self):
    #     if self.parent is None:
    #         return None
    #
    #     if not self.field_name:
    #         return self.parent.field_name
    #     return self.field_name
    #
    # def _get_field_permission_name(self, field):
    #     field_name = field.field_name
    #
    #     if isinstance(field, serializers.BaseSerializer):
    #         return '{}:{}'.format(self.SECTION_PREFIX, field_name)
    #
    #     self_field_name = self._get_self_field_name()
    #     if self_field_name:
    #         return '{}:{}'.format(self_field_name, field.field_name)
    #     return field.field_name
    #
    # def to_representation(self, instance):
    #     ret = super(VerboseFieldRepresentationMixin, self).to_representation(instance)
    #     if not self._use_verbose_fields:
    #         return ret
    #
    #     for field_name, value in ret.items():
    #         ret[field_name] = {'value': value,
    #                            'read_only': False,
    #                            'permission': self._get_field_permission_name(self.fields[field_name])}
    #     return ret


class IteneraryItemSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = IteneraryItem
        fields = ('origin', 'destination', 'departure_date', 'arrival_date', 'dsa_region', 'overnight_travel',
                  'mode_of_travel', 'airline')


class ExpenseSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ('type', 'document_currency', 'account_currency', 'amount')


class DeductionSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    day_of_the_week = serializers.CharField(read_only=True)

    class Meta:
        model = Deduction
        fields = ('date', 'breakfast', 'lunch', 'dinner', 'accomodation', 'no_dsa', 'day_of_the_week')


class CostAssignmentSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = CostAssignment
        fields = ('wbs', 'share', 'grant')


class ClearancesSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = Clearances
        fields = ('medical_clearance', 'security_clearance', 'security_course')


class TravelActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelActivity
        fields = ('travel_type', 'partner', 'partnership', 'result', 'location')


class TravelDetailsSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
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
        clearances = validated_data.pop('clearances', [])
        activities = validated_data.pop('activities', [])

        instance = super(TravelDetailsSerializer, self).create(validated_data)

        def add_travel(data):
            data['travel'] = instance
            return data

        itinerary = [IteneraryItem(**d) for d in map(add_travel, itinerary)]
        IteneraryItem.objects.bulk_create(itinerary)

        expenses = [Expense(**d) for d in map(add_travel, expenses)]
        Expense.objects.bulk_create(expenses)

        deductions = [Deduction(**d) for d in map(add_travel, deductions)]
        Deduction.objects.bulk_create(deductions)

        cost_assignments = [CostAssignment(**d) for d in map(add_travel, cost_assignments)]
        CostAssignment.objects.bulk_create(cost_assignments)

        clearances = [Clearances(**d) for d in map(add_travel, clearances)]
        Clearances.objects.bulk_create(clearances)

        activities = [TravelActivity(**d) for d in map(add_travel, activities)]
        TravelActivity.objects.bulk_create(activities)

        return instance

    # def update(self, instance, validated_data):
    #     itinerary = validated_data.pop('itinerary', [])
    #     expenses = validated_data.pop('expenses', [])
    #     deductions = validated_data.pop('deductions', [])
    #     cost_assignments = validated_data.pop('cost_assignments', [])
    #     clearances = validated_data.pop('clearances', [])
    #
    #     instance = super(TravelDetailsSerializer, self).update(instance)
    #
    #     return instance


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