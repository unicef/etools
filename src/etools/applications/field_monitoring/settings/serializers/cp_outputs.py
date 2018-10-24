from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.field_monitoring.settings.models import CPOutputConfig
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name')


class InterventionSerializer(serializers.ModelSerializer):
    partner = PartnerSerializer(source='agreement.partner')

    class Meta:
        model = Intervention
        fields = ('id', 'title', 'number', 'partner')


class CPOutputConfigSerializer(serializers.ModelSerializer):
    government_partners = SeparatedReadWriteField(
        read_field=PartnerSerializer(many=True, label=_('Contributing Government Partners'))
    )

    class Meta:
        model = CPOutputConfig
        fields = ('cp_output', 'is_monitored', 'is_priority', 'government_partners')
        extra_kwargs = {
            'cp_output': {'read_only': True}
        }


class FieldMonitoringCPOutputSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    fm_config = CPOutputConfigSerializer()
    name = serializers.CharField(source='*')
    interventions = serializers.SerializerMethodField(label=_('Contributing CSO Partners & PD/SSFAs'))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = Result
        fields = ('id', 'fm_config', 'interventions', 'name')

    def get_interventions(self, obj):
        return [InterventionSerializer(link.intervention).data for link in obj.intervention_links.all()]
