from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils.translation import gettext as _, gettext_lazy

from rest_framework import fields, serializers
from rest_framework.relations import RelatedField
from rest_framework.serializers import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.funds.models import FundsCommitmentItem, FundsReservationHeader
from etools.applications.funds.serializers import FRHeaderSerializer, FRsSerializer
from etools.applications.governments.models import (
    EWPActivity,
    GDD,
    GDDActivity,
    GDDActivityItem,
    GDDAttachment,
    GDDBudget,
    GDDKeyIntervention,
    GDDPlannedVisits,
    GDDPlannedVisitSite,
    GDDResultLink,
)
from etools.applications.governments.serializers.gdd_snapshot import FullGDDSnapshotSerializerMixin


class GDDActivityItemSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'invalid_budget': _('Invalid budget data. Total cash should be equal to items number * price per item.')
    }

    id = serializers.IntegerField(required=False)

    class Meta:
        model = GDDActivityItem
        fields = (
            'id',
            'code',
            'name',
            'unit',
            'unit_price',
            'no_units',
            'unicef_cash',
            # 'cso_cash',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        unit_price = attrs.get('unit_price', self.instance.unit_price if self.instance else 0)
        no_units = attrs.get('no_units', self.instance.no_units if self.instance else 0)
        unicef_cash = attrs.get('unicef_cash', self.instance.unicef_cash if self.instance else 0)
        # cso_cash = attrs.get('cso_cash', self.instance.cso_cash if self.instance else 0)

        # unit_price * no_units can contain more decimal places than we're able to save
        if abs((unit_price * no_units) - unicef_cash) > 0.01:
            self.fail('invalid_budget')

        return attrs


class GDDActivityItemBulkUpdateListSerializer(serializers.ListSerializer):
    """
    The purpose of this serializer is to wrap items update logic for activity
    yet having db queries optimized: reuse prefetched objects when it's possible + use bulk_create instead of each .save
    """
    @property
    def activity(self):
        return self.root.instance

    def get_instance(self, instance_id):
        assert hasattr(self.activity, '_prefetched_objects_cache'), 'items has to be prefetched for activity'
        assert 'items' in self.activity._prefetched_objects_cache, 'items has to be prefetched for activity'

        try:
            return [i for i in self.activity.items.all() if i.id == instance_id][0]
        except IndexError:
            raise ValidationError([_('Unable to find item for id: {}').format(instance_id)])

    def save(self, items, **kwargs):
        items = [
            {**attrs, **kwargs} for attrs in items
        ]

        pks_to_update = [item['id'] for item in items if 'id' in item]
        instances_to_create = []
        instances_to_update = {pk: self.get_instance(pk) for pk in pks_to_update}
        missing_pks_to_update = set(pks_to_update) - set(instances_to_update.keys())
        if missing_pks_to_update:
            raise ValidationError({'items': [_('Unable to find items: {}'.format(', '.join(missing_pks_to_update)))]})

        # items already validated, so we're free to use bulk operations instead of serializer.save
        for item in items:
            if 'id' in item:
                for key, value in item.items():
                    setattr(instances_to_update[item['id']], key, value)
            else:
                instances_to_create.append(GDDActivityItem(**item))

        fields_to_update = list(GDDActivityItemSerializer.Meta.fields)
        fields_to_update.remove('id')
        GDDActivityItem.objects.bulk_update(instances_to_update.values(), fields=fields_to_update)
        created_instances = GDDActivityItem.objects.bulk_create(instances_to_create)

        # cleanup, remove unused options
        updated_pks = list(instances_to_update.keys()) + [i.id for i in created_instances]
        removed_items = self.activity.items.exclude(pk__in=updated_pks).delete()
        if removed_items:
            # if items are removed, cash also should be recalculated
            self.activity.update_cash()
        GDDActivityItem.renumber_items_for_activity(self.activity)


class GDDActivityItemBulkUpdateSerializer(GDDActivityItemSerializer):
    class Meta(GDDActivityItemSerializer.Meta):
        list_serializer_class = GDDActivityItemBulkUpdateListSerializer

    @property
    def instance(self):
        """
        list serializer don't set instance for children directly, so we need to get it manually
        """
        if getattr(self, '_instance', None):
            return self._instance

        if 'id' not in self.initial_data:
            return None
        return self.parent.get_instance(self.initial_data['id'])

    @instance.setter
    def instance(self, value):
        """
        just dummy setter, to bypass `self.instance = None` step during initialization
        """
        self._instance = value

    def validate(self, attrs):
        # remember data to use for fetching instance
        self.initial_data = attrs
        return super().validate(attrs)


class GDDKeyInterventionSerializer(serializers.ModelSerializer):

    code = serializers.CharField(read_only=True)
    name = serializers.CharField(source='ewp_key_intervention.cp_key_intervention.name', read_only=True)

    class Meta:
        model = GDDKeyIntervention
        fields = [
            "id",
            "ewp_key_intervention",
            "code",
            "name",
            "result_link",
            "total",
            "created",
            "modified",
        ]


class GDDKeyInterventionCUSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)

    class Meta:
        model = GDDKeyIntervention
        fields = '__all__'


