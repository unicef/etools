import itertools

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodTypeSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.field_monitoring.fm_settings.models import CPOutputConfig, PlannedCheckListItem, \
    PlannedCheckListItemPartnerInfo
from etools.applications.partners.models import Intervention
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin
from etools.applications.reports.models import Result
from etools.applications.reports.serializers.v1 import SectionSerializer
from etools.applications.reports.serializers.v2 import OutputListSerializer
from etools.applications.utils.common.urlresolvers import build_frontend_url


class PartnerOrganizationSerializer(MinimalPartnerOrganizationListSerializer):
    url = serializers.SerializerMethodField()

    class Meta(MinimalPartnerOrganizationListSerializer.Meta):
        fields = MinimalPartnerOrganizationListSerializer.Meta.fields + (
            'url',
        )

    def get_url(self, obj):
        return build_frontend_url('pmp', 'partners', obj.id, 'details')


class InterventionSerializer(serializers.ModelSerializer):
    partner = PartnerOrganizationSerializer(source='agreement.partner')
    url = serializers.SerializerMethodField()

    class Meta:
        model = Intervention
        fields = ('id', 'title', 'number', 'partner', 'url')

    def get_url(self, obj):
        return build_frontend_url('pmp', 'interventions', obj.id, 'details')


class CPOutputConfigSerializer(serializers.ModelSerializer):
    government_partners = SeparatedReadWriteField(
        read_field=PartnerOrganizationSerializer(many=True),
        label=_('Contributing Government Partners')
    )
    recommended_method_types = SeparatedReadWriteField(
        read_field=FMMethodTypeSerializer(many=True),
        label=_('Method(s)')
    )
    sections = SeparatedReadWriteField(read_field=SectionSerializer())

    class Meta:
        model = CPOutputConfig
        fields = (
            'id', 'cp_output', 'is_monitored', 'is_priority', 'government_partners',
            'recommended_method_types', 'sections',
        )
        extra_kwargs = {
            'id': {'read_only': True},
            'cp_output': {'read_only': True, 'label': _('CP Output')}
        }


class ResultSerializer(OutputListSerializer):
    name = serializers.ReadOnlyField()

    class Meta(OutputListSerializer.Meta):
        pass


class NestedCPOutputSerializer(ResultSerializer):
    interventions = serializers.SerializerMethodField()

    class Meta(ResultSerializer.Meta):
        pass

    def get_interventions(self, obj):
        return [InterventionSerializer(link.intervention).data for link in obj.intervention_links.all()]


class CPOutputConfigDetailSerializer(SafeReadOnlySerializerMixin, CPOutputConfigSerializer):
    cp_output = NestedCPOutputSerializer()
    partners = serializers.SerializerMethodField()

    class Meta(CPOutputConfigSerializer.Meta):
        fields = CPOutputConfigSerializer.Meta.fields + ('partners',)

    def get_partners(self, obj):
        return [
            PartnerOrganizationSerializer(partner).data
            for partner in sorted(set(itertools.chain(
                obj.government_partners.all(),
                map(lambda l: l.intervention.agreement.partner, obj.cp_output.intervention_links.all()))
            ), key=lambda a: a.id)
        ]


class FieldMonitoringCPOutputSerializer(SafeReadOnlySerializerMixin, WritableNestedSerializerMixin, serializers.ModelSerializer):
    fm_config = CPOutputConfigSerializer()
    interventions = serializers.SerializerMethodField(label=_('Contributing CSO Partners & PD/SSFAs'))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = Result
        fields = ('id', 'fm_config', 'interventions', 'name', 'expired')

    def get_interventions(self, obj):
        return [InterventionSerializer(link.intervention).data for link in obj.intervention_links.all()]


class PlannedCheckListItemPartnerInfoSerializer(SafeReadOnlySerializerMixin,
                                                WritableNestedSerializerMixin, serializers.ModelSerializer):
    partner = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer())

    class Meta(WritableNestedSerializerMixin.Meta):
        model = PlannedCheckListItemPartnerInfo
        fields = ('id', 'partner', 'specific_details', 'standard_url',)


class PlannedCheckListItemSerializer(SafeReadOnlySerializerMixin, WritableNestedSerializerMixin,
                                     serializers.ModelSerializer):
    partners_info = PlannedCheckListItemPartnerInfoSerializer(many=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = PlannedCheckListItem
        fields = ('id', 'checklist_item', 'methods', 'partners_info')
