import itertools

from future.backports.urllib.parse import urljoin

from django.utils import six

from rest_framework import serializers
from rest_framework.fields import empty, SkipField

from utils.common.urlresolvers import build_frontend_url, site_url
from utils.common.utils import get_attribute_smart


class UsersExportField(serializers.Field):
    def to_representation(self, value):
        return ','.join(map(lambda u: u.get_full_name(), value.all()))


class CommaSeparatedExportField(serializers.Field):
    export_attr = None

    def __init__(self, *args, **kwargs):
        self.export_attr = kwargs.pop('export_attr', None)
        super(CommaSeparatedExportField, self).__init__(*args, **kwargs)

    def get_attribute(self, instance):
        try:
            return get_attribute_smart(instance, self.source_attrs)
        except (KeyError, AttributeError) as exc:
            if not self.required and self.default is empty:
                raise SkipField()
            msg = (
                'Got {exc_type} when attempting to get a value for field '
                '`{field}` on serializer `{serializer}`.\nThe serializer '
                'field might be named incorrectly and not match '
                'any attribute or key on the `{instance}` instance.\n'
                'Original exception text was: {exc}.'.format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc
                )
            )
            raise type(exc)(msg)

    def to_representation(self, value):
        value = set(value)

        if self.export_attr:
            return ', '.join(map(lambda x: getattr(x, self.export_attr), value))
        else:
            return ', '.join(map(six.text_type, value))


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
    link = serializers.CharField(source='tpm_visit.get_object_url')

    def get_activity(self, obj):
        return 'Activity #{}.{}'.format(obj.tpm_visit.id, obj.id)


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
    link = serializers.CharField(source='tpmactivity.tpm_visit.get_object_url')

    def get_activity(self, obj):
        return 'Activity #{}.{}'.format(obj.tpmactivity.tpm_visit.id, obj.tpmactivity.id)


class TPMVisitExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='reference_number')
    visit = serializers.CharField(source='__str__')
    status = serializers.CharField(source='get_status_display')
    activities = CommaSeparatedExportField(source='tpm_activities')
    sections = CommaSeparatedExportField(source='tpm_activities.section')
    partners = CommaSeparatedExportField(source='tpm_activities.implementing_partner')
    partnerships = CommaSeparatedExportField(source='tpm_activities.partnership')
    locations = CommaSeparatedExportField(source='tpm_activities.locations')
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    unicef_focal_points = CommaSeparatedExportField()
    tpm_partner_focal_points = CommaSeparatedExportField()
    report_link = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    link = serializers.CharField(source='get_object_url')

    def get_report_link(self, obj):
        return build_frontend_url('tpm', 'visits', obj.id, 'report')

    def get_attachments(self, obj):
        attachments = itertools.chain(
            itertools.chain(*map(
                lambda a: itertools.chain(a.attachments.all(), a.report_attachments.all()),
                obj.tpm_activities.all()
            )),
            obj.report_attachments.all()
        )
        return ', '.join(map(
            lambda a: '{} - {}'.format(a.file_type, urljoin(site_url(), a.url)),
            attachments
        ))


class TPMPartnerExportSerializer(serializers.Serializer):
    vendor_number = serializers.CharField()
    name = serializers.CharField()
    street_address = serializers.CharField()
    postal_code = serializers.CharField()
    city = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.CharField()


class TPMPartnerContactsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.CharField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    is_active = serializers.IntegerField(source='user.is_active')
    job_title = serializers.CharField(source='user.profile.job_title')
    phone_number = serializers.CharField(source='user.profile.phone_number')
    org_id = serializers.CharField(source='tpm_partner.vendor_number')
    org_name = serializers.CharField(source='tpm_partner.name')
    org_email = serializers.CharField(source='tpm_partner.email')
    org_phone = serializers.CharField(source='tpm_partner.phone_number')
    org_country = serializers.CharField(source='tpm_partner.country')
    org_city = serializers.CharField(source='tpm_partner.city')
    org_address = serializers.CharField(source='tpm_partner.street_address')
    org_postal_code = serializers.CharField(source='tpm_partner.postal_code')
