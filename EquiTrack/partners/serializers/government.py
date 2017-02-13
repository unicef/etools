import json

from django.db import transaction
from rest_framework import serializers

from EquiTrack.serializers import JsonFieldSerializer
from partners.models import GovernmentIntervention, GovernmentInterventionResult, GovernmentInterventionResultActivity


class GovernmentInterventionResultActivityNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentInterventionResultActivity
        fields = '__all__'


class GovernmentInterventionResultNestedSerializer(serializers.ModelSerializer):
    result_activities = GovernmentInterventionResultActivityNestedSerializer(many=True, read_only=True)

    class Meta:
        model = GovernmentInterventionResult
        fields = ('id', 'intervention', 'result', 'year', 'planned_amount', 'result_activities', 'unicef_managers', 'sectors',
                  'sections')

    def validate(self, data):
        """
        Check that the start is before the stop.
        """
        if not data['intervention']:
            raise serializers.ValidationError("There is no partner selected")
        return data


    @transaction.atomic()
    def create(self, validated_data):
        unicef_managers = validated_data.pop('unicef_managers')
        sectors = validated_data.pop('sectors')
        sections = validated_data.pop('sections')
        gir = GovernmentInterventionResult.objects.create(**validated_data)
        gir.unicef_managers = unicef_managers
        gir.save()
        activities = self.context.pop('result_activities')
        for act in activities:
            act['intervention_result'] = gir.pk
            ac_serializer = GovernmentInterventionResultActivityNestedSerializer(data=act)
            if ac_serializer.is_valid(raise_exception=True):
                ac_serializer.save()

        return gir

    @transaction.atomic()
    def update(self, instance, validated_data):
        activities = self.context.pop('result_activities')
        for key, val in validated_data.items():
            setattr(instance, key, val)
        for act in activities:
            act['intervention_result'] = instance.pk
            if 'id' in act:
                try:
                    activity = GovernmentInterventionResultActivity.objects.get(id=act['id'])
                    ac_serializer = GovernmentInterventionResultActivityNestedSerializer(instance=activity,
                                                                                         data=act, partial=True)
                except GovernmentInterventionResultActivity.DoesNotExist:
                    continue
            else:
                ac_serializer = GovernmentInterventionResultActivityNestedSerializer(data=act)

            if ac_serializer.is_valid(raise_exception=True):
                ac_serializer.save()

        instance.save()
        return instance


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