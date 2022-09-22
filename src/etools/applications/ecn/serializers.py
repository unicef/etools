from django.db import transaction

from rest_framework import serializers

from etools.applications.locations.models import Location
from etools.applications.partners.models import (
    Agreement,
    Intervention,
    InterventionBudget,
    InterventionManagementBudget,
    InterventionManagementBudgetItem,
    InterventionResultLink,
    InterventionRisk,
    InterventionSupplyItem,
)
from etools.applications.reports.models import (
    AppliedIndicator,
    IndicatorBlueprint,
    InterventionActivity,
    InterventionActivityItem,
    LowerResult,
    Section,
)


class InterventionRiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionRisk
        fields = [
            'risk_type',
            'mitigation_measures',
        ]


class InterventionSupplyItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionSupplyItem
        fields = [
            'title',
            'unit_number',
            'unit_price',
            'other_mentions',
            'provided_by',
            'unicef_product_number',
        ]


class InterventionBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionBudget
        fields = (
            "currency",
            "total_hq_cash_local",
        )


class InterventionManagementBudgetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionManagementBudgetItem
        fields = (
            'kind', 'name',
            'unit', 'unit_price', 'no_units',
            'unicef_cash', 'cso_cash'
        )


class InterventionManagementBudgetSerializer(serializers.ModelSerializer):
    items = InterventionManagementBudgetItemSerializer(many=True)

    class Meta:
        model = InterventionManagementBudget
        fields = (
            "items",
            "act1_unicef",
            "act1_partner",
            "act2_unicef",
            "act2_partner",
            "act3_unicef",
            "act3_partner",
        )

    def update(self, instance, validated_data):
        items = validated_data.pop('items')
        instance = super().update(instance, validated_data)
        self.set_items(instance, items)
        return instance

    def set_items(self, budget, items):
        serializer = InterventionManagementBudgetItemSerializer(many=True, data=items)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(budget=budget)
        # redo logic to bulk_create in case of performance issues
        # doing update in serializer instead of post_save to avoid big number of budget re-calculations
        # budget.update_cash()


class InterventionActivityItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionActivityItem
        fields = (
            'name',
            'unit',
            'unit_price',
            'no_units',
            'unicef_cash',
            'cso_cash',
        )


class InterventionActivitySerializer(serializers.ModelSerializer):
    items = InterventionActivityItemSerializer(many=True)
    time_frames = serializers.ListSerializer(child=serializers.IntegerField())

    class Meta:
        model = InterventionActivity
        fields = (
            'name', 'context_details',
            'unicef_cash', 'cso_cash',
            'time_frames', 'items',
        )

    def create(self, validated_data):
        items = validated_data.pop('items')
        time_frames = validated_data.pop('time_frames')
        instance = super().create(validated_data)
        self.set_items(instance, items)
        self.set_time_frames(instance, time_frames)
        return instance

    def set_items(self, activity, items):
        serializer = InterventionActivityItemSerializer(many=True, data=items)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(activity=activity)

    def set_time_frames(self, activity, time_frames):
        quarters = activity.result.result_link.intervention.quarters.filter(quarter__in=time_frames)
        activity.time_frames.add(*quarters)


class IndicatorBlueprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorBlueprint
        fields = [
            'title',
            'unit',
            'description',
            'code',
            'subdomain',
            'disaggregatable',
            'calculation_formula_across_periods',
            'calculation_formula_across_locations',
            'display_type',
        ]


class AppliedIndicatorSerializer(serializers.ModelSerializer):
    indicator = IndicatorBlueprintSerializer()
    target = serializers.JSONField()
    baseline = serializers.JSONField()

    class Meta:
        model = AppliedIndicator
        fields = [
            'indicator',
            'measurement_specifications',
            'label',
            'numerator_label',
            'denominator_label',
            'context_code',
            'target',
            'baseline',
            'assumptions',
            'means_of_verification',
            'total',
            'is_high_frequency',
            'is_active',
        ]

    def create(self, validated_data):
        indicator_data = validated_data.pop('indicator')

        # give priority to blueprints linked with current lower result
        blueprint = IndicatorBlueprint.objects.filter(
            appliedindicator__lower_result=self.parent.instance,
            **indicator_data,
        ).first()

        if not blueprint:
            indicator_blueprint_serializer = IndicatorBlueprintSerializer(data=indicator_data)
            indicator_blueprint_serializer.is_valid(raise_exception=True)
            indicator_blueprint_serializer.save()
            blueprint = indicator_blueprint_serializer.instance

        validated_data['indicator'] = blueprint
        # save section & locations manually, because PrimaryKeyRelatedField casts value to instance and then fails
        validated_data['section'] = self.root.instance.sections.first()
        validated_data['locations'] = self.root.instance.flat_locations.all()

        return super().create(validated_data)


