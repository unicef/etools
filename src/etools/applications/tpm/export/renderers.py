from copy import copy

from django.utils.translation import gettext as _

from rest_framework_csv.renderers import CSVRenderer
from unicef_rest_export.renderers import FriendlyCSVRenderer


class TPMActivityCSVRenderer(FriendlyCSVRenderer):
    header = ['ref', 'visit', 'visit_status', 'activity', 'section', 'cp_output', 'partner', 'intervention', 'pd_ssfa',
              'locations', 'date', 'unicef_focal_points', 'offices', 'tpm_focal_points', 'visit_information', 'is_pv',
              'additional_information', 'link']
    labels = {
        'ref': _('Visit Ref. #'),
        'visit': _('Visit'),
        'visit_status': _('Status of Visit'),
        'activity': _('Task'),
        'is_pv': _('Is Programmatic Visit'),
        'section': _('Section'),
        'cp_output': _('PD/SPD output'),
        'partner': _('Partner'),
        'intervention': _('Partnership'),
        'pd_ssfa': _('PD/SPD'),
        'locations': _('Locations'),
        'date': _('Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
        'offices': _('Offices'),
        'tpm_focal_points': _('Name of TPM Focal Point'),
        'visit_information': _('Visit Information'),
        'additional_information': _('Additional Information'),
        'link': _('Hyperlink'),
    }


class TPMLocationCSVRenderer(CSVRenderer):
    header = ['ref', 'visit', 'visit_status', 'activity', 'section', 'cp_output', 'partner', 'intervention', 'pd_ssfa',
              'location', 'date', 'unicef_focal_points', 'offices', 'tpm_focal_points', 'visit_information',
              'additional_information', 'link']
    labels = {
        'ref': _('Visit Ref. #'),
        'visit': _('Visit'),
        'visit_status': _('Status of Visit'),
        'activity': _('Task'),
        'section': _('Section'),
        'cp_output': _('PD/SPD output'),
        'partner': _('Partner'),
        'intervention': _('Partnership'),
        'pd_ssfa': _('PD/SPD'),
        'location': _('Location'),
        'date': _('Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
        'offices': _('Offices'),
        'tpm_focal_points': _('Name of TPM Focal Point'),
        'visit_information': _('Visit Information'),
        'additional_information': _('Additional Information'),
        'link': _('Hyperlink'),
    }


class TPMActionPointCSVRenderer(CSVRenderer):
    header = ['ref', 'assigned_to', 'author', 'section', 'status', 'locations', 'cp_output', 'due_date', 'description']
    labels = {
        'ref': _('Ref. #'),
        'assigned_to': _('Person Responsible'),
        'author': _('Assigned By'),
        'section': _('Section'),
        'status': _('Status'),
        'locations': _('Location(s)'),
        'cp_output': _('CP Output'),
        'due_date': _('Due Date'),
        'description': _('Description'),
    }


class TPMActionPointFullCSVRenderer(TPMActionPointCSVRenderer):
    header = ['visit_ref'] + TPMActionPointCSVRenderer.header
    labels = copy(TPMActionPointCSVRenderer.labels)
    labels.update({
        'visit_ref': _('Visit Ref. #')
    })


class TPMVisitCSVRenderer(CSVRenderer):
    header = [
        'ref', 'visit', 'status', 'activities',
        'sections', 'partners', 'interventions', 'pd_ssfa', 'locations',
        'start_date', 'end_date', 'unicef_focal_points',
        'tpm_partner_focal_points', 'report_link', 'attachments', 'visit_information', 'additional_information',
        'link',
    ]
    labels = {
        'ref': _('Visit Ref. #'),
        'visit': _('Visit'),
        'status': _('Status of Visit'),
        'activities': _('Tasks'),
        'sections': _('Sections'),
        'partners': _('Partners'),
        'interventions': _('Partnerships'),
        'pd_ssfa': _('PD/SPD'),
        'locations': _('Locations'),
        'start_date': _('Start Date'),
        'end_date': _('End Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
        'tpm_partner_focal_points': _('Name of TPM focal Point'),
        'report_link': _('Report Hyperlink'),
        'attachments': _('Attachment Type - Hyperlink'),
        'visit_information': _('Visit Information'),
        'additional_information': _('Additional Information'),
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
