import itertools
from urllib.parse import urljoin

from django.conf import settings
from django.db.models import Manager, QuerySet

from rest_framework import serializers
from unicef_restlib.fields import CommaSeparatedExportField

from etools.applications.core.urlresolvers import build_frontend_url


class UsersExportField(serializers.Field):
    def to_representation(self, value):
        if isinstance(value, (QuerySet, Manager)):
            value = value.all()

        return ','.join(map(lambda u: u.get_full_name(), value))


class TPMActivityExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='tpm_visit.reference_number')
    visit = serializers.CharField(source='tpm_visit')
    visit_information = serializers.CharField(source='tpm_visit.visit_information')
    visit_status = serializers.CharField(source='tpm_visit.get_status_display')
    activity = serializers.SerializerMethodField()
    is_pv = serializers.BooleanField()
    section = serializers.CharField()
    cp_output = serializers.CharField()
    partner = serializers.CharField()
    intervention = serializers.CharField(source='intervention.reference_number', allow_null=True)
    pd_ssfa = serializers.CharField(source='intervention.title', allow_null=True)
    locations = CommaSeparatedExportField()
    date = serializers.DateField(format='%d/%m/%Y')
    unicef_focal_points = UsersExportField()
    offices = CommaSeparatedExportField()
    tpm_focal_points = UsersExportField(source='tpm_visit.tpm_partner_focal_points')
    additional_information = serializers.CharField()
    link = serializers.CharField(source='tpm_visit.get_object_url')

    def get_activity(self, obj):
        return 'Task #{}.{}'.format(obj.tpm_visit.id, obj.id)


class TPMLocationExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='activity.tpmactivity.tpm_visit.reference_number')
    visit = serializers.CharField(source='activity.tpmactivity.tpm_visit')
    visit_status = serializers.CharField(source='activity.tpmactivity.tpm_visit.get_status_display')
    activity = serializers.SerializerMethodField()
    section = serializers.CharField(source='activity.tpmactivity.section')
    cp_output = serializers.CharField(source='activity.tpmactivity.cp_output')
    partner = serializers.CharField(source='activity.tpmactivity.partner')
    intervention = serializers.CharField(source='activity.tpmactivity.intervention.reference_number', allow_null=True)
    pd_ssfa = serializers.CharField(source='activity.tpmactivity.intervention.title', allow_null=True)
    location = serializers.CharField()
    visit_information = serializers.CharField(source='activity.tpmactivity.tpm_visit.visit_information')
    date = serializers.DateField(source='activity.tpmactivity.date', format='%d/%m/%Y')
    unicef_focal_points = UsersExportField(source='activity.tpmactivity.unicef_focal_points')
    offices = CommaSeparatedExportField(source='activity.tpmactivity.offices')
    tpm_focal_points = UsersExportField(source='activity.tpmactivity.tpm_visit.tpm_partner_focal_points')
    additional_information = serializers.CharField(source='activity.tpmactivity.additional_information')
    link = serializers.CharField(source='activity.tpmactivity.tpm_visit.get_object_url')

    def get_activity(self, obj):
        return 'Task #{}.{}'.format(obj.activity.tpmactivity.tpm_visit.id, obj.activity.tpmactivity.id)


class TPMActionPointExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='reference_number')
    assigned_to = serializers.CharField(source='assigned_to.get_full_name', allow_null=True)
    author = serializers.CharField(source='author.get_full_name')
    section = serializers.CharField(source='tpm_activity.section')
    status = serializers.CharField(source='get_status_display')
    locations = serializers.SerializerMethodField()
    cp_output = serializers.CharField(source='tpm_activity.cp_output', allow_null=True)
    due_date = serializers.DateField(format='%d/%m/%Y')
    description = serializers.CharField()

    def get_locations(self, obj):
        return ', '.join(map(str, obj.tpm_activity.locations.all()))


class TPMActionPointFullExportSerializer(TPMActionPointExportSerializer):
    visit_ref = serializers.CharField(source='tpm_activity.tpm_visit.reference_number')


class TPMVisitExportSerializer(serializers.Serializer):
    ref = serializers.CharField(source='reference_number')
    visit = serializers.CharField(source='*')
    status = serializers.CharField(source='get_status_display')
    activities = CommaSeparatedExportField(source='tpm_activities')
    sections = CommaSeparatedExportField(source='tpm_activities.section', allow_null=True)
    partners = CommaSeparatedExportField(source='tpm_activities.partner', allow_null=True)
    interventions = CommaSeparatedExportField(source='tpm_activities.intervention', export_attr='reference_number')
    pd_ssfa = CommaSeparatedExportField(source='tpm_activities.intervention', export_attr='title')
    locations = CommaSeparatedExportField(source='tpm_activities.locations', allow_null=True)
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    unicef_focal_points = CommaSeparatedExportField()
    tpm_partner_focal_points = CommaSeparatedExportField()
    report_link = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    additional_information = CommaSeparatedExportField(source='tpm_activities.additional_information', allow_null=True)
    visit_information = serializers.CharField()
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
            lambda a: '{} - {}'.format(a.file_type, urljoin(settings.HOST, a.url)),
            attachments
        ))


class TPMPartnerExportSerializer(serializers.Serializer):
    vendor_number = serializers.CharField(source='organization.vendor_number')
    name = serializers.CharField(source='organization.name')
    street_address = serializers.CharField()
    postal_code = serializers.CharField()
    city = serializers.CharField()
    phone_number = serializers.CharField()
    email = serializers.CharField()


class TPMPartnerContactsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.CharField(source='user.email', allow_null=True)
    first_name = serializers.CharField(source='user.first_name', allow_null=True)
    last_name = serializers.CharField(source='user.last_name', allow_null=True)
    is_active = serializers.IntegerField(source='user.is_active', allow_null=True)
    job_title = serializers.CharField(source='user.profile.job_title', allow_null=True)
    phone_number = serializers.CharField(source='user.profile.phone_number', allow_null=True)
    org_id = serializers.CharField(source='tpm_partner.vendor_number', allow_null=True)
    org_name = serializers.CharField(source='tpm_partner.name', allow_null=True)
    org_email = serializers.CharField(source='tpm_partner.email', allow_null=True)
    org_phone = serializers.CharField(source='tpm_partner.phone_number', allow_null=True)
    org_country = serializers.CharField(source='tpm_partner.country', allow_null=True)
    org_city = serializers.CharField(source='tpm_partner.city', allow_null=True)
    org_address = serializers.CharField(source='tpm_partner.street_address', allow_null=True)
    org_postal_code = serializers.CharField(source='tpm_partner.postal_code', allow_null=True)
