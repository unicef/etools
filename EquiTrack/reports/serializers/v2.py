from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from reports.models import Result, AppliedIndicator, IndicatorBlueprint, LowerResult, \
    Disaggregation, DisaggregationValue


class DisaggregationValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisaggregationValue
        fields = ('value', 'active', )


class DisaggregationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Disaggregation (i.e. the feature on which data is being disaggregated).

    This is a nested writable serializer based on:
    http://www.django-rest-framework.org/api-guide/relations/#writable-nested-serializers
    """
    disaggregation_values = DisaggregationValueSerializer(many=True)

    class Meta:
        model = Disaggregation
        fields = ('name', 'active', 'disaggregation_values', )

    def create(self, validated_data):
        values_data = validated_data.pop('disaggregation_values')
        disaggregation = Disaggregation.objects.create(**validated_data)
        for value_data in values_data:
            DisaggregationValue.objects.create(disaggregation=disaggregation, **value_data)
        return disaggregation


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


class AppliedIndicatorSerializer(serializers.ModelSerializer):

    indicator = IndicatorBlueprintCUSerializer(required=False)

    class Meta:
        model = AppliedIndicator
        extra_kwargs = {
            'indicator': {'validators': []},
        }
        fields = '__all__'

    def validate(self, attrs):
        lower_result = attrs.get('lower_result')
        blueprint_data = attrs.get('indicator')
        if self.partial:
            if not isinstance(blueprint_data, IndicatorBlueprint):
                raise ValidationError(
                    'Indicator blueprint cannot be updated after first use, '
                    'please remove this indicator and add another or contact the eTools Focal Point in '
                    'your office for assistance'
                )

        elif not attrs.get('cluster_indicator_id'):
            print "no cluster id"
            indicator_blueprint = IndicatorBlueprintCUSerializer(data=blueprint_data)
            indicator_blueprint.is_valid(raise_exception=True)
            indicator_blueprint.save()

            attrs["indicator"] = indicator_blueprint.instance
            if lower_result.applied_indicators.filter(indicator__id=attrs['indicator'].id).exists():
                raise ValidationError('This indicator is already being monitored for this Result')

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
