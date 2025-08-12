from rest_framework import serializers
from unicef_restlib.fields import CommaSeparatedExportField


class MonitoringActivityExportSerializer(serializers.Serializer):
    reference_number = serializers.CharField()
    ref_link = serializers.SerializerMethodField()
    start_date = serializers.DateField(format='%Y/%m/%d', allow_null=True)
    end_date = serializers.DateField(format='%Y/%m/%d', allow_null=True)
    location = serializers.CharField(allow_null=True)
    location_site = serializers.CharField(allow_null=True)
    sections = CommaSeparatedExportField()
    offices = CommaSeparatedExportField()
    status = serializers.CharField()
    monitor_type = serializers.CharField(source='get_monitor_type_display')
    team_members = CommaSeparatedExportField()
    tpm_partner = serializers.CharField(source='tpm_partner.name', allow_null=True)
    visit_lead = serializers.CharField(source='visit_lead.get_full_name', allow_null=True)
    partners = CommaSeparatedExportField()
    interventions = CommaSeparatedExportField()
    cp_outputs = CommaSeparatedExportField()

    def get_ref_link(self, obj):
        return obj.get_object_url()
