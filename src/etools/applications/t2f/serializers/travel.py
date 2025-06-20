import datetime
import operator
from itertools import chain

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields.related import ManyToManyField
from django.db.models.query_utils import Q
from django.utils.functional import cached_property
from django.utils.itercompat import is_iterable
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.serializers import ActionPointBaseSerializer
from etools.applications.locations.models import Location
from etools.applications.organizations.models import OrganizationType
from etools.applications.publics.models import AirlineCompany
from etools.applications.t2f.helpers.permission_matrix import PermissionMatrix
from etools.applications.t2f.models import ItineraryItem, Travel, TravelActivity, TravelAttachment, TravelType

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
        value = super().to_internal_value(data)
        return value.title()


class PermissionBasedModelSerializer(serializers.ModelSerializer):
    @cached_property
    def _writable_fields(self):
        fields = super()._writable_fields
        return [f for f in fields if self._can_write_field(f)]

    @cached_property
    def _readable_fields(self):
        fields = super()._readable_fields
        return [f for f in fields if self._can_read_field(f)]

    def _check_permission(self, permission_type, field_name):
        model_name = self.Meta.model.__name__.lower()

        permission_matrix = self.context.get('permission_matrix')

        if not permission_matrix:
            return True

        return permission_matrix.has_permission(permission_type, model_name, field_name)

    def _can_read_field(self, field):
        return self._check_permission(PermissionMatrix.VIEW, field.field_name)

    def _can_write_field(self, field):
        return self._check_permission(PermissionMatrix.EDIT, field.field_name)


class ItineraryItemSerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)
    airlines = serializers.PrimaryKeyRelatedField(many=True, queryset=AirlineCompany.admin_objects.all(),
                                                  required=False, allow_null=True)
    mode_of_travel = LowerTitleField(required=False)

    class Meta:
        model = ItineraryItem
        fields = ('id', 'origin', 'destination', 'departure_date', 'arrival_date', 'dsa_region', 'overnight_travel',
                  'mode_of_travel', 'airlines')


class TravelActivitySerializer(PermissionBasedModelSerializer):
    id = serializers.IntegerField(required=False)
    locations = serializers.PrimaryKeyRelatedField(many=True, queryset=Location.objects.all(), required=False,
                                                   allow_null=True)
    travel_type = LowerTitleField(required=False, allow_null=True)
    is_primary_traveler = serializers.BooleanField(required=False)
    primary_traveler = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        allow_null=True,
        required=False
    )
    action_points = ActionPointBaseSerializer(source='actionpoint_set', many=True, read_only=True, required=False)
    date = serializers.DateField(required=True)

    class Meta:
        model = TravelActivity
        fields = ('id', 'travel_type', 'partner', 'partnership', 'result', 'locations',
                  'primary_traveler', 'date', 'is_primary_traveler', 'action_points')

    def validate(self, attrs):
        if 'travel_type' in attrs and attrs['travel_type'] == TravelType.PROGRAMME_MONITORING or \
                'travel_type' not in attrs:
            raise ValidationError(
                "The capturing of Programmatic Visits in the Trip Management Module has been discontinued. "
                "Please use the Field Monitoring Module instead.")
        if 'id' not in attrs:
            if not attrs.get('is_primary_traveler'):
                if not attrs.get('primary_traveler'):
                    raise ValidationError({'primary_traveler': serializers.Field.default_error_messages['required']})
            if not attrs.get('date'):
                raise ValidationError({
                    'date': serializers.Field.default_error_messages['required']
                })

        partner = attrs.get('partner', getattr(self.instance, 'partner', None))
        travel_type = attrs.get('travel_type', getattr(self.instance, 'travel_type', None))

        if partner and partner.partner_type == OrganizationType.GOVERNMENT and \
                travel_type in [TravelType.SPOT_CHECK] and \
                'result' not in attrs:
            raise ValidationError({'result': serializers.Field.default_error_messages['required']})

        return attrs

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        ret.pop('is_primary_traveler', None)
        return ret


class TravelAttachmentSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    attachment = AttachmentSingleFileField()

    class Meta:
        model = TravelAttachment
        fields = ('id', 'name', 'type', 'url', 'file', 'attachment')

    def create(self, validated_data):
        validated_data['travel'] = self.context['travel']
        return super().create(validated_data)

    def get_url(self, obj):
        if obj.file:
            return obj.file.url
        return ""


