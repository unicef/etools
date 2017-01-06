from __future__ import unicode_literals

from itertools import chain

from django.contrib.auth import get_user_model
from django.db.models.fields.related import ManyToManyField
from django.utils.functional import cached_property
from rest_framework import serializers, ISO_8601
from rest_framework.exceptions import ValidationError


from locations.models import Location
from t2f.models import TravelActivity, Travel, IteneraryItem, Expense, Deduction, CostAssignment, Clearances,\
    TravelPermission, TravelAttachment, AirlineCompany, ModeOfTravel, ActionPoint
from locations.models import Location


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

        if not permission_matrix:
            return True

        return permission_matrix.has_permission(permission_type, model_name, field_name)

    def _can_read_field(self, field):
        return self._check_permission(TravelPermission.VIEW, field.field_name)

    def _can_write_field(self, field):
        return self._check_permission(TravelPermission.EDIT, field.field_name)


class ActionPointSerializer(serializers.ModelSerializer):
    trip_reference_number = serializers.CharField(source='travel.reference_number', read_only=True)
    action_point_number = serializers.CharField(read_only=True)

    class Meta:
        model = ActionPoint
        fields = ('id', 'action_point_number', 'trip_reference_number', 'description', 'due_date', 'person_responsible',
                  'status', 'completed_at', 'actions_taken', 'follow_up', 'comments', 'created_at', 'assigned_by')


class IteneraryItemSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)
    airlines = serializers.PrimaryKeyRelatedField(many=True, queryset=AirlineCompany.objects.all(), required=False,
                                                  allow_null=True)

    class Meta:
        model = IteneraryItem
        fields = ('id', 'origin', 'destination', 'departure_date', 'arrival_date', 'dsa_region', 'overnight_travel',
                  'mode_of_travel', 'airlines')


class ExpenseSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)

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
    medical_clearance = serializers.CharField()
    security_clearance = serializers.CharField()
    security_course = serializers.CharField()

    class Meta:
        model = Clearances
        fields = ('id', 'medical_clearance', 'security_clearance', 'security_course')


class TravelActivitySerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)
    locations = serializers.PrimaryKeyRelatedField(many=True, queryset=Location.objects.all(), required=False,
                                                   allow_null=True)

    class Meta:
        model = TravelActivity
        fields = ('id', 'travel_type', 'partner', 'partnership', 'result', 'locations', 'primary_traveler', 'date')


class TravelAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='file.url', read_only=True)

    class Meta:
        model = TravelAttachment
        fields = ('id', 'name', 'type', 'url', 'file')

    def create(self, validated_data):
        validated_data['travel'] = self.context['travel']
        return super(TravelAttachmentSerializer, self).create(validated_data)


class DSASerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(format=ISO_8601)
    end_date = serializers.DateTimeField(format=ISO_8601)
    daily_rate_usd = serializers.DecimalField(max_digits=20, decimal_places=4)
    night_count = serializers.IntegerField()
    amount_usd = serializers.DecimalField(max_digits=20, decimal_places=4)
    dsa_region = serializers.IntegerField()
    dsa_region_name = serializers.CharField()


class CostSummarySerializer(serializers.Serializer):
    dsa_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    deductions_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    dsa = DSASerializer(many=True)
    preserved_expenses = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    expenses_delta = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)


