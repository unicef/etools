import operator
from collections import defaultdict
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from reports.models import Result
from funds.models import FundsCommitmentItem

from partners.models import (
    GovernmentIntervention, PartnerType,
    GovernmentInterventionResult, GovernmentInterventionResultActivity,
)
from functools import reduce


class FundsCommitmentItemListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsCommitmentItem
        fields = '__all__'


class GovernmentInterventionResultActivityNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentInterventionResultActivity
        fields = '__all__'


class GovernmentInterventionResultNestedSerializer(serializers.ModelSerializer):
    result_activities = GovernmentInterventionResultActivityNestedSerializer(many=True, read_only=True)

    class Meta:
        model = GovernmentInterventionResult
        fields = ('id', 'intervention', 'result',
                  'year', 'planned_amount', 'result_activities',
                  'unicef_managers', 'sectors', 'planned_visits',
                  'sections')

    def validate(self, data):
        if 'intervention' not in data:
            raise serializers.ValidationError("There is no partner selected")
        if 'result' not in data:
            raise serializers.ValidationError("There is no result selected")
        if not data.get('year'):
            raise serializers.ValidationError("There is no year selected")
        if not data.get('planned_amount'):
            raise serializers.ValidationError("There is no planned amount entered")
        return data

    def validate_sectors(self, value):
        return value

    def validate_sections(self, value):
        return value

    @transaction.atomic()
    def create(self, validated_data):

        gir = super(GovernmentInterventionResultNestedSerializer, self).create(validated_data)

        activities = self.context.pop('result_activities', [])
        for act in activities:
            act['intervention_result'] = gir.pk
            ac_serializer = GovernmentInterventionResultActivityNestedSerializer(data=act)
            if ac_serializer.is_valid(raise_exception=True):
                ac_serializer.save()

        return gir

    @transaction.atomic()
    def update(self, instance, validated_data):
        activities = self.context.pop('result_activities', [])

        instance = super(GovernmentInterventionResultNestedSerializer, self).update(instance, validated_data)
        for act in activities:
            act['intervention_result'] = instance.pk
            if 'id' in act:
                try:
                    activity = GovernmentInterventionResultActivity.objects.get(id=act['id'])
                    ac_serializer = GovernmentInterventionResultActivityNestedSerializer(instance=activity,
                                                                                         data=act, partial=True)
                except GovernmentInterventionResultActivity.DoesNotExist:
                    raise ValidationError('government intervention result activity '
                                          'received an id but cannot be found in DB')
            else:
                ac_serializer = GovernmentInterventionResultActivityNestedSerializer(data=act)

            if ac_serializer.is_valid(raise_exception=True):
                ac_serializer.save()

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
            unicef_focal_points = list(set([(s.id, s.get_full_name()) for s in r.unicef_managers.all()] + unicef_focal_points))
        return list({"id": ufp[0], "name": ufp[1]} for ufp in unicef_focal_points)

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


class MinimalGovernmentInterventionListSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name')

    class Meta:
        model = GovernmentIntervention
        fields = (
            "id",
            "partner_name",
        )


class GovernmentInterventionCreateUpdateSerializer(serializers.ModelSerializer):
    results = GovernmentInterventionResultNestedSerializer(many=True, read_only=True, required=False)
    implementation_status = serializers.SerializerMethodField()

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'

    def get_implementation_status(self, obj):
        # Grab all Result objects which result type is Output and has a link to governmentinterventionresult
        cp_output_results = Result.objects.filter(
            result_type__name="Output",
            governmentinterventionresult__in=obj.results.all())

        # Query FundsCommitmentItem objects with above Result wbs list
        wbs_numbers = [x for x in cp_output_results.values_list('wbs', flat=True) if x is not None]

        # Form queryset for FC since WBS-s are at the Activity level
        if wbs_numbers:
            q = reduce(operator.or_, (Q(wbs__icontains=x) for x in wbs_numbers))
            target_funding_commitments = list(FundsCommitmentItem.objects.filter(q))
        else:
            target_funding_commitments = []

        fund_commitment_map = defaultdict(list)
        for f in target_funding_commitments:
            fund_commitment_map[f.wbs].append(FundsCommitmentItemListSerializer(f).data)

        def get_fc_records(output):
            v = []
            for k in fund_commitment_map:
                if output.wbs in k:
                    v = fund_commitment_map[k]
                    break
            return {"cp_output": output.id, "fc_records": v}

        implementation_status = [get_fc_records(k) for k in cp_output_results if k.wbs is not None]
        return implementation_status

    def validate(self, data):
        """
        Check that the start is before the stop.
        """
        if 'partner' not in data:
            raise serializers.ValidationError("There is no partner selected")
        if data['partner'].partner_type != PartnerType.GOVERNMENT:
            raise serializers.ValidationError("Partner type must be Government")
        if 'country_programme' not in data:
            raise serializers.ValidationError("There is no country programme selected")
        return data


class GovernmentInterventionExportSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name')
    country_programme_name = serializers.CharField(source='country_programme.name')
    cp_outputs = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    def get_cp_outputs(self, obj):
        cp_outputs = [
            'Output: {} ({}/{:,}/{})'.format(
                gr.result.name,
                gr.year,
                gr.planned_amount,
                gr.planned_visits)
            for gr in obj.results.all()
        ]
        return ', '.join(cp_outputs)

    def get_url(self, obj):
        return 'https://{}/pmp/governments/{}/details/'.format(self.context['request'].get_host(), obj.id)

    class Meta:
        model = GovernmentIntervention
        fields = ["partner_name", "country_programme_name", "number", "cp_outputs", "url", ]


class GovernmentInterventionSummaryListSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name')
    country_programme_name = serializers.CharField(source='country_programme.name')

    # government intervention = true, for distinguishing on the front end
    government_intervention = serializers.SerializerMethodField()

    def get_government_intervention(self, obj):
        return True

    class Meta:
        model = GovernmentIntervention
        fields = ("id", 'number', "created_at", "partner_name", "country_programme_name", "government_intervention")
