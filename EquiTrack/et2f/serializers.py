from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

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


class ExpenseSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = Expense


class DeductionSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    day_of_the_week = serializers.CharField(read_only=True)

    class Meta:
        model = Deduction


class CostAssignmentSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = CostAssignment


class ClearancesSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = Clearances


class TravelDetailsSerializer(VerboseFieldRepresentationMixin, serializers.ModelSerializer):
    itinerary = IteneraryItemSerializer(many=True)
    expenses = ExpenseSerializer(many=True)
    deductions = DeductionSerializer(many=True)
    cost_assignments = CostAssignmentSerializer(many=True)
    clearances = ClearancesSerializer()

    class Meta:
        model = Travel
        fields = ('reference_number', 'supervisor', 'office', 'end_date', 'section', 'international_travel',
                  'traveller', 'start_date', 'ta_required', 'purpose', 'id', 'itinerary', 'expenses', 'deductions',
                  'cost_assignments', 'clearances')


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


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')

    class Meta:
        model = get_user_model()
        fields = ('id', 'full_name')


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ('id', 'name', 'iso_4217')


class StaticDataSerializer(serializers.Serializer):
    users = UserSerializer(many=True)
    currencies = CurrencySerializer(many=True)
