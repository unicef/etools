import json

from django.db import transaction
from rest_framework import serializers

from EquiTrack.serializers import JsonFieldSerializer
from partners.models import GovernmentIntervention, GovernmentInterventionResult, PartnerType


class GovernmentInterventionResultNestedSerializer(serializers.ModelSerializer):
    activity = JsonFieldSerializer(required=False)

    class Meta:
        model = GovernmentInterventionResult
        fields = ('id', 'intervention', 'result', 'year', 'planned_amount', 'activity',
                    'planned_visits', 'unicef_managers', 'sectors', 'sections')

        def validate(self, data):
            if not data['intervention']:
                raise serializers.ValidationError("There is no partner selected")
            if not data['result']:
                raise serializers.ValidationError("There is no result selected")
            if not data['year']:
                raise serializers.ValidationError("There is no year selected")
            if not data['planned_amount']:
                raise serializers.ValidationError("There is no planned amount entered")
            return data


class GovernmentInterventionListSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name')
    country_programme_name = serializers.CharField(source='country_programme.name')
    unicef_focal_points = serializers.SerializerMethodField()
    sectors = serializers.SerializerMethodField()
    cp_outputs = serializers.SerializerMethodField()
    years = serializers.SerializerMethodField()

    def get_unicef_focal_points(self, obj):
        unicef_focal_points = []
        for r in obj.results.all():
            unicef_focal_points = list(set([s.id for s in r.unicef_managers.all()] + unicef_focal_points))
        return unicef_focal_points

    def get_sectors(self, obj):
        sectors = []
        for r in obj.results.all():
            sectors = list(set([s.name for s in r.sectors.all()] + sectors))
        return sectors

    def get_cp_outputs(self, obj):
        return list(set([gr.result.id for gr in obj.results.all()]))

    def get_years(self, obj):
        return list(set([gr.year for gr in obj.results.all()]))

    class Meta:
        model = GovernmentIntervention
        fields = ("id", "number", "created_at", "partner", "partner_name", "country_programme",
                  "country_programme_name", "unicef_focal_points", "sectors", "cp_outputs", "years")


class GovernmentInterventionCreateUpdateSerializer(serializers.ModelSerializer):
    results = GovernmentInterventionResultNestedSerializer(many=True, required=False)

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'

    def validate(self, data):
        """
        Check that the start is before the stop.
        """
        if not 'partner' in data:
            raise serializers.ValidationError("There is no partner selected")
        if data['partner'].partner_type != PartnerType.GOVERNMENT:
            raise serializers.ValidationError("Partner type must be Government")
        if not 'country_programme' in data:
            raise serializers.ValidationError("There is no country programme selected")
        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        updated = super(GovernmentInterventionCreateUpdateSerializer, self).update(instance, validated_data)
        return updated


class GovernmentInterventionExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'
