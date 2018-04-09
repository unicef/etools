from operator import itemgetter

from django.db import transaction
from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from reports.models import (
    AppliedIndicator,
    Disaggregation,
    DisaggregationValue,
    Indicator,
    IndicatorBlueprint,
    LowerResult,
    ReportingRequirement,
    Result,
)


class OutputListSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="output_name")
    result_type = serializers.SlugRelatedField(slug_field="name", read_only=True)
    expired = serializers.ReadOnlyField()
    special = serializers.ReadOnlyField()

    class Meta:
        model = Result
        fields = '__all__'


class MinimalOutputListSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="output_name")

    class Meta:
        model = Result
        fields = (
            "id",
            "name"
        )


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
        validated_data['title'] = validated_data['title'].title()
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
                        for k, v in value_data.items():
                            setattr(value, k, v)
                        value.save()
                    except DisaggregationValue.DoesNotExist:
                        raise ValidationError(
                            "Tried to modify DisaggregationValue {} that is not associated with {}".format(
                                value_id, instance,
                            )
                        )
                else:
                    # if you're adding a new disaggregation value, add it here
                    value = DisaggregationValue.objects.create(disaggregation=instance, **value_data)
                    found_values.append(value.id)
            # delete any values that weren't specified in the update request.
            instance.disaggregation_values.exclude(id__in=found_values).delete()
        return super(DisaggregationSerializer, self).update(instance, validated_data)


class AppliedIndicatorSerializer(serializers.ModelSerializer):

    indicator = IndicatorBlueprintCUSerializer(required=False, allow_null=True)

    class Meta:
        model = AppliedIndicator
        extra_kwargs = {
            'indicator': {'validators': []},
        }
        fields = '__all__'

    def validate(self, attrs):
        lower_result = attrs.get('lower_result')
        blueprint_data = attrs.get('indicator')

        # make sure locations are in the intervention
        locations = set(l.id for l in attrs.get('locations', []))
        if not locations.issubset(l.id for l in lower_result.result_link.intervention.flat_locations.all()):
            raise ValidationError(_('This indicator can only have locations that were '
                                    'previously saved on the intervention'))

        # make sure section are in the intervention
        section = attrs.get('section', None)
        if section is None:
            raise ValidationError(_('Section is required'))
        if section.id not in [s.id for s in lower_result.result_link.intervention.sections.all()]:
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

        return super(AppliedIndicatorSerializer, self).validate(attrs)

    def create(self, validated_data):
        return super(AppliedIndicatorSerializer, self).create(validated_data)


class AppliedIndicatorCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppliedIndicator
        fields = '__all__'


class LowerResultSimpleCUSerializer(serializers.ModelSerializer):

    code = serializers.CharField(read_only=True)

    def update(self, instance, validated_data):
        new_result_link = validated_data.get('result_link')
        if new_result_link.pk != instance.result_link.pk:
            raise ValidationError("You can't associate this PD Output to a different CP Result")

        return super(LowerResultSimpleCUSerializer, self).update(instance, validated_data)

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
                    indicator_serializer = AppliedIndicatorCUSerializer(
                        instance=indicator_instance,
                        data=indicator,
                        partial=True
                    )
                except AppliedIndicator.DoesNotExist:
                    raise ValidationError('Indicator has an ID but could not be found in the db')

            else:
                indicator_serializer = AppliedIndicatorCUSerializer(
                    data=indicator
                )

            if indicator_serializer.is_valid(raise_exception=True):
                indicator_serializer.save()

    @transaction.atomic
    def create(self, validated_data):
        applied_indicators = self.context.pop('applied_indicators', [])
        instance = super(LowerResultCUSerializer, self).create(validated_data)
        self.update_applied_indicators(instance, applied_indicators)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        applied_indicators = self.context.pop('applied_indicators', [])

        self.update_applied_indicators(instance, applied_indicators)

        return super(LowerResultCUSerializer, self).update(instance, validated_data)


class IndicatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Indicator
        fields = "__all__"


class ReportingRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingRequirement
        fields = ("id", "start_date", "end_date", "due_date", )


class IndicatorReportingRequirementSerializer(serializers.ModelSerializer):
    report_type = serializers.ChoiceField(
        choices=ReportingRequirement.TYPE_CHOICES
    )
    reporting_requirements = ReportingRequirementSerializer(many=True)

    class Meta:
        model = AppliedIndicator
        fields = ("id", "reporting_requirements", "report_type", )
        read_only_fields = ("id", )

    def _validate_qpr(self, intervention, reqs):
        # Ensure that the first reporting requirement start date
        # is on or after PD start date
        if reqs[0]["start_date"] < intervention.start:
            raise serializers.ValidationError({
                "reporting_requirements": {
                    "start_date": _(
                        "Start date needs to be on or after PD start date."
                    )
                }
            })

        # Ensure start date is after previous end date
        for i in range(1, len(reqs)):
            if reqs[i]["start_date"] <= reqs[i-1]["end_date"]:
                raise serializers.ValidationError({
                    "reporting_requirements": {
                        "start_date": _(
                            "Start date needs to be after previous end date."
                        )
                    }
                })

    def _validate_hr(self, indicator, intervention, reqs):
        # Ensure intervention is HF or cluster
        if not indicator.is_high_frequency and not indicator.cluster_indicator_id:
            raise serializers.ValidationError(
                _("Indicator needs to be either cluster or high frequency.")
            )

    def run_validation(self, initial_data):
        serializer = self.fields["reporting_requirements"].child
        report_type = initial_data.get("report_type")
        if report_type == ReportingRequirement.TYPE_HR:
            serializer.fields["start_date"].required = False
            serializer.fields["end_date"].required = False
        return super().run_validation(initial_data)

    def validate(self, data):
        """The first reporting requirement's start date needs to be
        on or after the PD start date.
        Subsequent reporting requirements start date needs to be after the
        previous reporting requirement end date.
        """
        pk = self.initial_data.get("id")
        try:
            indicator = self.Meta.model.objects.get(pk=pk)
        except self.Meta.model.DoesNotExist:
            raise serializers.ValidationError({
                "id": _("Invalid indicator id.")
            })

        # Only able to change reporting requirements when PD
        # is in amendment status
        intervention = indicator.lower_result.result_link.intervention
        if intervention.status not in [intervention.DRAFT]:
            raise serializers.ValidationError(
                _("Changes not allowed when PD not in amendment state.")
            )
        if not intervention.start:
            raise serializers.ValidationError(
                _("PD needs to have a start date.")
            )

        # Validate reporting requirements first
        if not len(data["reporting_requirements"]):
            raise serializers.ValidationError({
                "reporting_requirements": _("This field cannot be empty.")
            })

        current_reqs = ReportingRequirement.objects.values_list(
            "id",
            "start_date",
            "end_date",
            "due_date",
        ).filter(
            applied_indicator__pk=pk,
            report_type=data["report_type"],
        )
        # We need all reporting requirements in end date order
        merged_reqs = list(current_reqs) + data["reporting_requirements"]

        if data["report_type"] == ReportingRequirement.TYPE_QPR:
            reqs = sorted(merged_reqs, key=itemgetter("end_date"))
            self._validate_qpr(intervention, reqs)
        elif data["report_type"] == ReportingRequirement.TYPE_HR:
            reqs = sorted(merged_reqs, key=itemgetter("due_date"))
            self._validate_hr(indicator, intervention, reqs)

        return data
