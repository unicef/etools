
from django.contrib.auth import get_user_model

from rest_framework import serializers

from etools.applications.locations.models import Location
from etools.applications.partners.models import Intervention, InterventionResultLink, PartnerOrganization
from etools.applications.reports.models import Result, Sector
from etools.applications.users.models import Office


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')

    class Meta:
        model = get_user_model()
        fields = ('id', 'full_name')


class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = ('id', 'name')


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ('id', 'name', 'description')


class PartnerOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name')


class PartnershipSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title')
    partner = serializers.PrimaryKeyRelatedField(source='agreement.partner', read_only=True)
    results = serializers.SerializerMethodField()

    class Meta:
        model = Intervention
        fields = ('id', 'name', 'partner', 'results')

    def get_results(self, obj):
        return InterventionResultLink.objects.filter(intervention=obj).values_list('cp_output_id', flat=True)


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Result
        fields = ('id', 'name')


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ('id', 'name')


class StaticDataSerializer(serializers.Serializer):
    partnerships = PartnershipSerializer(many=True)
    travel_types = serializers.ListField(child=serializers.CharField())
    travel_modes = serializers.ListField(child=serializers.CharField())
    action_point_statuses = serializers.ListField(child=serializers.CharField())
