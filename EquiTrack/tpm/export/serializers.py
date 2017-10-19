from django.utils import six

from rest_framework import serializers

from utils.common.urlresolvers import build_frontend_url


class UsersExportField(serializers.Field):
    def to_representation(self, value):
        return ','.join(map(lambda u: u.get_full_name(), value.all()))


class CommaSeparatedExportField(serializers.Field):
    export_attr = None

    def __init__(self, *args, **kwargs):
        self.export_attr = kwargs.pop('export_attr', None)
        super(CommaSeparatedExportField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        if self.export_attr:
            return ','.join(map(lambda x: getattr(x, self.export_attr), value.all()))
        else:
            return ','.join(map(six.text_type, value.all()))


class TPMActivityExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='tpm_visit.reference_number')
    visit = serializers.CharField(source='tpm_visit')
    activity = serializers.SerializerMethodField()
    section = serializers.CharField()
    cp_output = serializers.CharField()
    implementing_partner = serializers.CharField()
    partnership = serializers.CharField()
    locations = CommaSeparatedExportField()
    date = serializers.DateField(format='%d/%m/%Y')
    unicef_focal_points = UsersExportField(source='tpm_visit.unicef_focal_points')
    offices = CommaSeparatedExportField(source='tpm_visit.offices')
    tpm_focal_points = UsersExportField(source='tpm_visit.tpm_partner_focal_points')
    link = serializers.SerializerMethodField()

    def get_activity(self, obj):
        return 'Activity #{}.{}'.format(obj.tpm_visit.id, obj.id)

    def get_link(self, obj):
        return build_frontend_url('tpm', 'visits', obj.tpm_visit.id, 'details')


class TPMLocationExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='tpmactivity.tpm_visit.reference_number')
    visit = serializers.CharField(source='tpmactivity.tpm_visit')
    activity = serializers.SerializerMethodField()
    section = serializers.CharField(source='tpmactivity.section')
    cp_output = serializers.CharField(source='tpmactivity.cp_output')
    implementing_partner = serializers.CharField(source='tpmactivity.implementing_partner')
    partnership = serializers.CharField(source='tpmactivity.partnership')
    location = serializers.CharField()
    date = serializers.DateField(source='tpmactivity.date', format='%d/%m/%Y')
    unicef_focal_points = UsersExportField(source='tpmactivity.tpm_visit.unicef_focal_points')
    offices = CommaSeparatedExportField(source='tpmactivity.tpm_visit.offices')
    tpm_focal_points = UsersExportField(source='tpmactivity.tpm_visit.tpm_partner_focal_points')
    link = serializers.SerializerMethodField()

    def get_activity(self, obj):
        return 'Activity #{}.{}'.format(obj.tpmactivity.tpm_visit.id, obj.tpmactivity.id)

    def get_link(self, obj):
        return build_frontend_url('tpm', 'visits', obj.tpmactivity.tpm_visit.id, 'details')


class TPMPartnerExportSerializer(serializers.Serializer):
    vendor_number = serializers.CharField()
    name = serializers.CharField()
    street_address = serializers.CharField()
    postal_code = serializers.CharField()
    city = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.CharField()
