from rest_framework import serializers


class UsersExportField(serializers.Field):
    def to_representation(self, value):
        return ','.join(map(lambda u: u.get_full_name(), value.all()))


class CommaSeparatedExportField(serializers.Field):
    export_attr = None

    def __init__(self, *args, **kwargs):
        self.export_attr = kwargs.pop('export_attr')
        super(CommaSeparatedExportField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        return ','.join(map(lambda x: getattr(x, self.export_attr), value.all()))


class TPMVisitExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='tpm_visit.reference_number')
    activity = serializers.SerializerMethodField()
    sections = CommaSeparatedExportField(source='tpm_visit.sections', export_attr='name')
    output = serializers.CharField(source='cp_output.name')
    locations = CommaSeparatedExportField(export_attr='name')
    date = serializers.DateField(format='%d/%m/%Y')
    unicef_focal_points = UsersExportField(source='tpm_visit.unicef_focal_points')

    def get_activity(self, obj):
        return 'Activity #{}.{}'.format(obj.tpm_visit.id, obj.id)