class GDDResultCUSerializer(serializers.ModelSerializer):

    gdd_key_interventions = GDDKeyInterventionSerializer(many=True, read_only=True)

    class Meta:
        model = GDDResultLink
        fields = "__all__"

    def update_gdd_key_interventions(self, instance, gdd_key_interventions):
        gdd_key_interventions = gdd_key_interventions if gdd_key_interventions else []

        for ki in gdd_key_interventions:
            ki['result_link'] = instance.pk
            instance_id = ki.get('id', None)
            if instance_id:
                try:
                    ki_instance = GDDKeyIntervention.objects.get(pk=instance_id)
                except GDDKeyIntervention.DoesNotExist:
                    raise ValidationError(_('lower_result has an id but cannot be found in the db'))

                ki_serializer = GDDKeyInterventionCUSerializer(
                    instance=ki_instance,
                    data=ki,
                    partial=True
                )

            else:
                ki_serializer = GDDKeyInterventionCUSerializer(data=ki)

            if ki_serializer.is_valid(raise_exception=True):
                ki_serializer.save()

    @transaction.atomic
    def create(self, validated_data):
        gdd_key_interventions = self.context.pop('gdd_key_interventions', [])
        instance = super().create(validated_data)
        self.update_gdd_key_interventions(instance, gdd_key_interventions)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        gdd_key_interventions = self.context.pop('gdd_key_interventions', [])
        self.update_gdd_key_interventions(instance, gdd_key_interventions)
        return super().update(instance, validated_data)


class EWPActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = EWPActivity
        fields = "__all__"


class GDDActivityCreateSerializer(
    FullGDDSnapshotSerializerMixin,
    serializers.ModelSerializer,
):
    items = GDDActivityItemBulkUpdateSerializer(many=True, required=False)

    class Meta:
        model = GDDActivity
        fields = (
            'id',
            'ewp_activity',
            'code',
            'created',
            'context_details',
            'unicef_cash',
            # 'cso_cash',
            'items',
            'time_frames',
            'is_active',
        )
        read_only_fields = ['code']

    def __init__(self, *args, **kwargs):
        self.gdd = kwargs.pop('gdd', None)
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance and self.partial and 'items' not in attrs and self.instance.items.exists():
            # when we do partial update for activity having items attached without items provided in request
            # it's easy to break total values, so we ignore them
            attrs.pop('unicef_cash', None)
            # attrs.pop('cso_cash', None)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # TODO: [e4] remove this whenever a better validation is decided on. This is out of place but needed as a hotfix
        if self.gdd.status in [self.gdd.SIGNATURE]:
            raise ValidationError(_("New activities are not able to be added in this status"))
        options = validated_data.pop('items', None)
        time_frames = validated_data.pop('time_frames', None)
        self.instance = super().create(validated_data)
        self.set_items(self.instance, options)
        self.set_time_frames(self.instance, time_frames)
        return self.instance

    @transaction.atomic
    def update(self, instance, validated_data):
        options = validated_data.pop('items', None)
        time_frames = validated_data.pop('time_frames', None)
        # TODO: [e4] remove this whenever a better validation is decided on. This is out of place but needed as a hotfix
        if self.gdd.status not in [self.gdd.SIGNATURE]:
            # if you're in status signature, ignore all other updates. This is horrible as the user can be confused
            # however it's a very limited amount of people that are able to make changes here and FE will inform them
            # otherwise would need to catch any intended changes as the FE currently re-submits existing fields
            self.instance = super().update(instance, validated_data)
            self.set_items(self.instance, options)
        self.set_time_frames(self.instance, time_frames)
        return self.instance

    def set_items(self, instance, items):
        if items is None:
            return
        self.fields['items'].save(items, activity=instance)

    def set_time_frames(self, instance, time_frames):
        if time_frames is None:
            return

        new_time_frames = self.gdd.quarters.filter(id__in=[t.id for t in time_frames])
        instance.time_frames.clear()
        instance.time_frames.add(*new_time_frames)

    def get_gdd(self):
        return self.gdd


class GDDActivityDetailSerializer(serializers.ModelSerializer):
    ewp_activity = EWPActivitySerializer()
    items = GDDActivityItemSerializer(many=True, required=False)

    class Meta:
        model = GDDActivity
        fields = (
            'id', 'ewp_activity', 'code', 'context_details',
            'unicef_cash', 'time_frames', 'is_active', 'created', 'items'
        )
        read_only_fields = ['code']


class GDDKeyInterventionWithActivitiesSerializer(GDDKeyInterventionSerializer):
    activities = GDDActivityDetailSerializer(read_only=True, many=True, source='gdd_activities')

    class Meta(GDDKeyInterventionSerializer.Meta):
        fields = GDDKeyInterventionSerializer.Meta.fields + ["activities"]


class BaseGDDResultNestedSerializer(serializers.ModelSerializer):
    cp_output_name = serializers.CharField(source="cp_output.cp_output.name", read_only=True)
    ram_indicator_names = serializers.SerializerMethodField(read_only=True)

    def get_ram_indicator_names(self, obj):
        return [i.light_repr for i in obj.ram_indicators.all()]

    class Meta:
        model = GDDResultLink
        fields = [
            'id',
            'created',
            'code',
            'gdd',
            'cp_output',
            'cp_output_name',
            'ram_indicators',
            'ram_indicator_names',
            'total',
        ]
        read_only_fields = ['code']


class GDDResultNestedSerializer(BaseGDDResultNestedSerializer):
    gdd_key_interventions = GDDKeyInterventionWithActivitiesSerializer(many=True, read_only=True)

    class Meta(BaseGDDResultNestedSerializer.Meta):
        fields = BaseGDDResultNestedSerializer.Meta.fields + ['gdd_key_interventions']


class GDDDetailResultsStructureSerializer(serializers.ModelSerializer):
    result_links = GDDResultNestedSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = GDD
        fields = (
            "result_links",
        )
