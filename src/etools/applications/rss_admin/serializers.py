from rest_framework import serializers

from etools.applications.organizations.models import Organization
from etools.applications.partners.models import PartnerOrganization


class PartnerOrganizationAdminSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())

    class Meta:
        model = PartnerOrganization
        fields = '__all__'


