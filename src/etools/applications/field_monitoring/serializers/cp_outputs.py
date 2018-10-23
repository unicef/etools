from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.field_monitoring.models import CPOutputConfig
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


class FMCPOutputSerializer(serializers.ModelSerializer):
    fm_config = CPOutputConfigSerializer()
    name = serializers.CharField(source='*')
    interventions = serializers.SerializerMethodField(label=_('Contributing CSO Partners & PD/SSFAs'))

    class Meta:
        model = Result
        fields = ('id', 'fm_config', 'interventions', 'name')

    def update(self, instance, validated_data):
        config_data = validated_data.pop('fm_config')
        config = CPOutputConfig.objects.filter(cp_output=instance).first()
        if not config:
            config_data['cp_output'] = instance
            instance.fm_config = self.get_fields()['fm_config'].create(config_data)
        else:
            instance.fm_config = self.get_fields()['fm_config'].update(config, config_data)

        return super().update(instance, validated_data)

    def get_interventions(self, obj):
        return [InterventionSerializer(link.intervention).data for link in obj.intervention_links.all()]
