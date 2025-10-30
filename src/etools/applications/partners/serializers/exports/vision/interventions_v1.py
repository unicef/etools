from django.db import connection

from rest_framework import serializers

from etools.applications.partners.serializers.interventions_v2 import InterventionResultNestedSerializer
from etools.applications.partners.serializers.interventions_v3 import (
    InterventionDetailSerializer,
    InterventionManagementBudgetSerializer,
)
from etools.applications.reports.serializers.v2 import (
    InterventionActivitySerializer,
    LowerResultWithActivitiesSerializer,
)


class BAPInterventionActivitySerializer(InterventionActivitySerializer):
    name = serializers.SerializerMethodField()

    class Meta(InterventionActivitySerializer.Meta):
        fields = ['id', 'name', 'unicef_cash', 'cso_cash', 'is_active']

    def get_name(self, obj):
        return f"{obj.code} {obj.name}" if getattr(obj, 'code', None) else obj.name


class BAPLowerResultWithActivitiesSerializer(LowerResultWithActivitiesSerializer):
    activities = BAPInterventionActivitySerializer(read_only=True, many=True)

    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return f"{obj.code} {obj.name}" if getattr(obj, 'code', None) else obj.name

    class Meta(LowerResultWithActivitiesSerializer.Meta):
        fields = ['id', 'name', 'activities']


class BAPInterventionResultNestedSerializer(InterventionResultNestedSerializer):

    ll_results = BAPLowerResultWithActivitiesSerializer(many=True, read_only=True)

    class Meta(InterventionResultNestedSerializer.Meta):
        fields = ['id', 'll_results']


class BAPInterventionManagementBudgetSerializer(InterventionManagementBudgetSerializer):
    class Meta(InterventionManagementBudgetSerializer.Meta):
        fields = [f for f in InterventionManagementBudgetSerializer.Meta.fields if f not in ['items']]


class InterventionSerializer(InterventionDetailSerializer):
    permissions = None
    available_actions = None
    business_area = serializers.SerializerMethodField()
    offices = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()
    result_links = BAPInterventionResultNestedSerializer(many=True, read_only=True, required=False)
    management_budgets = BAPInterventionManagementBudgetSerializer(read_only=True)

    class Meta(InterventionDetailSerializer.Meta):
        fields = [
            "number", "title", "partner_vendor", "business_area", "offices", "start", "end", "document_type",
            "status", "planned_budget", "partner_authorized_officer_signatory", "partner_focal_points",
            "unicef_focal_points", "budget_owner", "result_links", "management_budgets",
        ]

    def get_user(self):
        """
        evidently disallow current user usage to avoid data inconsistencies
        """
        raise NotImplementedError

    def get_business_area(self, _obj):
        return connection.tenant.business_area_code

    def get_number(self, obj):
        return obj.number.split('-')[0]

    def get_offices(self, obj):
        return [o.id for o in obj.offices.all()]
