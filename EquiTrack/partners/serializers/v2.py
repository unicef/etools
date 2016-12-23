from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import serializers

from partners.models import GovernmentIntervention, GovernmentInterventionResult


class GovernmentInterventionResultNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentInterventionResult
        fields = (
            "result",
            "year",
            "planned_amount",
            "activities",
            "unicef_managers",
            "sector",
            "section",
            "activities_list",
            "planned_visits",
        )


class GovernmentInterventionResultCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentInterventionResult
        fields = '__all__'

    def validate(self, data):
        errors = {}
        try:
            data = super(GovernmentInterventionResultCreateUpdateSerializer, self).validate(data)
        except ValidationError as e:
            errors.update(e)

        if not data.get("result", None):
            errors.update(result=["This field is required."])
        if not data.get("planned_amount", None):
            errors.update(planned_amount=["This field is required."])
        if not data.get("year", None):
            errors.update(year=["This field is required."])
        if not data.get("sector", None):
            errors.update(result=["This field is required."])
        if not data.get("section", None):
            errors.update(result=["This field is required."])

        if errors:
            raise serializers.ValidationError(errors)

        return data


class GovernmentInterventionListSerializer(serializers.ModelSerializer):

    years = serializers.CharField()
    sectors = serializers.CharField()

    class Meta:
        model = GovernmentIntervention
        fields = (
            "number",
            "partner",
            "result_structure",
            "years",
            "sectors",
        )


class GovernmentInterventionDetailSerializer(serializers.ModelSerializer):

    results = GovernmentInterventionResultNestedSerializer(many=True)

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'


class GovernmentInterventionCreateUpdateSerializer(serializers.ModelSerializer):

    results = GovernmentInterventionResultNestedSerializer(many=True)

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        results = validated_data.pop("results", [])
        gov_intervention = super(GovernmentInterventionCreateUpdateSerializer, self).create(validated_data)
        for item in results:
            item["intervention"] = gov_intervention.id
            item["result"] = item["result"].id
            item["sector"] = item["sector"].id
            item["section"] = item["section"].id
            item["unicef_managers"] = [x.id for x in item["unicef_managers"]]
            serializer = GovernmentInterventionResultCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return gov_intervention

    @transaction.atomic
    def update(self, instance, validated_data):
        results = validated_data.pop("results", [])
        obj = GovernmentIntervention.objects.get(id=instance.id)
        for attr, value in validated_data.iteritems():
            setattr(obj, attr, value)
        obj.save()

        # Delete removed results
        ids = [x["id"] for x in results if "id" in x.keys()]
        for item in instance.results.all():
            if item.id not in ids:
                item.delete()

        # Create or update new/changed results.
        for item in results:
            item["intervention"] = instance.id
            item["result"] = item["result"].id
            item["sector"] = item["sector"].id
            item["section"] = item["section"].id
            item["unicef_managers"] = [x.id for x in item["unicef_managers"]]
            serializer = GovernmentInterventionResultCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return obj
