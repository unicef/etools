from django.db import connection

from rest_framework import serializers

from etools.applications.partners.serializers.interventions_v2 import InterventionResultNestedSerializer
from etools.applications.partners.serializers.interventions_v3 import InterventionDetailSerializer
from etools.applications.reports.serializers.v2 import (
    InterventionActivitySerializer,
    LowerResultWithActivitiesSerializer,
)


class BAPInterventionActivitySerializer(InterventionActivitySerializer):
    class Meta(InterventionActivitySerializer.Meta):
        fields = [
            f for f in InterventionActivitySerializer.Meta.fields
            if f in ['id', 'name', 'unicef_cash', 'cso_cash', 'is_active']
        ]


class BAPLowerResultWithActivitiesSerializer(LowerResultWithActivitiesSerializer):
    activities = BAPInterventionActivitySerializer(read_only=True, many=True)

    class Meta(LowerResultWithActivitiesSerializer.Meta):
        fields = [
            f for f in LowerResultWithActivitiesSerializer.Meta.fields
            if f in ['id', 'name', 'activities']
        ]


class BAPInterventionResultNestedSerializer(InterventionResultNestedSerializer):

    ll_results = BAPLowerResultWithActivitiesSerializer(many=True, read_only=True)

    class Meta(InterventionResultNestedSerializer.Meta):
        fields = [
            f for f in InterventionResultNestedSerializer.Meta.fields
            if f in ['id', 'll_results']
        ]


class InterventionSerializer(InterventionDetailSerializer):
    permissions = None
    available_actions = None
    business_area = serializers.SerializerMethodField()
    offices = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()
    result_links = BAPInterventionResultNestedSerializer(many=True, read_only=True, required=False)

    class Meta(InterventionDetailSerializer.Meta):
        fields = [
            f for f in InterventionDetailSerializer.Meta.fields
            if f in {

            }
        ] + [
            "number", "title", "partner_vendor", "business_area", "offices", "start", "end", "document_type",
            "status", "planned_budget", "partner_authorized_officer_signatory", "partner_focal_points", "budget_owner",
            "result_links"
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
