from django.db import transaction
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_rest_export.serializers import ExportSerializer

from etools.applications.partners.models import Intervention
from etools.applications.reports.models import (
    AppliedIndicator,
    Disaggregation,
    DisaggregationValue,
    Indicator,
    IndicatorBlueprint,
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
        if obj.result_type.name == ResultType.OUTPUT:
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
        return IndicatorBlueprint.objects.get_or_create(**validated_data)[0]


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
        blueprint_data = attrs.get('indicator', getattr(self.instance, 'indicator', None))

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
                    'You cannot change the Indicator Target Denominator if PD/SSFA is '
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
                    'You cannot change the Indicator Target Denominator if PD/SSFA is '
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

        if self.partial:
            if not isinstance(blueprint_data, IndicatorBlueprint):
                raise ValidationError(
                    _('Indicator blueprint cannot be updated after first use, '
                      'please remove this indicator and add another or contact the eTools Focal Point in '
                      'your office for assistance')
                )

        elif not attrs.get('cluster_indicator_id'):
            indicator_blueprint = IndicatorBlueprintCUSerializer(data=blueprint_data)
            indicator_blueprint.is_valid(raise_exception=True)
            indicator_blueprint.save()

            attrs["indicator"] = indicator_blueprint.instance
            if lower_result.applied_indicators.filter(indicator__id=attrs['indicator'].id).exists():
                raise ValidationError(_('This indicator is already being monitored for this Result'))

        if lower_result.result_link.intervention.agreement.partner.blocked is True:
            raise ValidationError(_('The Indicators cannot be updated while the Partner is blocked in Vision'))
        return super().validate(attrs)

    def create(self, validated_data):
        return super().create(validated_data)


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
        fields = '__all__'


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
