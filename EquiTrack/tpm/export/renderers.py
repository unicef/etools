from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


class TPMActivityCSVRenderer(CSVRenderer):
    header = ['ref', 'activity', 'section', 'cp_output',
              'locations', 'date', 'unicef_focal_points']
    labels = {
        'ref': _('Visit Ref. #'),
        'activity': _('Activity'),
        'section': _('Section'),
        'cp_output': _('PD/SSFA output'),
        'locations': _('Locations'),
        'date': _('Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
    }


class TPMLocationCSVRenderer(CSVRenderer):
    header = ['ref', 'activity', 'section', 'cp_output',
              'location', 'date', 'unicef_focal_points']
    labels = {
        'ref': _('Visit Ref. #'),
        'activity': _('Activity'),
        'section': _('Section'),
        'cp_output': _('PD/SSFA output'),
        'location': _('Location'),
        'date': _('Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
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