class TravelDetailsSerializer(PermissionBasedModelSerializer):
    itinerary = ItineraryItemSerializer(many=True, required=False)
    activities = TravelActivitySerializer(many=True, required=False)
    attachments = TravelAttachmentSerializer(many=True, read_only=True, required=False)
    report = serializers.CharField(source='report_note', required=False, default='', allow_blank=True)
    mode_of_travel = serializers.ListField(child=LowerTitleField(), allow_null=True, required=False)

    # Fix because of a frontend validation failure (fix it on the frontend first)
    estimated_travel_cost = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)

    class Meta:
        model = Travel
        fields = ('reference_number', 'supervisor', 'office', 'end_date', 'international_travel', 'section',
                  'traveler', 'start_date', 'ta_required', 'purpose', 'id', 'itinerary',
                  'status', 'activities', 'mode_of_travel', 'estimated_travel_cost',
                  'currency', 'completed_at', 'canceled_at', 'rejection_note', 'cancellation_note', 'attachments',
                  'certification_note', 'report', 'additional_note', 'misc_expenses',
                  'first_submission_date')
        # Review this, as a developer could be confusing why the status field is not saved during an update
        read_only_fields = ('status', 'reference_number')

    def __init__(self, *args, **kwargs):
        data = kwargs.get('data', {})
        self.transition_name = data.get('transition_name', None)
        super().__init__(*args, **kwargs)

        ta_required = data.get('ta_required', False)
        if self.instance and not is_iterable(self.instance):
            ta_required |= self.instance.ta_required

    def validate_itinerary(self, value):
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

        current_date = next(dates_iterator)
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

        if self.transition_name in [Travel.SUBMIT_FOR_APPROVAL, Travel.APPROVED, Travel.COMPLETED]:
            traveler = attrs.get('traveler', None)
            if not traveler and self.instance:
                traveler = self.instance.traveler

            start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
            end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))

            if start_date and end_date:
                # All travels which shares the same traveller, not planned or cancelled and has start
                # or end date between the range of the start and end date of the current trip
                travel_q = Q(traveler=traveler)
                travel_q &= ~Q(status__in=[Travel.PLANNED, Travel.CANCELLED])
                travel_q &= Q(
                    start_date__range=(
                        start_date,
                        end_date - datetime.timedelta(days=1),
                    )
                ) | Q(
                    end_date__range=(
                        start_date + datetime.timedelta(days=1),
                        end_date,
                    )
                )

                # In case of first save, no id present
                if self.instance:
                    travel_q &= ~Q(id=self.instance.id)

                if Travel.objects.filter(travel_q).exists():
                    raise ValidationError(_('You have an existing trip with overlapping dates. '
                                            'Please adjust your trip accordingly.'))

        return super().validate(attrs)

    def to_internal_value(self, data):
        if self.instance:
            traveler_id = getattr(self.instance.traveler, 'id', None)
        else:
            traveler_id = None

        traveler_id = data.get('traveler', traveler_id)

        for travel_activity_data in data.get('activities', []):
            if travel_activity_data.get('is_primary_traveler'):
                travel_activity_data['primary_traveler'] = traveler_id

        # Align start and end dates based on itinerary
        if data.get('itinerary', []):
            data = self.align_dates_to_itinerary(data)

        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        for travel_activity_data in data.get('activities', []):
            if travel_activity_data['primary_traveler'] == data.get('traveler', None):
                travel_activity_data['is_primary_traveler'] = True
            else:
                travel_activity_data['is_primary_traveler'] = False

        return data

    def align_dates_to_itinerary(self, data):
        """Updates travel start and end date based on itineraries"""
        itinerary = data.get('itinerary', [])
        departures = []
        arrivals = []
        for item in itinerary:
            departures.append(item['departure_date'])
            arrivals.append(item['arrival_date'])

        data['start_date'] = min(departures)
        data['end_date'] = max(arrivals)

        return data

    # -------- Create and update methods --------
    def create(self, validated_data):
        itinerary = validated_data.pop('itinerary', [])
        activities = validated_data.pop('activities', [])
        action_points = validated_data.pop('action_points', [])

        instance = super().create(validated_data)

        # Reverse FK and M2M relations
        itineraryitems = self.create_related_models(ItineraryItem, itinerary, travel=instance)
        # ensure itineraryitems are ordered by `departure_date`
        order_itineraryitems(instance, itineraryitems)
        self.create_related_models(ActionPoint, action_points, travel=instance)
        travel_activities = self.create_related_models(TravelActivity, activities)
        for activity in travel_activities:
            activity.travels.add(instance)

        return instance

    def create_related_models(self, model, related_data, **kwargs):
        new_models = []
        for data in related_data:
            data = dict(data)
            m2m_fields = {k: data.pop(k, []) for k in list(data.keys())
                          if isinstance(model._meta.get_field(k), ManyToManyField)}
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
        related_fields = {n: f for n, f in model_serializer.get_fields().items()
                          if isinstance(f, serializers.BaseSerializer) and f.read_only is False}
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
        m2m_fields = {k: data.pop(k, []) for k in list(data.keys())
                      if isinstance(obj._meta.get_field(k), ManyToManyField)}
        for attr, value in data.items():
            setattr(obj, attr, value)
        obj.save()

        for field_name, value in m2m_fields.items():
            related_manager = getattr(obj, field_name)
            to_remove = [r for r in related_manager.all() if r.id not in {r.id for r in value}]
            related_manager.remove(*to_remove)
            related_manager.add(*value)

    def update_related_objects(self, attr_name, related_data):
        many = isinstance(self.fields[attr_name], serializers.ListSerializer)

        try:
            related = getattr(self.instance, attr_name)
        except ObjectDoesNotExist:
            related = None

        if many:
            # Load the queryset
            related = related.all()

            model = self.fields[attr_name].child.Meta.model
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
                    except (TypeError, AttributeError):
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
    traveler = serializers.CharField(source='traveler.get_full_name', allow_null=True)
    supervisor_name = serializers.CharField(source='supervisor.get_full_name', allow_null=True)

    class Meta:
        model = Travel
        fields = ('id', 'reference_number', 'traveler', 'purpose', 'status', 'office', 'start_date', 'section',
                  'end_date', 'supervisor_name')
        read_only_fields = ('status',)


class TravelActivityByPartnerSerializer(serializers.ModelSerializer):
    locations = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    primary_traveler = serializers.CharField(source='primary_traveler.get_full_name')
    reference_number = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()
    trip_id = serializers.ReadOnlyField()
    travel_latest_date = serializers.SerializerMethodField()

    def get_travel_latest_date(self, obj):
        return getattr(obj.travels.filter(traveler=obj.primary_traveler).last(), 'end_date', '-')

    class Meta:
        model = TravelActivity
        fields = ('travel_latest_date', 'primary_traveler', 'travel_type', 'date', 'locations', 'reference_number',
                  'status', 'trip_id')


class CloneOutputSerializer(TravelDetailsSerializer):
    class Meta:
        model = Travel
        fields = ('id',)


class CloneParameterSerializer(serializers.Serializer):
    traveler = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())

    class Meta:
        fields = ('traveler',)
