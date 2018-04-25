
from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


class TPMActivityCSVRenderer(CSVRenderer):
    header = ['ref', 'visit', 'activity', 'section', 'cp_output', 'partner', 'intervention',
              'locations', 'date', 'unicef_focal_points', 'offices', 'tpm_focal_points', 'link']
    labels = {
        'ref': _('Visit Ref. #'),
        'visit': _('Visit'),
        'activity': _('Activity'),
        'section': _('Section'),
        'cp_output': _('PD/SSFA output'),
        'partner': _('Partner'),
        'intervention': _('Partnership'),
        'locations': _('Locations'),
        'date': _('Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
        'offices': _('Offices'),
        'tpm_focal_points': _('Name of TPM Focal Point'),
        'link': _('Hyperlink'),
    }


class TPMLocationCSVRenderer(CSVRenderer):
    header = ['ref', 'visit', 'activity', 'section', 'cp_output', 'partner', 'intervention',
              'location', 'date', 'unicef_focal_points', 'offices', 'tpm_focal_points', 'link']
    labels = {
        'ref': _('Visit Ref. #'),
        'visit': _('Visit'),
        'activity': _('Activity'),
        'section': _('Section'),
        'cp_output': _('PD/SSFA output'),
        'partner': _('Partner'),
        'intervention': _('Partnership'),
        'location': _('Location'),
        'date': _('Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
        'offices': _('Offices'),
        'tpm_focal_points': _('Name of TPM Focal Point'),
        'link': _('Hyperlink'),
    }


class TPMActionPointCSVRenderer(CSVRenderer):
    header = ['person_responsible', 'author', 'section', 'status', 'locations', 'cp_output', 'due_date']
    labels = {
        'person_responsible': _('Person Responsible'),
        'author': _('Assigned By'),
        'section': _('Section'),
        'status': _('Status'),
        'locations': _('Location(s)'),
        'cp_output': _('CP Output'),
        'due_date': _('Due Date'),
    }


class TPMVisitCSVRenderer(CSVRenderer):
    header = [
        'ref', 'visit', 'status', 'activities',
        'sections', 'partners', 'interventions', 'locations',
        'start_date', 'end_date', 'unicef_focal_points',
        'tpm_partner_focal_points', 'report_link', 'attachments', 'link',
    ]
    labels = {
        'ref': _('Visit Ref. #'),
        'visit': _('Visit'),
        'status': _('Status'),
        'activities': _('Activities'),
        'sections': _('Sections'),
        'partners': _('Partners'),
        'interventions': _('Partnerships'),
        'locations': _('Locations'),
        'start_date': _('Start Date'),
        'end_date': _('End Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
        'tpm_partner_focal_points': _('Name of TPM focal Point'),
        'report_link': _('Report Hyperlink'),
        'attachments': _('Attachment Type - Hyperlink'),
        'link': _('Visit Hyperlink'),
    }


class TPMPartnerCSVRenderer(CSVRenderer):
    header = [
        'vendor_number', 'name', 'street_address', 'postal_code', 'city',
        'phone_number', 'email',
    ]
    labels = {
        'vendor_number': _('Vendor Number'),
        'name': _('TPM Name'),
        'street_address': _('Address'),
        'postal_code': _('Postal Code'),
        'city': _('City'),
        'phone_number': _('Phone Number'),
        'email': _('Email Address'),
    }


class TPMPartnerContactsCSVRenderer(CSVRenderer):
    header = ['id', 'email', 'first_name', 'last_name', 'is_active', 'job_title', 'phone_number',
              'org_id', 'org_name', 'org_email', 'org_phone',
              'org_country', 'org_city', 'org_address', 'org_postal_code']
    labels = {
        'id': _('ID'),
        'email': _('Email'),
        'first_name': _('First name'),
        'last_name': _('Last name'),
        'is_active': _('Is active'),
        'job_title': _('Job title'),
        'phone_number': _('Phone number'),
        'org_id': _('Organization ID'),
        'org_name': _('Organization name'),
        'org_email': _('Organization email'),
        'org_phone': _('Organization phone number'),
        'org_country': _('Organization country'),
        'org_city': _('Organization city'),
        'org_address': _('Organization street address'),
        'org_postal_code': _('Organization postal code'),
    }