class TravelDetailsSerializer(serializers.ModelSerializer):
    itinerary = IteneraryItemSerializer(many=True, required=False)
    expenses = ExpenseSerializer(many=True, required=False)
    deductions = DeductionSerializer(many=True, required=False)
    cost_assignments = CostAssignmentSerializer(many=True, required=False)
    clearances = ClearancesSerializer(required=False)
    activities = TravelActivitySerializer(many=True, required=False)
    attachments = TravelAttachmentSerializer(many=True, read_only=True)
    cost_summary = CostSummarySerializer(read_only=True)
    report = serializers.CharField(source='report_note', required=False, default='', allow_blank=True)
    mode_of_travel = serializers.PrimaryKeyRelatedField(queryset=ModeOfTravel.objects.all(), required=False, many=True)
    action_points = ActionPointSerializer(many=True, required=False)

    # Fix because of a frontend validation failure (fix it on the frontend first)
    estimated_travel_cost = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)

    class Meta:
        model = Travel
        fields = ('reference_number', 'supervisor', 'office', 'end_date', 'section', 'international_travel',
                  'traveler', 'start_date', 'ta_required', 'purpose', 'id', 'itinerary', 'expenses', 'deductions',
                  'cost_assignments', 'clearances', 'status', 'activities', 'mode_of_travel', 'estimated_travel_cost',
                  'currency', 'completed_at', 'canceled_at', 'rejection_note', 'cancellation_note', 'attachments',
                  'cost_summary', 'certification_note', 'report', 'additional_note', 'misc_expenses', 'action_points')
        # Review this, as a developer could be confusing why the status field is not saved during an update
        read_only_fields = ('status', 'reference_number')

    def __init__(self, *args, **kwargs):
        data = kwargs.get('data', {})
        self.transition_name = data.get('transition_name', None)
        super(TravelDetailsSerializer, self).__init__(*args, **kwargs)

    # -------- Validation method --------
    def validate_cost_assignments(self, value):
        # If transition is None, it's a normal save (not an action) and we don't have to validate this
        if not value or self.transition_name is None:
            return value

        share_sum = sum([ca['share'] for ca in value])
        if share_sum != 100:
            raise ValidationError('Shares should add up to 100%')
        return value

    def validate_itinerary(self, value):
        if self.transition_name == 'submit_for_approval' and len(value) < 1:
            raise ValidationError('Travel must have at least one itinerary item')

        if not value:
            return value

        # Check destination-origin relation
        previous_destination = value[0]['destination']

        for itinerary_item in value[1:]:
            if itinerary_item['origin'] != previous_destination:
                raise ValidationError('Origin should match with the previous destination')
            previous_destination = itinerary_item['destination']

        # Check date integrity
        dates_iterator = chain.from_iterable((i['departure_date'], i['arrival_date']) for i in value)

        current_date = dates_iterator.next()
        for date in dates_iterator:
            if date is None:
                continue

            if date < current_date:
                raise ValidationError('Itinerary items have to be ordered by date')
            current_date = date

        return value

    # -------- Create and update methods --------
    def create(self, validated_data):
        itinerary = validated_data.pop('itinerary', [])
        expenses = validated_data.pop('expenses', [])
        deductions = validated_data.pop('deductions', [])
        cost_assignments = validated_data.pop('cost_assignments', [])
        clearances = validated_data.pop('clearances', {})
        activities = validated_data.pop('activities', [])
        action_points = validated_data.pop('action_points', [])

        instance = super(TravelDetailsSerializer, self).create(validated_data)

        # Reverse FK and M2M relations
        self.create_related_models(IteneraryItem, itinerary, travel=instance)
        self.create_related_models(Expense, expenses, travel=instance)
        self.create_related_models(Deduction, deductions, travel=instance)
        self.create_related_models(CostAssignment, cost_assignments, travel=instance)
        self.create_related_models(ActionPoint, action_points, travel=instance)
        travel_activities = self.create_related_models(TravelActivity, activities)
        for activity in travel_activities:
            activity.travels.add(instance)

        # O2O relations
        clearances['travel'] = instance
        Clearances.objects.create(**clearances)

        return instance

    def create_related_models(self, model, related_data, **kwargs):
        new_models = []
        for data in related_data:
            data = dict(data)
            m2m_fields = {k: data.pop(k, []) for k in data.keys()
                          if isinstance(model._meta.get_field_by_name(k)[0], ManyToManyField)}
            data.update(kwargs)
            related_instance = model.objects.create(**data)
            for field_name, value in m2m_fields.items():
                related_manager = getattr(related_instance, field_name)
                related_manager.add(*value)
            new_models.append(related_instance)
        return new_models

    def update(self, instance, validated_data):
        related_attributes = {}
        for attr_name in ('itinerary', 'expenses', 'deductions', 'cost_assignments', 'activities', 'clearances',
                          'action_points'):
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
        m2m_fields = {k: data.pop(k, []) for k in data.keys()
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
                    try:
                        self.create_related_models(model, [attrs], travel=self.instance)
                    except TypeError:
                        attrs.pop('travel', None)
                        new_models = self.create_related_models(model, [attrs])
                        for m in new_models:
                            m.travels.add(self.instance)

            # Delete the leftover
            model.objects.filter(pk__in=related_to_delete).delete()

        else:
            if related_data and related:
                self.update_object(related, related_data)
            elif related_data and related is None:
                model = self._fields[attr_name].Meta.model
                self.create_related_models(model, [related_data], travel=self.instance)
            elif related_data is None and related:
                related.delete()


class TravelListSerializer(TravelDetailsSerializer):
    traveler = serializers.CharField(source='traveler.get_full_name')

    class Meta:
        model = Travel
        fields = ('id', 'reference_number', 'traveler', 'purpose', 'status', 'section', 'office', 'start_date',
                  'end_date')
        read_only_fields = ('status',)


class CloneOutputSerializer(TravelDetailsSerializer):
    class Meta:
        model = Travel
        fields = ('id',)


class CloneParameterSerializer(serializers.Serializer):
    traveler = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())

    class Meta:
        fields = ('traveler',)
