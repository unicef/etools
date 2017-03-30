from __future__ import unicode_literals

import operator
from itertools import chain
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields.related import ManyToManyField
from django.utils.functional import cached_property
from django.utils.itercompat import is_iterable
from rest_framework import serializers, ISO_8601
from rest_framework.exceptions import ValidationError

from publics.models import AirlineCompany
from t2f.models import TravelActivity, Travel, ItineraryItem, Expense, Deduction, CostAssignment, Clearances,\
    TravelAttachment, ActionPoint, TravelPermission
from locations.models import Location
from t2f.serializers import CostSummarySerializer

User = get_user_model()

itineraryItemSortKey = operator.attrgetter('departure_date')

def order_itineraryitems(instance, items):
    # ensure itineraryitems are ordered by `departure_date`
    if (items is not None) and (len(items) > 1):
        instance.set_itineraryitem_order([i.pk for i in
            sorted(items, key=itineraryItemSortKey)])

class LowerTitleField(serializers.CharField):
    def to_representation(self, value):
        return value.lower()

    def to_internal_value(self, data):
        value = super(LowerTitleField, self).to_internal_value(data)
        return value.title()


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
    trip_id = serializers.IntegerField(source='travel.id', read_only=True)
    assigned_by = serializers.IntegerField(source='assigned_by.id', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)

    description = serializers.CharField(required=True)
    due_date = serializers.DateTimeField(required=True)
    person_responsible = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    person_responsible_name = serializers.CharField(source='person_responsible.get_full_name', read_only=True)
    status = serializers.CharField(required=True)

    class Meta:
        model = ActionPoint
        fields = ('id', 'action_point_number', 'trip_reference_number', 'description', 'due_date', 'person_responsible',
                  'status', 'completed_at', 'actions_taken', 'follow_up', 'comments', 'created_at', 'assigned_by',
                  'assigned_by_name', 'person_responsible_name', 'trip_id')

    def validate_due_date(self, value):
        if value.date() < datetime.utcnow().date():
            raise ValidationError('Due date cannot be earlier than today.')
        return value

    def validate(self, attrs):
        error_dict = {}
        status = attrs.get('status')
        if status is None and self.instance:
            status = self.instance.status

        if status == ActionPoint.COMPLETED and not attrs.get('completed_at'):
            error_dict['completed_at'] = 'This field is required'

        if (status == ActionPoint.COMPLETED or attrs.get('completed_at')) and not attrs.get('actions_taken'):
            error_dict['actions_taken'] = 'This field is required'

        if error_dict:
            raise ValidationError(error_dict)

        return attrs

    def validate_status(self, value):
        statuses = dict(ActionPoint.STATUS).keys()
        if value not in statuses:
            raise ValidationError('Invalid status. Possible choices: {}'.format(', '.join(statuses)))
        return value


class ItineraryItemSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)
    airlines = serializers.PrimaryKeyRelatedField(many=True, queryset=AirlineCompany.objects.all(), required=False,
                                                  allow_null=True)
    mode_of_travel = LowerTitleField(required=False)

    class Meta:
        model = ItineraryItem
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
        fields = ('id', 'wbs', 'share', 'grant', 'fund', 'business_area', 'delegate')


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
    travel_type = LowerTitleField(required=False, allow_null=True)
    is_primary_traveler = serializers.BooleanField(required=False)
    primary_traveler = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True)

    class Meta:
        model = TravelActivity
        fields = ('id', 'travel_type', 'partner', 'partnership', 'government_partnership', 'result', 'locations',
                  'primary_traveler', 'date', 'is_primary_traveler')

    def validate(self, attrs):
        if 'id' not in attrs:
            if not attrs.get('is_primary_traveler'):
                if not attrs.get('primary_traveler'):
                    raise ValidationError({'primary_traveler': 'This field is required'})

        if attrs.get('partnership') and attrs.get('government_partnership'):
            raise ValidationError('Partnership and government partnership cannot be set at the same time')

        if 'partnership' in attrs:
            attrs['government_partnership'] = None
        elif 'government_partnership' in attrs:
            attrs['partnership'] = None

        return attrs

    def to_internal_value(self, data):
        ret = super(TravelActivitySerializer, self).to_internal_value(data)
        ret.pop('is_primary_traveler', None)
        return ret


class TravelAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='file.url', read_only=True)

    class Meta:
        model = TravelAttachment
        fields = ('id', 'name', 'type', 'url', 'file')

    def create(self, validated_data):
        validated_data['travel'] = self.context['travel']
        return super(TravelAttachmentSerializer, self).create(validated_data)