class LowerResultSerializer(serializers.ModelSerializer):
    activities = InterventionActivitySerializer(many=True)
    applied_indicators = AppliedIndicatorSerializer(many=True)

    class Meta:
        model = LowerResult
        fields = [
            "name",
            "activities",
            "applied_indicators",
        ]

    def create(self, validated_data):
        activities = validated_data.pop('activities')
        applied_indicators = validated_data.pop('applied_indicators')
        instance = super().create(validated_data)
        self.create_activities(instance, activities)
        self.create_applied_indicators(instance, applied_indicators)
        return instance

    def create_activities(self, result, activities):
        serializer = InterventionActivitySerializer(many=True, data=activities)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(result=result)

    def create_applied_indicators(self, result, applied_indicators):
        serializer = AppliedIndicatorSerializer(many=True, data=applied_indicators)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(lower_result=result)


class InterventionResultLinkSerializer(serializers.ModelSerializer):
    ll_results = LowerResultSerializer(many=True)

    class Meta:
        model = InterventionResultLink
        fields = ['ll_results']

    def create(self, validated_data):
        ll_results = validated_data.pop('ll_results')
        instance = super().create(validated_data)
        self.create_ll_results(instance, ll_results)
        return instance

    def create_ll_results(self, result_link, ll_results):
        serializer = LowerResultSerializer(many=True, data=ll_results)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(result_link=result_link)


class InterventionSerializer(serializers.ModelSerializer):
    planned_budget = InterventionBudgetSerializer()
    management_budgets = InterventionManagementBudgetSerializer()
    result_links = InterventionResultLinkSerializer(many=True)
    risks = InterventionRiskSerializer(many=True)
    supply_items = InterventionSupplyItemSerializer(many=True)
    locations = serializers.CharField()

    class Meta:
        model = Intervention
        fields = [
            'planned_budget',
            'result_links',
            'risks',
            'supply_items',
            'management_budgets',
            'title',
            'start', 'end',
            'context', 'implementation_strategy',
            'capacity_development', 'other_info', 'other_partners_involved',
            'gender_rating', 'gender_narrative',
            'equity_rating', 'equity_narrative',
            'sustainability_rating', 'sustainability_narrative',
            'ip_program_contribution', 'reference_number_year',
            'locations', 'sections'
        ]

    def create_risks(self, intervention, data):
        serializer = InterventionRiskSerializer(many=True, data=data)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(intervention=intervention)

    def create_supply_items(self, intervention, data):
        serializer = InterventionSupplyItemSerializer(many=True, data=data)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(intervention=intervention)

    def update_planned_budget(self, intervention, data):
        serializer = InterventionBudgetSerializer(data=data, instance=intervention.planned_budget)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def update_management_budgets(self, intervention, data):
        serializer = InterventionManagementBudgetSerializer(data=data, instance=intervention.management_budgets)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save()

    def create_result_links_structure(self, intervention, data):
        serializer = InterventionResultLinkSerializer(many=True, data=data)
        serializer.parent = self
        serializer.is_valid(raise_exception=True)
        serializer.save(intervention=intervention)

    @transaction.atomic
    def create(self, validated_data):
        risks = validated_data.pop('risks')
        supply_items = validated_data.pop('supply_items')
        planned_budget = validated_data.pop('planned_budget')
        management_budgets = validated_data.pop('management_budgets')
        result_links = validated_data.pop('result_links')

        locations = validated_data.pop('locations')
        if validated_data['other_info']:
            validated_data['other_info'] += '\n\n'
            validated_data['other_info'] += f'Locations: {locations}'
        else:
            validated_data['other_info'] = f'Locations: {locations}'
        validated_data['other_info'] += f'\n\nSection {validated_data["sections"][0]} was added to all indicators, ' \
                                        f'please review and correct if needed.'
        validated_data['other_info'] += '\n\nAll indicators were assigned all locations, please adjust as needed.'

        self.instance = super().create(validated_data)

        self.create_risks(self.instance, risks)
        self.create_supply_items(self.instance, supply_items)
        self.update_planned_budget(self.instance, planned_budget)
        self.update_management_budgets(self.instance, management_budgets)
        self.create_result_links_structure(self.instance, result_links)

        return self.instance


class ECNSyncSerializer(serializers.Serializer):
    number = serializers.CharField()
    agreement = serializers.PrimaryKeyRelatedField(queryset=Agreement.objects.all())
    sections = serializers.PrimaryKeyRelatedField(many=True, queryset=Section.objects.all())
    locations = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), many=True)

    class Meta:
        fields = ['number', 'agreement', 'section', 'locations']
