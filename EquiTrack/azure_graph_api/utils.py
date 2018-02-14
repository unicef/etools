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
    logger.debug('Azure: Information retrieved'.format(record.get('userPrincipalName', None)))
    user_sync = AzureUserMapper()
    user_sync.create_or_update_user(record)

    logger.debug('ID: {}'.format(record.get('id', None)))
    logger.debug('Username: {}'.format(record.get('userPrincipalName', None)))
    logger.debug('Email: {}'.format(record.get('mail', None)))
    logger.debug('Name: {}'.format(record.get('givenName', None)))
    logger.debug('Surname: {}'.format(record.get('surname', None)))
    logger.debug('Phone: {}'.format(record.get('businessPhones', None)))
    logger.debug('Mobile: {}'.format(record.get('mobilePhone', None)))
    logger.debug('Department: {}'.format(record.get('department', None)))

    logger.debug('Country Code [Business Area Code]: {}'.format(
        record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute1', '-')))
    logger.debug('Country: {}'.format(record.get('country', '-')))
    logger.debug('Index Number: {}'.format(
        record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute2', '-')))
    logger.debug('Nationality: {}'.format(record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute3', '-')))
    # logger.debug('4: {}'.format(record.get(
    #     'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute4', '-')))
    logger.debug('Region Name: {}'.format(record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute5', '-')))
    logger.debug('Division Code: {}'.format(record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute6', '-')))
    logger.debug('Section Name [Unit]: {}'.format(
        record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute7', '-')))
    logger.debug('Grade: {}{}'.format(
        record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute8', '-'),
        record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute9', '-')))
    # logger.debug('10: {}'.format(
    #     record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute10', '-')))
    logger.debug('Job Title: {}'.format(record.get('jobTitle', '-')))
    logger.debug('EOD: {}'.format(record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute11')))
    logger.debug('NTE: {}'.format(record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute12')))
    logger.debug('Hierarchy [Office]: {}'.format(
        record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute13', '-')))
    logger.debug('Division: {}'.format(record.get(
        'extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute14', '-')))
    logger.debug('Duty Station: {}'.format(
        record.get('extension_f4805b4021f643d0aa596e1367d432f1_extensionAttribute15', '-')))

    logger.debug('office Location: {}'.format(record.get('officeLocation', '-')))
    logger.debug('usage Location: {}'.format(record.get('usageLocation', '-')))
    logger.debug('Type: {}'.format(record.get('userType', '-')))

    logger.debug('----------------------------------------')
