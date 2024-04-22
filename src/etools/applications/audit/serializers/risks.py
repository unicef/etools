import itertools

from django.db import models
from django.utils.translation import gettext as _

from rest_framework import serializers
from unicef_restlib.fields import WriteListSerializeFriendlyRecursiveField
from unicef_restlib.serializers import RecursiveListSerializer, WritableListSerializer, WritableNestedSerializerMixin

from etools.applications.audit.models import Risk, RiskBluePrint, RiskCategory
from etools.libraries.pythonlib.collections import to_choices_list


class BaseRiskSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    value = serializers.ChoiceField(choices=to_choices_list(Risk.VALUES), required=True)
    value_display = serializers.SerializerMethodField()

    class Meta(WritableNestedSerializerMixin.Meta):
        model = Risk
        fields = [
            'value', 'value_display', 'extra',
        ]

    def get_value_display(self, obj):
        return self.fields['value'].choices.get(obj.value)

    def validate_extra(self, value):
        if isinstance(value, str):
            raise serializers.ValidationError('Invalid data type.')
        return value


class RiskSerializer(BaseRiskSerializer):
    class Meta(BaseRiskSerializer.Meta):
        fields = ['id'] + BaseRiskSerializer.Meta.fields


class RiskSingletoneSerializer(BaseRiskSerializer):
    class Meta(BaseRiskSerializer.Meta):
        pass

    def get_attribute(self, instance):
        if instance.risks.exists():
            # It's work only if risks already filtered by engagement. See get_attribute method in RiskRootSerializer.
            return instance.risks.all()[0]
        else:
            return None


class RiskBlueprintNestedSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    """
    Risk blueprint connected with risk value for certain engagement instance.
    """
    risk = RiskSingletoneSerializer(label=_('Risk Assessment'))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = RiskBluePrint
        fields = [
            'id', 'header', 'description', 'weight', 'is_key', 'risk',
        ]
        read_only_fields = [
            'header', 'description', 'weight', 'is_key',
        ]

    def update(self, instance, validated_data):
        """
        Updating engagement risk value for selected blueprint.
        """
        if 'risk' in validated_data:
            data = validated_data.pop('risk')
            field = self.fields['risk']
            risk = field.get_attribute(instance)
            try:
                if risk:
                    field.update(risk, data)
                else:
                    data['engagement'] = self.root.instance
                    data['blueprint'] = instance
                    field.create(data)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'risk': exc.detail})

        return super().update(instance, validated_data)


