import json
from operator import xor

from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import serializers

from partners.models import (
    PCA,
    Agreement,
    PartnershipBudget,
    SupplyPlan,
    DistributionPlan,
    AmendmentLog,
    PCASector,
)
from partners.serializers.v1 import PCASectorSerializer, DistributionPlanSerializer


# Reference Number - DONE
# PD/SSFA Type - DONE
# Partner Full Name - DONE
# Status - DONE
# Title - DONE
# Start Date - DONE
# End Date - DONE
#    in the drop-down
# HRP, blank if null
# Sectors - DONE
# Total CSO Contribution (USD) - DONE
# Total UNICEF Budget (USD) - DONE


class InterventionListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name')
    pcasector_set = PCASectorSerializer(many=True, read_only=True)
    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')

    class Meta:
        model = PCA
        fields = (
            'id', 'reference_number', 'partnership_type', 'partner_name', 'status', 'title', 'start_date', 'end_date',
            'pcasector_set', 'unicef_budget', 'cso_contribution',
        )


class PartnershipBudgetNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnershipBudget
        fields = (
            "partner_contribution",
            "unicef_cash",
            "in_kind_amount",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "year",
            "total",
        )


class PartnershipBudgetCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnershipBudget
        fields = "__all__"

    def validate(self, data):
        errors = {}
        try:
            data = super(PartnershipBudgetCreateUpdateSerializer, self).validate(data)
        except ValidationError, e:
            errors.update(e)

        status = data.get("status", "")
        year = data.get("year", "")
        if not year and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(year="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        partner_contribution = data.get("partner_contribution", "")
        if not partner_contribution and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(partner_contribution="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        unicef_cash = data.get("unicef_cash", "")
        if not unicef_cash and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(unicef_cash="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        if errors:
            raise serializers.ValidationError(errors)

        return data


class PCASectorCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PCASector
        fields = "__all__"


class PCASectorNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = PCASector
        fields = (
            "sector",
        )


class SupplyPlanCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupplyPlan
        fields = "__all__"


class SupplyPlanNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupplyPlan
        fields = (
            "item",
            "quantity",
        )


class DistributionPlanCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DistributionPlan
        fields = "__all__"


class DistributionPlanNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = DistributionPlan
        fields = (
            "item",
            "quantity",
            "site",
        )


class AmendmentLogCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = AmendmentLog
        fields = "__all__"


class AmendmentLogNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = AmendmentLog
        fields = (
            "amended_at",
            "type",
        )


class InterventionCreateUpdateSerializer(serializers.ModelSerializer):

    # TODO
    # Locations? m2m?
    # Humanitarian response plan? equals resultstructure?
    # Planned visits: which field is writable? Whats partner risk rating and audit?
    # Fr number is charfield, is that ok?
    budget_log = PartnershipBudgetNestedSerializer(many=True)
    supply_plans = SupplyPlanNestedSerializer(many=True, required=False)
    distribution_plans = DistributionPlanNestedSerializer(many=True, required=False)
    amendments_log = AmendmentLogNestedSerializer(many=True, required=False)
    pcasectors = PCASectorNestedSerializer(many=True, required=False)

    class Meta:
        model = PCA
        fields = (
            "id", "partner", "agreement", "partnership_type", "result_structure", "number",
            "title", "project_type", "status", "start_date", "end_date", "initiation_date",
            "submission_date", "review_date", "signed_by_unicef_date", "signed_by_partner_date",
            "unicef_manager", "unicef_managers", "programme_focal_points", "partner_manager",
            "partner_focal_point", "office", "fr_number", "planned_visits", "population_focus",
            "sectors", "current", "created_at", "updated_at", "budget_log", "supply_plans",
            "distribution_plans", "amendments_log", "pcasectors",
        )
        read_only_fields = ("id",)

    @transaction.atomic
    def create(self, validated_data):
        planned_budgets = validated_data.pop("budget_log", [])
        supply_plans = validated_data.pop("supply_plans", [])
        distribution_plans = validated_data.pop("distribution_plans", [])
        amendments_log = validated_data.pop("amendments_log", [])
        pcasectors = validated_data.pop("pcasectors", [])

        intervention = super(InterventionCreateUpdateSerializer, self).create(validated_data)

        for item in pcasectors:
            item["pca"] = intervention.id
            item["sector"] = item["sector"].id
            serializer = PCASectorCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in planned_budgets:
            item["partnership"] = intervention.id
            serializer = PartnershipBudgetCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in supply_plans:
            item["partnership"] = intervention.id
            item["item"] = item["item"].id
            serializer = SupplyPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in distribution_plans:
            item["partnership"] = intervention.id
            item["item"] = item["item"].id
            item["site"] = item["site"].id
            serializer = DistributionPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in amendments_log:
            item["partnership"] = intervention.id
            serializer = AmendmentLogCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return intervention

    @transaction.atomic
    def update(self, instance, validated_data):
        pcasectors = validated_data.pop("pcasectors", [])
        budget_log = validated_data.pop("budget_log", [])
        supply_plans = validated_data.pop("supply_plans", [])
        distribution_plans = validated_data.pop("distribution_plans", [])
        amendments_log = validated_data.pop("amendments_log", [])

        updated = super(InterventionCreateUpdateSerializer, self).update(instance, validated_data)

        # Sectors
        ids = [x["id"] for x in pcasectors if "id" in x.keys()]
        for item in instance.pcasectors.all():
            if item.id not in ids:
                item.delete()

        for item in pcasectors:
            item["pca"] = instance.id
            item["sector"] = item["sector"].id
            serializer = PCASectorCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Budget Log
        ids = [x["id"] for x in budget_log if "id" in x.keys()]
        for item in instance.budget_log.all():
            if item.id not in ids:
                item.delete()

        for item in budget_log:
            item["partnership"] = instance.id
            serializer = PartnershipBudgetCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Supply Plan
        ids = [x["id"] for x in supply_plans if "id" in x.keys()]
        for item in instance.supply_plans.all():
            if item.id not in ids:
                item.delete()

        for item in supply_plans:
            item["partnership"] = instance.id
            item["item"] = item["item"].id
            serializer = SupplyPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Distribution Plan
        ids = [x["id"] for x in distribution_plans if "id" in x.keys()]
        for item in instance.distribution_plans.all():
            if item.id not in ids:
                item.delete()

        for item in distribution_plans:
            item["partnership"] = instance.id
            item["item"] = item["item"].id
            item["site"] = item["site"].id
            serializer = DistributionPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Amendments log
        ids = [x["id"] for x in amendments_log if "id" in x.keys()]
        for item in instance.amendments_log.all():
            if item.id not in ids:
                item.delete()

        for item in amendments_log:
            item["partnership"] = instance.id
            serializer = AmendmentLogCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return updated

    def validate(self, data):
        errors = {}
        try:
            data = super(InterventionCreateUpdateSerializer, self).validate(data)
        except ValidationError, e:
            errors.update(e)

        partnership_type_errors = []
        partnership_type = data.get("partnership_type", "")
        agreement = data.get("agreement", "")
        if not partnership_type:
            partnership_type_errors.append("This field is required.")
        if agreement.agreement_type == Agreement.PCA and partnership_type not in [PCA.PD, PCA.SHPD]:
            partnership_type_errors.append("This field must be PD or SHPD in case of agreement is PCA.")
        if agreement.agreement_type == Agreement.SSFA and partnership_type != PCA.SSFA:
            partnership_type_errors.append("This field must be SSFA in case of agreement is SSFA.")
        if partnership_type_errors:
            errors.update(partnership_type=partnership_type_errors)

        office = data.get("office", "")
        if not office:
            errors.update(office="This field is required.")

        programme_focal_points = data.get("programme_focal_points", "")
        status = data.get("status", "")
        if not programme_focal_points and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(programme_focal_points="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        unicef_managers = data.get("unicef_managers", "")
        if not unicef_managers and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(unicef_managers="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        partner_focal_point = data.get("partner_focal_point", "")
        if not partner_focal_point and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(partner_focal_point="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        if xor(bool(data.get("signed_by_partner_date", None)), bool(data.get("partner_manager", None))):
            errors.update(partner_manager=["partner_manager and signed_by_partner_date must be provided."])
            errors.update(signed_by_partner_date=["signed_by_partner_date and partner_manager must be provided."])

        if xor(bool(data.get("signed_by_unicef_date", None)), bool(data.get("unicef_manager", None))):
            errors.update(unicef_manager=["unicef_manager and signed_by_unicef_date must be provided."])
            errors.update(signed_by_unicef_date=["signed_by_unicef_date and unicef_manager must be provided."])

        start_date_errors = []
        start_date = data.get("start_date", None)
        signed_by_unicef_date = data.get("signed_by_unicef_date", None)
        signed_by_partner_date = data.get("signed_by_partner_date", None)
        if not start_date and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            start_date_errors.append("This field is required.")
        if start_date and (signed_by_unicef_date or signed_by_partner_date) and \
                start_date < max(signed_by_unicef_date, signed_by_partner_date):
            start_date_errors.append("Start date must be after the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date).")
        if start_date_errors:
            errors.update(start_date=start_date_errors)

        end_date_errors = []
        end_date = data.get("end_date", None)
        if not end_date and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            end_date_errors.append("This field is required.")
        if end_date and start_date and end_date < start_date:
            end_date_errors.append("End date must be after the start date.")
        if end_date_errors:
            errors.update(end_date=end_date_errors)

        population_focus = data.get("population_focus", "")
        if not population_focus and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(population_focus="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        pcasectors = data.get("pcasectors", "")
        if not pcasectors and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(pcasectors="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        if errors:
            raise serializers.ValidationError(errors)

        return data


class InterventionDetailSerializer(serializers.ModelSerializer):

    # TODO
    # Humanitarian response plan
    # Locations
    # Budget log
    # Planned visits

    pca_id = serializers.CharField(source='id', read_only=True)
    pca_title = serializers.CharField(source='title')
    pca_number = serializers.CharField(source='reference_number')
    partner_name = serializers.CharField(source='partner.name')
    partner_id = serializers.CharField(source='partner.id')
    pcasector_set = PCASectorSerializer(many=True, read_only=True)
    distribution_plans = DistributionPlanSerializer(many=True, read_only=True)
    total_budget = serializers.CharField(read_only=True)

    class Meta:
        model = PCA
        fields = '__all__'


# to be done
# CP Outputs
# RAM Indicators


# FR Number(s)
# Fund Commitment(s)

# how to calculate local currency
# Local Currency of Planned Budget
# Total UNICEF Budget (Local)
# Total CSO Budget (Local)

# Planned Programmatic Visits
# Planned Spot Checks
# Planned Audits

# Supply Plan
# Distribution Plan
# URL

class InterventionExportSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name')
    pcasector_set = PCASectorSerializer(many=True, read_only=True)
    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')
    result_structure_name = serializers.CharField(source='result_structure.name')
    agreement_name = serializers.CharField(source='agreement.name')
    locations = serializers.SerializerMethodField()
    unicef_focal_points = serializers.CharField(source='unicef_managers.name')
    cso_authorized_officials = serializers.CharField(source='partner_focal_point.first_name')
    programme_focals = serializers.CharField(source='programme_focal_points.name')

    class Meta:
        model = PCA
        fields = ('status', 'partner_name', 'partnership_type', 'number',  'title', 'start_date', 'end_date',
                  'pcasector_set', 'result_structure_name',  'unicef_budget', 'cso_contribution', 'agreement_name',
                  'office', 'locations', 'unicef_focal_points', 'programme_focal_points', 'population_focus',
                  'initiation_date', 'submission_date', 'review_date', 'partner_manager', 'signed_by_partner_date',
                  'unicef_manager', 'signed_by_unicef_date', 'days_from_submission_to_signed',
                  'days_from_review_to_signed', 'fr_numbers'
                  )

    def get_locations(self, obj):
        return ', '.join([' - '.join(l.location.name, l.location.p_code) for l in obj.locations.all() if l.location])
