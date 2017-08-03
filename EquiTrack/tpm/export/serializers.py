from rest_framework import serializers


class UsersExportField(serializers.Field):
    def to_representation(self, value):
        return ','.join(map(lambda u: u.get_full_name(), value.all()))


class TPMVisitExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='tpm_low_result.tpm_sector.tpm_activity.tpm_visit.reference_number')
    visit = serializers.CharField(source='tpm_low_result.tpm_sector.tpm_activity.tpm_visit')
    activity = serializers.CharField(source='tpm_low_result.tpm_sector.tpm_activity')
    sector = serializers.CharField(source='tpm_low_result.tpm_sector.sector')
    output = serializers.CharField(source='tpm_low_result.result.cp_output')
    location = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    unicef_focal_points = UsersExportField(source='tpm_low_result.tpm_sector.tpm_activity.unicef_focal_points')
