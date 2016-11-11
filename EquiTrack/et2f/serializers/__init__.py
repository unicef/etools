from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.db.models.fields.related import ManyToManyField
from django.utils.functional import cached_property
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from et2f.models import TravelActivity, Travel, IteneraryItem, Expense, Deduction, CostAssignment, Clearances,\
    TravelPermission


class PermissionBasedModelSerializer(serializers.ModelSerializer):
    @cached_property
    def _writable_fields(self):
        fields = super(PermissionBasedModelSerializer, self)._writable_fields
        return [f for f in fields if self._can_write_field(f)]

    @cached_property
    def _readable_fields(self):
        fields = super(PermissionBasedModelSerializer, self)._readable_fields
        return [f for f in fields if self._can_read_field(f)]

    def _check_permission(self, permission_type, field_name):
        model_name = model_name = self.Meta.model.__name__.lower()

        permission_matrix = self.context.get('permission_matrix')

        if permission_matrix is None:
            return True

        return permission_matrix.has_permission(permission_type, model_name, field_name)

    def _can_read_field(self, field):
        return self._check_permission(TravelPermission.VIEW, field.field_name)

    def _can_write_field(self, field):
        return self._check_permission(TravelPermission.EDIT, field.field_name)


class IteneraryItemSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = IteneraryItem
        fields = ('id', 'origin', 'destination', 'departure_date', 'arrival_date', 'dsa_region', 'overnight_travel',
                  'mode_of_travel', 'airlines')


class ExpenseSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Expense
        fields = ('id', 'type', 'document_currency', 'account_currency', 'amount')


class DeductionSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)
    day_of_the_week = serializers.CharField(read_only=True)

    class Meta:
        model = Deduction
        fields = ('id', 'date', 'breakfast', 'lunch', 'dinner', 'accomodation', 'no_dsa', 'day_of_the_week')


class CostAssignmentSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = CostAssignment
        fields = ('id', 'wbs', 'share', 'grant', 'fund')


class ClearancesSerializer(PermissionBasedModelSerializer):
    medical_clearance = serializers.NullBooleanField()
    security_clearance = serializers.NullBooleanField()
    security_course = serializers.NullBooleanField()

    class Meta:
        model = Clearances
        fields = ('id', 'medical_clearance', 'security_clearance', 'security_course')


class TravelActivitySerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = TravelActivity
        fields = ('id', 'travel_type', 'partner', 'partnership', 'result', 'locations', 'primary_traveler', 'date')


class TravelDetailsSerializer(serializers.ModelSerializer):
    itinerary = IteneraryItemSerializer(many=True, required=False)
    expenses = ExpenseSerializer(many=True, required=False)
    deductions = DeductionSerializer(many=True, required=False)
    cost_assignments = CostAssignmentSerializer(many=True, required=False)
    clearances = ClearancesSerializer(required=False)
    activities = TravelActivitySerializer(many=True, required=False)

    class Meta:
        model = Travel
        fields = ('reference_number', 'supervisor', 'office', 'end_date', 'section', 'international_travel',
                  'traveller', 'start_date', 'ta_required', 'purpose', 'id', 'itinerary', 'expenses', 'deductions',
                  'cost_assignments', 'clearances', 'status', 'activities', 'mode_of_travel', 'estimated_travel_cost',
                  'currency', 'completed_at', 'canceled_at', 'rejection_note')
        # Review this, as a developer could be confusing why the status field is not saved during an update
        read_only_fields = ('status',)

    def __init__(self, *args, **kwargs):
        data = kwargs.get('data', {})
        self.transition_name = data.get('transition_name', None)
        super(TravelDetailsSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        itinerary = validated_data.pop('itinerary', [])
        expenses = validated_data.pop('expenses', [])
        deductions = validated_data.pop('deductions', [])
        cost_assignments = validated_data.pop('cost_assignments', [])
        clearances = validated_data.pop('clearances', {})
        activities = validated_data.pop('activities', [])

        instance = super(TravelDetailsSerializer, self).create(validated_data)

        def create_related_models(model, related_data):
            for data in related_data:
                m2m_fields = {k: data.pop(k, []) for k in data
                              if isinstance(model._meta.get_field_by_name(k)[0], ManyToManyField)}
                data['travel'] = instance
                related_instance = model.objects.create(**data)
                for field_name, value in m2m_fields.items():
                    related_manager = getattr(related_instance, field_name)
                    related_manager.add(*value)

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
        related_attributes = {}
        for attr_name in ('itinerary', 'expenses', 'deductions', 'cost_assignments', 'activities', 'clearances'):
            if isinstance(self._fields[attr_name], serializers.ListSerializer):
                default = []
            elif self._fields[attr_name].allow_null:
                default = None
            else:
                default = {}
            related_attributes[attr_name] = validated_data.pop(attr_name, default)

        self.update_object(instance, validated_data)

        for attr_name, related_data in related_attributes.items():
            self.update_related_objects(attr_name, related_data)

        return instance

    def update_object(self, obj, data):
        m2m_fields = {k: data.pop(k, []) for k in data
                      if isinstance(obj._meta.get_field_by_name(k)[0], ManyToManyField)}
        for attr, value in data.items():
            setattr(obj, attr, value)
        obj.save()

        for field_name, value in m2m_fields.items():
            related_manager = getattr(obj, field_name)
            related_manager.add(*value)

    def update_related_objects(self, attr_name, related_data):
        many = isinstance(self._fields[attr_name], serializers.ListSerializer)

        related = getattr(self.instance, attr_name)
        if many:
            # Load the 1ueryset
            related = related.all()

            model = self._fields[attr_name].child.Meta.model
            related_to_delete = {o.pk for o in related}

            # Iterate over incoming data and create/update the models
            for attrs in related_data:
                pk = attrs.pop('id', None)
                if pk:
                    obj = related.get(pk=pk)
                    self.update_object(obj, attrs)
                    related_to_delete.remove(pk)
                else:
                    model.objects.create(travel=self.instance, **attrs)

            # Delete the leftover
            model.objects.filter(pk__in=related_to_delete).delete()

        else:
            if related_data and related:
                self.update_object(related, related_data)
            elif related_data and related is None:
                model = self._fields[attr_name].Meta.model
                model.objects.creat(travel=self.instance, **related_data)
            elif related_data is None and related:
                related.delete()


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


class CurrentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')

    class Meta:
        model = get_user_model()
        fields = ('id', 'full_name')