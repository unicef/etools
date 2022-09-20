from django.db import transaction
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_rest_export.serializers import ExportSerializer

from etools.applications.partners.models import Intervention
from etools.applications.partners.serializers.intervention_snapshot import FullInterventionSnapshotSerializerMixin
from etools.applications.reports.models import (
    AppliedIndicator,
    Disaggregation,
    DisaggregationValue,
    Indicator,
    IndicatorBlueprint,
    InterventionActivity,
    InterventionActivityItem,
    InterventionTimeFrame,
    LowerResult,
    Office,
    ReportingRequirement,
    Result,
    ResultType,
    SpecialReportingRequirement,
)
from etools.applications.reports.validators import (
    SpecialReportingRequirementUniqueValidator,
    value_none_or_numbers,
    value_numbers,
)


class MinimalOutputListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Result
        fields = (
            "id",
            "name"
        )

    def get_name(self, obj):
        if obj.result_type == ResultType.OUTPUT:
            return obj.output_name
        else:
            return obj.result_name


class OutputListSerializer(MinimalOutputListSerializer):
    result_type = serializers.SlugRelatedField(slug_field="name", read_only=True)
    expired = serializers.ReadOnlyField()
    special = serializers.ReadOnlyField()

    class Meta(MinimalOutputListSerializer.Meta):
        fields = '__all__'


class IndicatorBlueprintCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = IndicatorBlueprint
        fields = '__all__'
        # remove the unique validator as we're doing a get_por_create
        extra_kwargs = {
            'code': {'validators': []},
        }

    def create(self, validated_data):
        # always try to get first
        indicator = IndicatorBlueprint.objects.filter(**validated_data).first()
        if not indicator:
            indicator = super().create(validated_data)
        return indicator


class IndicatorBlueprintUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorBlueprint
        fields = ('id', 'title')


class DisaggregationValueSerializer(serializers.ModelSerializer):
    # this is here explicitly to allow for passing IDs as nested values in the update function
    # https://stackoverflow.com/a/37275096/8207
    id = serializers.IntegerField(required=False)

    class Meta:
        model = DisaggregationValue
        fields = ('id', 'value', 'active',)


class DisaggregationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Disaggregation (i.e. the feature on which data is being disaggregated).

    This is a nested writable serializer based on:
    http://www.django-rest-framework.org/api-guide/relations/#writable-nested-serializers
    """

    disaggregation_values = DisaggregationValueSerializer(many=True)

    class Meta:
        model = Disaggregation
        fields = ('id', 'name', 'active', 'disaggregation_values', )

    def create(self, validated_data):
        values_data = validated_data.pop('disaggregation_values')
        if not values_data or len(values_data) == 1:
            raise ValidationError('At least 2 Disaggregation Groups must be set.')
        disaggregation = Disaggregation.objects.create(**validated_data)
        for value_data in values_data:
            if 'id' in value_data:
                raise ValidationError(
                    "You are not allowed to specify DisaggregationValues IDs when creating a new Disaggregation"
                )
            DisaggregationValue.objects.create(disaggregation=disaggregation, **value_data)
        return disaggregation

    def update(self, instance, validated_data):
        if instance.applied_indicators.count():
            raise ValidationError(
                'You cannot update a Disaggregation that is already associated with an Indicator.'
            )
        try:
            # get values data http://www.django-rest-framework.org/api-guide/serializers/#dynamically-modifying-fields
            values_data = validated_data.pop('disaggregation_values')
        except KeyError:
            pass
        else:
            # If you're trying to change some of the values you initially entered or remove some selected values
            found_values = []
            for value_data in values_data:
                value_id = value_data.get('id', None)
                # if you're changing an existing value, update the value manually
                if value_id:
                    found_values.append(value_id)
                    try:
                        value = DisaggregationValue.objects.get(disaggregation=instance, id=value_id)
                    except DisaggregationValue.DoesNotExist:
                        raise ValidationError(
                            "Tried to modify DisaggregationValue {} that is not associated with {}".format(
                                value_id, instance,
                            )
                        )
                    else:
                        for k, v in value_data.items():
                            setattr(value, k, v)
                        value.save()
                else:
                    # if you're adding a new disaggregation value, add it here
                    value = DisaggregationValue.objects.create(disaggregation=instance, **value_data)
                    found_values.append(value.id)
            # delete any values that weren't specified in the update request.
            instance.disaggregation_values.exclude(id__in=found_values).delete()
        return super().update(instance, validated_data)


class AppliedIndicatorSerializer(serializers.ModelSerializer):

    indicator = IndicatorBlueprintCUSerializer(required=False, allow_null=True)
    target = serializers.JSONField(required=False, validators=[value_numbers])
    baseline = serializers.JSONField(required=False, validators=[value_none_or_numbers])

    class Meta:
        model = AppliedIndicator
        extra_kwargs = {
            'indicator': {'validators': []},
        }
        fields = '__all__'

    def validate(self, attrs):
        lower_result = attrs.get('lower_result', getattr(self.instance, 'lower_result', None))

        # allowed to change target "v" denominator only if intervention is draft or signed
        # or active and in amendment mode
        # allowed to change target "d" denominator only if intervention is draft or signed
        status = lower_result.result_link.intervention.status
        in_amendment = lower_result.result_link.intervention.in_amendment
        if attrs.get('target') and self.instance:
            if attrs['target']['v'] != self.instance.target_display[1] \
               and not (status in [Intervention.DRAFT, Intervention.SIGNED] or
                        (status == Intervention.ACTIVE and in_amendment)):
                raise ValidationError(_(
                    'You cannot change the Indicator Target Denominator if PD/SPD is '
                    'not in status Draft or Signed'
                ))
            if attrs['target']['d'] != self.instance.target_display[1] and not (
                    status in [Intervention.DRAFT, Intervention.SIGNED] or (
                        status == Intervention.ACTIVE and in_amendment and
                        (
                            self.instance.indicator and
                            self.instance.indicator.display_type != IndicatorBlueprint.RATIO
                        )
                    )
            ):
                raise ValidationError(_(
                    'You cannot change the Indicator Target Denominator if PD/SPD is '
                    'not in status Draft or Signed'
                ))

        # make sure locations are in the intervention
        locations = set(loc.id for loc in attrs.get('locations', []))
        if not locations.issubset(
                l_result.id for l_result in lower_result.result_link.intervention.flat_locations.all()
        ):
            raise ValidationError(_('This indicator can only have locations that were '
                                    'previously saved on the intervention'))

        # make sure section are in the intervention
        section = attrs.get('section', None)
        if section is None and self.context.get('request').method != 'PATCH':
            raise ValidationError(_('Section is required'))
        if section is not None \
                and section.id not in [s.id for s in lower_result.result_link.intervention.sections.all()]:
            raise ValidationError(_('This indicator can only have a section that was '
                                    'previously saved on the intervention'))

        if lower_result.result_link.intervention.agreement.partner.blocked is True:
            raise ValidationError(_('The Indicators cannot be updated while the Partner is blocked in Vision'))
        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data):
        if 'indicator' in validated_data and not validated_data.get('cluster_indicator_id'):
            lower_result = validated_data['lower_result']
            indicator_data = validated_data.pop('indicator')

            # give priority to blueprints linked with current lower result
            blueprint = IndicatorBlueprint.objects.filter(
                appliedindicator__lower_result=lower_result,
                **indicator_data,
            ).first()

            if not blueprint:
                indicator_blueprint_serializer = IndicatorBlueprintCUSerializer(data=indicator_data)
                indicator_blueprint_serializer.is_valid(raise_exception=True)
                indicator_blueprint_serializer.save()
                blueprint = indicator_blueprint_serializer.instance

            validated_data['indicator'] = blueprint

            if lower_result.applied_indicators.filter(indicator__id=blueprint.id).exists():
                raise ValidationError({
                    'non_field_errors': [_('This indicator is already being monitored for this Result')],
                })

        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        if validated_data.get('indicator') and self.partial and instance.indicator:
            indicator_data = validated_data.pop('indicator')

            # if instance was signed, it was reported to PRP. it means we cannot just edit blueprint
            # and only option is to deactivate previous indicator as inactive
            instance_copy = instance.make_copy()

            intervention = instance.lower_result.result_link.intervention
            was_active_before = intervention.was_active_before()
            in_amendment = intervention.in_amendment
            if was_active_before or in_amendment:
                instance.is_active = False
                instance.save()
            else:
                instance.delete()

            instance = instance_copy

            blueprint_serializer = IndicatorBlueprintUpdateSerializer(instance=instance.indicator, data=indicator_data)
            blueprint_serializer.is_valid(raise_exception=True)
            blueprint_serializer.save()

        return super().update(instance, validated_data)


class AppliedIndicatorCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppliedIndicator
        fields = '__all__'


class AppliedIndicatorBasicSerializer(serializers.ModelSerializer):
    title = serializers.ReadOnlyField(source='indicator.title')

    class Meta:
        model = AppliedIndicator
        fields = ('pk', 'title', 'section')


class ClusterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppliedIndicator
        fields = 'cluster_name',


class LowerResultSimpleCUSerializer(serializers.ModelSerializer):

    code = serializers.CharField(read_only=True)

    def update(self, instance, validated_data):
        new_result_link = validated_data.get('result_link', instance.result_link)
        if new_result_link.pk != instance.result_link.pk:
            raise ValidationError("You can't associate this PD Output to a different CP Result")
        if new_result_link and new_result_link.intervention.agreement.partner.blocked is True:
            raise ValidationError("A PD Output cannot be updated for a partner that is blocked in Vision")

        return super().update(instance, validated_data)

    def create(self, validated_data):
        result_link = validated_data.get('result_link')
        if result_link and result_link.intervention.agreement.partner.blocked is True:
            raise ValidationError("A PD Output cannot be created for a partner that is blocked in Vision")
        return super().create(validated_data)

    class Meta:
        model = LowerResult
        fields = '__all__'


class LowerResultSerializer(serializers.ModelSerializer):

    applied_indicators = AppliedIndicatorSerializer(many=True, read_only=True)
    code = serializers.CharField(read_only=True)

    class Meta:
        model = LowerResult
        fields = [
            "id",
            "name",
            "code",
            "result_link",
            "total",
            "applied_indicators",
            "created",
            "modified",
        ]


class LowerResultCUSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)

    class Meta:
        model = LowerResult
        fields = '__all__'

    def handle_blueprint(self, indicator):

        blueprint_instance, created = IndicatorBlueprint.objects.get_or_create(
            title=indicator.pop('name', None),
            unit=indicator.pop('unit', None),
            # for now all indicator blueprints will be considered dissagregatable
            disaggregatable=True
        )

        return blueprint_instance.pk

    def update_applied_indicators(self, instance, applied_indicators):

        for indicator in applied_indicators:
            indicator['lower_result'] = instance.pk

            indicator['indicator'] = self.handle_blueprint(indicator)

            indicator_id = indicator.get('id')
            if indicator_id:
                try:
                    indicator_instance = AppliedIndicator.objects.get(pk=indicator_id)
                except AppliedIndicator.DoesNotExist:
                    raise ValidationError('Indicator has an ID but could not be found in the db')
                else:
                    indicator_serializer = AppliedIndicatorCUSerializer(
                        instance=indicator_instance,
                        data=indicator,
                        partial=True
                    )

            else:
                indicator_serializer = AppliedIndicatorCUSerializer(
                    data=indicator
                )

            if indicator_serializer.is_valid(raise_exception=True):
                indicator_serializer.save()

    @transaction.atomic
    def create(self, validated_data):
        applied_indicators = self.context.pop('applied_indicators', [])
        instance = super().create(validated_data)
        self.update_applied_indicators(instance, applied_indicators)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        applied_indicators = self.context.pop('applied_indicators', [])

        self.update_applied_indicators(instance, applied_indicators)

        return super().update(instance, validated_data)


class IndicatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Indicator
        fields = "__all__"


class RAMIndicatorSerializer(serializers.ModelSerializer):
    indicator_name = serializers.SerializerMethodField()

    def get_indicator_name(self, obj):
        return obj.light_repr

    class Meta:
        model = Indicator
        fields = ("indicator_name",)


class ReportingRequirementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ReportingRequirement
        fields = ("id", "start_date", "end_date", "due_date", )


class SpecialReportingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialReportingRequirement
        fields = "__all__"
        validators = [
            SpecialReportingRequirementUniqueValidator(
                queryset=SpecialReportingRequirement.objects.all(),
            )
        ]


class ResultFrameworkSerializer(serializers.Serializer):
    result = serializers.SerializerMethodField(label=_("Result"))
    indicators = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    baseline = serializers.SerializerMethodField()
    means_of_verification = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()

    class Meta:
        fields = (
            "result",
            "indicators",
            "locations",
            "baseline",
            "target",
            "means_of_verification",
        )

    def get_result(self, obj):
        if hasattr(obj, "cp_output"):
            return obj.cp_output
        return obj.lower_result

    def get_indicators(self, obj):
        if hasattr(obj, "ram_indicators"):
            return "\n".join([
                i.name for i in obj.ram_indicators.all()
                if i.name
            ])
        return obj.indicator.title

    def get_target(self, obj):
        if hasattr(obj, "target"):
            return obj.target_display
        return ""

    def get_baseline(self, obj):
        if hasattr(obj, "baseline"):
            return obj.baseline_display
        return ""

    def get_means_of_verification(self, obj):
        if hasattr(obj, "means_of_verification"):
            return obj.means_of_verification
        return ""

    def get_locations(self, obj):
        if hasattr(obj, "locations"):
            return "\n".join(set([loc.name for loc in obj.locations.all()]))
        return ""


class ResultFrameworkExportSerializer(ExportSerializer):
    pass


class OfficeLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = ('id', 'name')


class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = "__all__"


class InterventionActivityItemSerializer(serializers.ModelSerializer):
    default_error_messages = {
        'invalid_budget': _('Invalid budget data. Total cash should be equal to items number * price per item.')
    }

    id = serializers.IntegerField(required=False)

    class Meta:
        model = InterventionActivityItem
        fields = (
            'id',
            'code',
            'name',
            'unit',
            'unit_price',
            'no_units',
            'unicef_cash',
            'cso_cash',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        unit_price = attrs.get('unit_price', self.instance.unit_price if self.instance else None)
        no_units = attrs.get('no_units', self.instance.no_units if self.instance else None)
        unicef_cash = attrs.get('unicef_cash', self.instance.unicef_cash if self.instance else None)
        cso_cash = attrs.get('cso_cash', self.instance.cso_cash if self.instance else None)

        # unit_price * no_units can contain more decimal places than we're able to save
        if abs((unit_price * no_units) - (unicef_cash + cso_cash)) > 0.01:
            self.fail('invalid_budget')

        return attrs


class InterventionActivityItemBulkUpdateListSerializer(serializers.ListSerializer):
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
                instances_to_create.append(InterventionActivityItem(**item))

        fields_to_update = list(InterventionActivityItemSerializer.Meta.fields)
        fields_to_update.remove('id')
        InterventionActivityItem.objects.bulk_update(instances_to_update.values(), fields=fields_to_update)
        created_instances = InterventionActivityItem.objects.bulk_create(instances_to_create)

        # cleanup, remove unused options
        updated_pks = list(instances_to_update.keys()) + [i.id for i in created_instances]
        removed_items = self.activity.items.exclude(pk__in=updated_pks).delete()
        if removed_items:
            # if items are removed, cash also should be recalculated
            self.activity.update_cash()
        InterventionActivityItem.renumber_items_for_activity(self.activity)


class InterventionActivityItemBulkUpdateSerializer(InterventionActivityItemSerializer):
    class Meta(InterventionActivityItemSerializer.Meta):
        list_serializer_class = InterventionActivityItemBulkUpdateListSerializer

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


class InterventionTimeFrameSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    start = serializers.DateField(source='start_date')
    end = serializers.DateField(source='end_date')

    class Meta:
        model = InterventionTimeFrame
        fields = ('id', 'name', 'start', 'end',)

    def get_name(self, obj: InterventionTimeFrame):
        return 'Q{}'.format(obj.quarter)


class InterventionActivityDetailSerializer(FullInterventionSnapshotSerializerMixin, serializers.ModelSerializer):
    items = InterventionActivityItemBulkUpdateSerializer(many=True, required=False)
    partner_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = InterventionActivity
        fields = (
            'id',
            'name',
            'code',
            'created',
            'context_details',
            'unicef_cash',
            'cso_cash',
            'items',
            'time_frames',
            'partner_percentage',
            'is_active',
        )
        read_only_fields = ['code']

    def __init__(self, *args, **kwargs):
        self.intervention = kwargs.pop('intervention', None)
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance and self.partial and 'items' not in attrs and self.instance.items.exists():
            # when we do partial update for activity having items attached without items provided in request
            # it's easy to break total values, so we ignore them
            attrs.pop('unicef_cash', None)
            attrs.pop('cso_cash', None)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
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

        new_time_frames = self.intervention.quarters.filter(id__in=[t.id for t in time_frames])
        instance.time_frames.clear()
        instance.time_frames.add(*new_time_frames)

    def get_intervention(self):
        return self.intervention


class InterventionActivitySerializer(serializers.ModelSerializer):
    partner_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = InterventionActivity
        fields = (
            'id', 'name', 'code', 'context_details',
            'unicef_cash', 'cso_cash', 'partner_percentage',
            'time_frames', 'is_active', 'created',
        )
        read_only_fields = ['code']


class LowerResultWithActivitiesSerializer(LowerResultSerializer):
    activities = InterventionActivitySerializer(read_only=True, many=True)

    class Meta(LowerResultSerializer.Meta):
        fields = LowerResultSerializer.Meta.fields + ["activities"]


class LowerResultWithActivityItemsSerializer(LowerResultSerializer):
    activities = InterventionActivityDetailSerializer(read_only=True, many=True)

    class Meta(LowerResultSerializer.Meta):
        fields = LowerResultSerializer.Meta.fields + ["activities"]
