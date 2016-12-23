import json
from operator import xor

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from reports.serializers import IndicatorSerializer, OutputSerializer
from partners.serializers.v1 import (
    PartnerOrganizationSerializer,
    PartnerStaffMemberEmbedSerializer,
    InterventionSerializer,
)
from locations.models import Location

from partners.models import (
    PCA,
    PartnershipBudget,
    SupplyPlan,
    DistributionPlan,
    PlannedVisits,
    Intervention,
    InterventionAmendment,
    PartnerOrganization,
    PartnerType,
    Agreement,
    PartnerStaffMember,

)
from partners.serializers.v1 import PCASectorSerializer, DistributionPlanSerializer




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
        model = InterventionAmendment
        fields = "__all__"


class AmendmentLogNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionAmendment
        fields = (
            "amended_at",
            "type",
        )
