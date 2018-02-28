from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from users.tasks import AzureUserMapper

logger = logging.getLogger(__name__)


def handle_records(jresponse):
    if 'value' in jresponse:
        for record in jresponse['value']:
            handle_record(record)
    else:
        handle_record(jresponse)


def handle_record(record):
    logger.debug('Azure: Information retrieved %s', record.get('userPrincipalName', '-'))
    user_sync = AzureUserMapper()
    user_sync.create_or_update_user(record)

    logger.debug('ID: %s', record.get('id', '-'))
    logger.debug('Username: %s', record.get('userPrincipalName', '-'))
    logger.debug('Email: %s', record.get('mail', '-'))
    logger.debug('Name: %s', record.get('givenName', '-'))
    logger.debug('Surname: %s', record.get('surname', '-'))
    logger.debug('Phone: %s', record.get('businessPhones', '-'))
    logger.debug('Mobile: %s', record.get('mobilePhone', '-'))
    logger.debug('Department: %s', record.get('department', '-'))

    logger.debug('Country Code [Business Area Code]: %s',
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute1', '-'))
    logger.debug('Country: %s', record.get('country', '-'))
    logger.debug('Index Number: %s',
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute2', '-'))
    logger.debug('Nationality: %s', record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute3', '-'))
    logger.debug('Attribute 4: %s', record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute4', '-'))
    logger.debug('Region Name: %s', record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute5', '-'))
    logger.debug('Division Code: %s', record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute6', '-'))
    logger.debug('Section Name [Unit]: %s',
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute7', '-'))
    logger.debug('Grade: %s%s',
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute8', '-'),
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute9', '-'))
    logger.debug('Attribute 10: %s',
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute10', '-'))
    logger.debug('Job Title: %s', record.get('jobTitle', '-'))
    logger.debug('EOD: %s', record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute11'))
    logger.debug('NTE: %s', record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute12'))
    logger.debug('Hierarchy [Office]: %s',
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute13', '-'))
    logger.debug('Division: %s', record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute14', '-'))
    logger.debug('Duty Station: %s',
                 record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute15', '-'))

    logger.debug('office Location: %s', record.get('officeLocation', '-'))
    logger.debug('usage Location: %s', record.get('usageLocation', '-'))
    logger.debug('Type: %s', record.get('userType', '-'))

    logger.debug('----------------------------------------')
