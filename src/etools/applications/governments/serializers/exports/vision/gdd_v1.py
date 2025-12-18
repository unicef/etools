from django.db import connection

from rest_framework import serializers

from etools.applications.governments.models import GDDActivity, GDDKeyIntervention
from etools.applications.governments.serializers.gdd import GDDDetailSerializer
from etools.applications.governments.serializers.result_structure import GDDResultNestedSerializer
from etools.applications.reports.serializers.v2 import InterventionActivitySerializer


class KeyInterventionSerializer(serializers.ModelSerializer):

    code = serializers.CharField(read_only=True)

    class Meta:
        model = GDDKeyIntervention
        fields = [
            "id",
            "name",
            "code",
            "result_link",
            "total",
            "created",
            "modified",
        ]


class KeyInterventionWithActivitiesSerializer(KeyInterventionSerializer):
    activities = InterventionActivitySerializer(read_only=True, many=True)

    class Meta(KeyInterventionSerializer.Meta):
        fields = KeyInterventionSerializer.Meta.fields + ["activities"]


class BAPGDDActivitySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='ewp_activity.title', read_only=True)

    class Meta:
        model = GDDActivity
        fields = ['id', 'name', 'code', 'unicef_cash', 'cso_cash', 'is_active']


class BAPKeyInterventionWithActivitiesSerializer(KeyInterventionWithActivitiesSerializer):
    activities = BAPGDDActivitySerializer(read_only=True, many=True, source='gdd_activities')

    class Meta(KeyInterventionWithActivitiesSerializer.Meta):
        fields = ['id', 'name', 'activities']


class BAPGDDResultNestedSerializer(GDDResultNestedSerializer):

    gdd_key_interventions = BAPKeyInterventionWithActivitiesSerializer(many=True, read_only=True)

    class Meta(GDDResultNestedSerializer.Meta):
        fields = ['id', 'gdd_key_interventions']


class GDDVisionExportSerializer(GDDDetailSerializer):
    permissions = None
    available_actions = None
    document_type = serializers.SerializerMethodField()
    business_area = serializers.SerializerMethodField()
    offices = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()
    result_links = BAPGDDResultNestedSerializer(many=True, read_only=True, required=False)

    class Meta(GDDDetailSerializer.Meta):
        fields = [
            "number", "title", "partner_vendor", "business_area", "offices", "start", "end", "document_type",
            "status", "planned_budget", "partner_authorized_officer_signatory", "partner_focal_points",
            "unicef_focal_points", "budget_owner", "result_links"
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

    def get_document_type(self, obj):
        return 'GPD'
