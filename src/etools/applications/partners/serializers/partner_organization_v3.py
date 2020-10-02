from rest_framework import serializers

from etools.applications.partners.models import PartnerOrganization


class PartnerOrganizationDummySerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerOrganization
        fields = ()
