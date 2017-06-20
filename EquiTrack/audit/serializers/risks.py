from __future__ import division

from django.db import models

from rest_framework import serializers

from audit.models import RiskCategory, RiskBluePrint, Risk
from utils.common.serializers.fields import WriteListSerializeFriendlyRecursiveField, RecursiveListSerializer
from utils.writable_serializers.serializers import WritableListSerializer, WritableNestedSerializerMixin


class RiskSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = Risk
        fields = [
            'value', 'extra',
        ]
        extra_kwargs = {
            'value': {
                'required': True,
            }
        }

    def get_attribute(self, instance):
        if instance.risks.exists():
            # It's work only if risks already filtered by engagement. See get_attribute method in RiskRootSerializer.
            return instance.risks.all()[0]
        else:
            return None


class RiskBlueprintNestedSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    risk = RiskSerializer()

    class Meta(WritableNestedSerializerMixin.Meta):
        model = RiskBluePrint
        fields = [
            'id', 'header', 'description', 'weight', 'is_key', 'risk',
        ]
        read_only_fields = [
            'header', 'description', 'weight', 'is_key',
        ]

    def update(self, instance, validated_data):
        if 'risk' in validated_data:
            data = validated_data.pop('risk')
            field = self.fields['risk']
            risk = field.get_attribute(instance)
            try:
                if risk:
                    field.update(risk, data)
                else:
                    data['engagement'] = self.context.get('instance', None)
                    data['blueprint'] = instance
                    field.create(data)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'risk': exc.detail})

        return super(RiskBlueprintNestedSerializer, self).update(instance, validated_data)


class RiskCategoryNestedSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    blueprints = WritableListSerializer(child=RiskBlueprintNestedSerializer(required=False), required=False)
    children = RecursiveListSerializer(child=WriteListSerializeFriendlyRecursiveField(required=False), required=False)

    risk_rating = serializers.CharField(read_only=True)
    risk_score = serializers.FloatField(read_only=True)
    total_number_risk_points = serializers.IntegerField(read_only=True)
    applicable_questions = serializers.IntegerField(read_only=True)
    applicable_key_questions = serializers.IntegerField(read_only=True)
    blueprint_count = serializers.IntegerField(read_only=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = RiskCategory
        fields = [
            'id', 'header', 'type', 'code',
            'risk_rating', 'risk_score',
            'total_number_risk_points',
            'applicable_questions',
            'applicable_key_questions',
            'blueprint_count',
            'blueprints', 'children', 'parent',
        ]
        read_only_fields = [
            'header', 'code', 'type', 'parent',
        ]


class RiskRootSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    blueprints = RiskBlueprintNestedSerializer(required=False, many=True)
    children = RiskCategoryNestedSerializer(many=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = RiskCategory
        fields = [
            'id', 'header', 'type', 'code',
            'blueprints', 'children', 'parent',
        ]
        read_only_fields = ['header', 'code', 'type', 'parent']

    def __init__(self, code, *args, **kwargs):
        self.code = code
        super(RiskRootSerializer, self).__init__(*args, **kwargs)

    def get_attribute(self, instance):
        categories = self.Meta.model.objects.filter(code=self.code).prefetch_related(
            'blueprints',
            models.Prefetch('blueprints__risks', Risk.objects.filter(engagement=instance))
        )

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
        root = parent_id_children_map[None][0]

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


class AggregatedRiskRootSerializer(RiskRootSerializer):
    risk_rating = serializers.CharField(read_only=True)
    risk_score = serializers.FloatField(read_only=True)
    total_number_risk_points = serializers.IntegerField(read_only=True)
    applicable_questions = serializers.IntegerField(read_only=True)
    applicable_key_questions = serializers.IntegerField(read_only=True)
    blueprint_count = serializers.IntegerField(read_only=True)

    class Meta(RiskRootSerializer.Meta):
        fields = RiskRootSerializer.Meta.fields + [
            'risk_rating', 'risk_score',
            'total_number_risk_points',
            'applicable_questions',
            'applicable_key_questions',
            'blueprint_count',
        ]

    def to_representation(self, instance):
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

        return super(RiskRootSerializer, self).to_representation(instance)

    @staticmethod
    def calculate_risk(category):
        for blueprint in category.blueprints.all():
            if blueprint.risks.all().exists():
                # It's work only if risks already filtered by engagement. See get_attribute method in RiskRootSerializer.
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

        category.applicable_questions = len(filter(lambda b: not b._risk or b._risk.risk_point, category.blueprints.all()))
        for child in category.children.all():
            category.applicable_questions += child.applicable_questions

        category.applicable_key_questions = len(filter(lambda b: b.is_key and (not b._risk or b._risk.risk_point), category.blueprints.all()))
        for child in category.children.all():
            category.applicable_key_questions += child.applicable_key_questions

        category.risk_points = sum(map(lambda b: b._risk.risk_point if b._risk else 0, category.blueprints.all()))
        for child in category.children.all():
            category.risk_points += child.risk_points
        category.total_number_risk_points = category.risk_points

        if category.applicable_questions:
            category.risk_score = category.risk_points / category.applicable_questions

            lowest_score_possible = 1
            highest_score_possible = (4*category.applicable_questions + 4*category.applicable_key_questions)/category.applicable_questions
            banding_width = (highest_score_possible-lowest_score_possible)/4
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
            category.risk_score = None
            category.risk_rating = 0
