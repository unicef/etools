from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.field_monitoring.settings.models import CPOutputConfig
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import Result
from etools.applications.reports.serializers.v2 import OutputListSerializer


class InterventionSerializer(serializers.ModelSerializer):
    partner = MinimalPartnerOrganizationListSerializer(source='agreement.partner')

    class Meta:
        model = Intervention
        fields = ('id', 'title', 'number', 'partner')


class CPOutputConfigSerializer(serializers.ModelSerializer):
    government_partners = SeparatedReadWriteField(
        read_field=MinimalPartnerOrganizationListSerializer(many=True, label=_('Contributing Government Partners'))
    )

    class Meta:
        model = CPOutputConfig
        fields = ('id', 'cp_output', 'is_monitored', 'is_priority', 'government_partners')
        extra_kwargs = {
            'id': {'read_only': True},
            'cp_output': {'read_only': True, 'label': _('CP Output')}
        }


class CPOutputConfigDetailSerializer(CPOutputConfigSerializer):
    cp_output = OutputListSerializer()

    class Meta(CPOutputConfigSerializer.Meta):
        pass


class FieldMonitoringCPOutputSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    fm_config = CPOutputConfigSerializer()
    name = serializers.CharField(source='*', read_only=True)
    interventions = serializers.SerializerMethodField(label=_('Contributing CSO Partners & PD/SSFAs'))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = Result
        fields = ('id', 'fm_config', 'interventions', 'name', 'expired')

    def get_interventions(self, obj):
        return [InterventionSerializer(link.intervention).data for link in obj.intervention_links.all()]