class ManyRiskBlueprintNestedSerializer(RiskBlueprintNestedSerializer):
    """
    Risk blueprint connected with many risk values for certain engagement instance.
    """

    risks = RiskSerializer(label=_('Risk Assessment'), many=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = RiskBluePrint
        fields = [
            'id', 'header', 'description', 'weight', 'is_key', 'risks',
        ]
        read_only_fields = [
            'header', 'description', 'weight', 'is_key',
        ]

    def update(self, instance, validated_data):
        """
        Updating engagement risk value for selected blueprint.
        """
        if 'risks' in validated_data:
            for risk in validated_data['risks']:
                risk['engagement'] = self.root.instance
                risk['blueprint'] = instance

        return super().update(instance, validated_data)


class RiskCategoryNestedSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    """
    Nested recursive serializer for risk category.
    """

    blueprints = WritableListSerializer(child=RiskBlueprintNestedSerializer(required=False), required=False)
    children = RecursiveListSerializer(child=WriteListSerializeFriendlyRecursiveField(required=False), required=False)

    # Aggregated values wouldn't exists in result data if calculate_risk wasn't called in root serializer.
    risk_rating = serializers.CharField(read_only=True)
    risk_score = serializers.FloatField(read_only=True)
    total_number_risk_points = serializers.IntegerField(read_only=True)
    applicable_questions = serializers.IntegerField(read_only=True)
    applicable_key_questions = serializers.IntegerField(read_only=True)
    blueprint_count = serializers.IntegerField(read_only=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = RiskCategory
        fields = [
            'id', 'header', 'category_type', 'code',
            'risk_rating', 'risk_score',
            'total_number_risk_points',
            'applicable_questions',
            'applicable_key_questions',
            'blueprint_count',
            'blueprints', 'children', 'parent',
        ]
        read_only_fields = [
            'header', 'code', 'category_type', 'parent',
        ]


class ManyRiskCategoryNestedSerializer(RiskCategoryNestedSerializer):
    blueprints = WritableListSerializer(child=ManyRiskBlueprintNestedSerializer(required=False), required=False)

    class Meta(RiskCategoryNestedSerializer.Meta):
        pass


class RiskRootSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    """
    Root serializer for recursive risks categories. Contain questions and values together for easier usage.
    """

    blueprints = RiskBlueprintNestedSerializer(required=False, many=True)
    children = RiskCategoryNestedSerializer(many=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = RiskCategory
        fields = [
            'id', 'header', 'category_type', 'code',
            'blueprints', 'children', 'parent',
        ]
        read_only_fields = ['header', 'code', 'category_type', 'parent']

    def __init__(self, code, *args, **kwargs):
        self.code = code
        self.risk_choices = kwargs.pop('risk_choices', None)

        super().__init__(*args, **kwargs)

        if self.risk_choices:
            blueprint_fields = self.fields['blueprints'].child.fields
            if 'risk' in blueprint_fields:
                blueprint_fields['risk'].fields['value'].choices = to_choices_list(self.risk_choices)
            if 'risks' in blueprint_fields:
                blueprint_fields['risks'].child.fields['value'].choices = to_choices_list(self.risk_choices)

    def get_code(self, instance):
        if callable(self.code):
            return self.code(instance)
        return self.code

    def get_attribute(self, instance):
        """
        Collect categories tree with connected blueprints and risks related to engagement.
        This allows us to avoid passing instance deeper for filtering risks.
        """
        categories = self.Meta.model.objects.filter(code=self.get_code(instance)).prefetch_related(
            'blueprints',
            models.Prefetch('blueprints__risks', Risk.objects.filter(engagement=instance))
        )

        # {'cat_parent_pk': [cat_child_1, cat_child_2], 'cat_parent2_pk': [cat_child2_1], None: [root]}
        parent_id_children_map = dict()
        for category in categories:
            children = parent_id_children_map.get(category.parent_id, None)
            if children is None:
                children = list()
                parent_id_children_map[category.parent_id] = children

            children.append(category)

        # Root doesn't have parent
        if None not in parent_id_children_map:
            return None
        root = parent_id_children_map[None][0]  # top level category

        # Breadth-first search
        queue = [root]
        while queue:
            category = queue.pop(0)
            children = parent_id_children_map.get(category.id, [])

            # Set relation between categories
            for child in children:
                child.parent = category
            category._prefetched_objects_cache['children'] = children

            if children:
                queue.extend(children)

        return root


class BaseAggregatedRiskRootSerializer(RiskRootSerializer):
    def to_representation(self, instance):
        """
        Processing nested categories to collect aggregates.
        """
        # Depth-first search
        stack = [instance]
        while stack:
            category = stack[-1]

            if not getattr(category, '_processed', False):
                stack.extend(category.children.all())
                category._processed = True
                continue

            self.calculate_risk(category)

            stack.pop()

        return super().to_representation(instance)

    @staticmethod
    def calculate_risk(category):
        raise NotImplementedError()


class KeyInternalWeaknessSerializer(BaseAggregatedRiskRootSerializer):
    """
    Risk root serializer with additional aggregated data for audit.
    """
    blueprints = ManyRiskBlueprintNestedSerializer(required=False, many=True)
    children = ManyRiskCategoryNestedSerializer(many=True)

    high_risk_count = serializers.IntegerField(label=_('High risk'), read_only=True)
    medium_risk_count = serializers.IntegerField(label=_('Medium risk'), read_only=True)
    low_risk_count = serializers.IntegerField(label=_('Low risk'), read_only=True)

    @staticmethod
    def _get_bluerprint_count_by_risk_value(category, field_name, risk_value):
        values_count = len([
            risk for risk in itertools.chain(*[
                blueprint.risks.all()
                for blueprint in category.blueprints.all()
            ])
            if risk.value == risk_value
        ])

        setattr(category, field_name, values_count)

        for child in category.children.all():
            setattr(category, field_name, getattr(category, field_name, 0) + getattr(child, field_name, 0))

    @staticmethod
    def calculate_risk(category):
        KeyInternalWeaknessSerializer._get_bluerprint_count_by_risk_value(
            category, 'high_risk_count', Risk.VALUES.high
        )
        KeyInternalWeaknessSerializer._get_bluerprint_count_by_risk_value(
            category, 'medium_risk_count', Risk.VALUES.medium
        )
        KeyInternalWeaknessSerializer._get_bluerprint_count_by_risk_value(
            category, 'low_risk_count', Risk.VALUES.low
        )

    class Meta(BaseAggregatedRiskRootSerializer.Meta):
        fields = BaseAggregatedRiskRootSerializer.Meta.fields + [
            'high_risk_count', 'medium_risk_count', 'low_risk_count',
        ]


class AggregatedRiskRootSerializer(BaseAggregatedRiskRootSerializer):
    """
    Risk root serializer with additional aggregated data.
    """

    risk_rating = serializers.CharField(read_only=True)
    risk_score = serializers.FloatField(read_only=True)
    total_number_risk_points = serializers.IntegerField(read_only=True)
    applicable_questions = serializers.IntegerField(read_only=True)
    applicable_key_questions = serializers.IntegerField(read_only=True)
    blueprint_count = serializers.IntegerField(read_only=True)

    class Meta(BaseAggregatedRiskRootSerializer.Meta):
        fields = BaseAggregatedRiskRootSerializer.Meta.fields + [
            'risk_rating', 'risk_score',
            'total_number_risk_points',
            'applicable_questions',
            'applicable_key_questions',
            'blueprint_count',
        ]

    @staticmethod
    def calculate_risk(category):
        """
        Calculate aggregated values for category.
        :param category: RiskCategory instance with filtered risks by engagement.
        """
        for blueprint in category.blueprints.all():
            if blueprint.risks.all().exists():
                # It's work only if risks already filtered by engagement. See get_attribute method in RiskRootSerializer
                blueprint._risk = blueprint.risks.all()[0]
                if blueprint._risk.value == 1:
                    blueprint._risk.risk_point = blueprint._risk.value
                else:
                    blueprint._risk.risk_point = blueprint.weight * blueprint._risk.value
            else:
                blueprint._risk = None

        category.blueprint_count = len(category.blueprints.all())
        for child in category.children.all():
            category.blueprint_count += child.blueprint_count

        category.applicable_questions = len(
            [b for b in category.blueprints.all() if not b._risk or b._risk.risk_point]
        )
        for child in category.children.all():
            category.applicable_questions += child.applicable_questions

        category.applicable_key_questions = len(
            [b for b in category.blueprints.all() if b.is_key and (not b._risk or b._risk.risk_point)]
        )
        for child in category.children.all():
            category.applicable_key_questions += child.applicable_key_questions

        category.risk_points = sum([
            b._risk.risk_point if b._risk else 0
            for b in category.blueprints.all()
        ])
        for child in category.children.all():
            category.risk_points += child.risk_points
        category.total_number_risk_points = category.risk_points

        if category.applicable_questions:
            category.risk_score = category.risk_points / category.applicable_questions

            if category.code in ['ma_questionnaire', 'ma_subject_areas']:
                # v1 calculations
                lowest_score_possible = 1
                highest_score_possible = (4 * category.applicable_questions + 4 * category.applicable_key_questions)
                highest_score_possible = highest_score_possible / category.applicable_questions
                banding_width = (highest_score_possible - lowest_score_possible) / 4
                low_scores_below = lowest_score_possible + banding_width
                moderate_scores_below = low_scores_below + banding_width
                significant_score_below = moderate_scores_below + banding_width

                category.risk_rating = 0
                if category.risk_score < low_scores_below:
                    category.risk_rating = 'low'
                elif category.risk_score < moderate_scores_below:
                    category.risk_rating = 'medium'
                elif category.risk_score < significant_score_below:
                    category.risk_rating = 'significant'
                else:
                    category.risk_rating = 'high'
            else:
                # v2 calculations
                lowest_score_possible = category.applicable_questions
                highest_score_possible = 4 * lowest_score_possible
                banding_width = highest_score_possible - lowest_score_possible
                low_points_below = lowest_score_possible + banding_width * 0.15
                moderate_points_below = lowest_score_possible + banding_width * 0.3
                significant_points_below = lowest_score_possible + banding_width * 0.5

                if category.risk_points < low_points_below:
                    category.risk_rating = 'low'
                elif category.risk_points < moderate_points_below:
                    category.risk_rating = 'medium'
                elif category.risk_points < significant_points_below:
                    category.risk_rating = 'significant'
                else:
                    category.risk_rating = 'high'
        else:
            category.risk_score = None
            category.risk_rating = 0
