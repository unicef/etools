import logging

from etools.applications.users.tasks import AzureUserMapper

logger = logging.getLogger(__name__)


def handle_records(jresponse):

    if 'value' in jresponse:
        status = {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        for record in jresponse['value']:
            page_status, _ = handle_record(record)
            status['processed'] += page_status['processed']
            status['created'] += page_status['created']
            status['updated'] += page_status['updated']
            status['skipped'] += page_status['skipped']
            status['errors'] += page_status['errors']
    else:
        status, _ = handle_record(jresponse)

    return status


def handle_record(record):
    logger.debug('Azure: Information retrieved %s', record.get('userPrincipalName', '-'))
    user_sync = AzureUserMapper()
    status = user_sync.create_or_update_user(record)

    record_dict = {
        'Username*': record.get('userPrincipalName', '-'),
        'Email*': record.get('mail', '-'),
        'Name*': record.get('givenName', '-'),
        'Surname*': record.get('surname', '-'),
        'Type*': record.get('userType', '-'),
        'Company Name*': record.get('companyName', '-'),
        'ID': record.get('id', '-'),
        'Phone': record.get('businessPhones', '-'),
        'Mobile': record.get('mobilePhone', '-'),
        'Department': record.get('department', '-'),
        'Country Code [Business Area Code]': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute1', '-'),
        'Country': record.get('country', '-'),
        'Index Number': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute2', '-'),
        'Nationality': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute3', '-'),
        'Attribute 4': record.get(
            'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute4', '-'),
        'Region Name': record.get(
            'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute5', '-'),
        'Division Code': record.get(
            'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute6', '-'),
        'Section Name [Unit]': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute7', '-'),
        'Grade': '{}{}'.format(record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute8', '-'),
                               record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute9', '-')),
        'Attribute 10': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute10', '-'),
        'Job Title': record.get('jobTitle', '-'),
        'EOD': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute11'),
        'NTE': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute12'),
        'Hierarchy [Office]': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute13', '-'),
        'Division': record.get(
            'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute14', '-'),
        'Duty Station': record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute15', '-'),

        'office Location': record.get('officeLocation', '-'),
        'usage Location': record.get('usageLocation', '-'),
    }

    for label, value in record_dict.items():
        logger.debug(f'{label}: {value}')
    logger.debug('----------------------------------------')

    return status, record_dict