class TravelDetailsSerializer(serializers.ModelSerializer):
    itinerary = ItineraryItemSerializer(many=True, required=False)
    expenses = ExpenseSerializer(many=True, required=False)
    deductions = DeductionSerializer(many=True, required=False)
    cost_assignments = CostAssignmentSerializer(many=True, required=False)
    clearances = ClearancesSerializer(required=False)
    activities = TravelActivitySerializer(many=True, required=False)
    attachments = TravelAttachmentSerializer(many=True, read_only=True)
    cost_summary = CostSummarySerializer(read_only=True)
    report = serializers.CharField(source='report_note', required=False, default='', allow_blank=True)
    mode_of_travel = serializers.ListField(child=LowerTitleField(), allow_null=True, required=False)
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

        ta_required = data.get('ta_required', False)
        if self.instance and not is_iterable(self.instance):
            ta_required |= self.instance.ta_required

        if not ta_required:
            data.pop('itinerary', None)
            data.pop('deductions', None)
            data.pop('expenses', None)
            data.pop('cost_assignments', None)

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
        if self.transition_name == 'submit_for_approval' and len(value) < 2:
            raise ValidationError('Travel must have at least two itinerary item')

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

    def validate(self, attrs):
        if 'mode_of_travel' in attrs and attrs['mode_of_travel'] is None:
            attrs['mode_of_travel'] = []
        return super(TravelDetailsSerializer, self).validate(attrs)

    def to_internal_value(self, data):
        if self.instance:
            traveler_id = getattr(self.instance.traveler, 'id', None)
        else:
            traveler_id = None

        traveler_id = data.get('traveler', traveler_id)

        for travel_activity_data in data.get('activities', []):
            if travel_activity_data.get('is_primary_traveler'):
                travel_activity_data['primary_traveler'] = traveler_id

        return super(TravelDetailsSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        data = super(TravelDetailsSerializer, self).to_representation(instance)

        for travel_activity_data in data.get('activities', []):
            if travel_activity_data['primary_traveler'] == data.get('traveler', None):
                travel_activity_data['is_primary_traveler'] = True
            else:
                travel_activity_data['is_primary_traveler'] = False

        return data

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
        itineraryitems = self.create_related_models(ItineraryItem, itinerary, travel=instance)
        # ensure itineraryitems are ordered by `departure_date`
        order_itineraryitems(instance, itineraryitems)

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

            # TODO: remove this ugly stuff from here
            if issubclass(model, ActionPoint):
                data['assigned_by'] = self.context['request'].user

            related_instance = model.objects.create(**data)
            for field_name, value in m2m_fields.items():
                related_manager = getattr(related_instance, field_name)
                related_manager.add(*value)
            new_models.append(related_instance)
        return new_models

    def update(self, instance, validated_data, model_serializer=None):
        model_serializer = model_serializer or self

        related_attributes = {}
        related_fields = {n:f for n, f in model_serializer.get_fields().items()
                          if isinstance(f, serializers.BaseSerializer) and f.read_only == False}
        for attr_name in related_fields:
            if model_serializer.partial and attr_name not in validated_data:
                continue

            if isinstance(related_fields[attr_name], serializers.ListSerializer):
                default = []
            elif related_fields[attr_name].allow_null:
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
            to_remove = [r for r in related_manager.all() if r.id not in {r.id for r in value}]
            related_manager.remove(*to_remove)
            related_manager.add(*value)

    def update_related_objects(self, attr_name, related_data):
        many = isinstance(self._fields[attr_name], serializers.ListSerializer)

        try:
            related = getattr(self.instance, attr_name)
        except ObjectDoesNotExist:
            related = None

        if many:
            # Load the queryset
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

        # ensure itineraryitems are ordered by `departure_date`
        order_itineraryitems(self.instance, self.instance.itinerary.all())


class TravelListSerializer(TravelDetailsSerializer):
    # TODO: reserve field names to pks for related fields and add _name for the names
    traveler = serializers.CharField(source='traveler.get_full_name')
    supervisor_name = serializers.CharField(source='supervisor.get_full_name')

    class Meta:
        model = Travel
        fields = ('id', 'reference_number', 'traveler', 'purpose', 'status', 'section', 'office', 'start_date',
                  'end_date', 'supervisor_name')
        read_only_fields = ('status',)


class TravelActivityByPartnerSerializer(serializers.ModelSerializer):
    locations = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    primary_traveler = serializers.CharField(source='primary_traveler.get_full_name')
    reference_number = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.travels.first().status

    def get_reference_number(self, obj):
        return obj.travels.first().reference_number

    class Meta:
        model = TravelActivity
        fields = ("primary_traveler", "travel_type", "date", "locations", "reference_number", "status",)


class CloneOutputSerializer(TravelDetailsSerializer):
    class Meta:
        model = Travel
        fields = ('id',)


class CloneParameterSerializer(serializers.Serializer):
    traveler = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        fields = ('traveler',)
