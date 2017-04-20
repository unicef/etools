
from django.core.exceptions import ValidationError
from rest_framework import serializers

from partners.models import (
    PCA,
    InterventionBudget,
    SupplyPlan,
    DistributionPlan,
    InterventionAmendment,
)


class InterventionBudgetNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionBudget
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


class InterventionBudgetCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionBudget
        fields = "__all__"

    def validate(self, data):
        errors = {}
        try:
            data = super(InterventionBudgetCreateUpdateSerializer, self).validate(data)
        except ValidationError as e:
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


class InterventionAmendmentCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


class InterventionAmendmentNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionAmendment
        fields = (
            "amended_at",
            "type",
        )
