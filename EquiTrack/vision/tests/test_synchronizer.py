# Python imports
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

from django.test import override_settings, TestCase
from django.utils import timezone

import mock

from vision.vision_data_synchronizer import VisionDataLoader, VisionDataSynchronizer
from EquiTrack.tests.mixins import FastTenantTestCase
from users.models import Country

FAUX_VISION_URL = 'https://api.example.com/foo.svc/'

class TestVisionDataLoader(FastTenantTestCase):
    '''Exercise VisionDataLoader class'''
    # Note - I don't understand why, but @override_settings(VISION_URL=FAUX_VISION_URL) doesn't work when I apply
    # it on TestVisionDataLoader instead of each individual test case.
    @override_settings(VISION_URL=FAUX_VISION_URL)
    def test_instantiation_no_country(self):
        '''Ensure I can create a loader without specifying a country'''
        loader = VisionDataLoader(endpoint='GetSomeStuff_JSON')
        self.assertEqual(loader.url, FAUX_VISION_URL + '/GetSomeStuff_JSON')

    @override_settings(VISION_URL=FAUX_VISION_URL)
    def test_instantiation_with_country(self):
        '''Ensure I can create a loader that specifies a country'''
        test_country = Country.objects.all()[0]
        test_country.business_area_code = 'ABC'
        test_country.save()

        loader = VisionDataLoader(country=test_country, endpoint='GetSomeStuff_JSON')
        self.assertEqual(loader.url, FAUX_VISION_URL + '/GetSomeStuff_JSON/ABC')



# class VisionDataLoader(object):
#     URL = settings.VISION_URL
#     EMPTY_RESPONSE_VISION_MESSAGE = u'No Data Available'

#     def __init__(self, country=None, endpoint=None):
#         if endpoint is None:
#             raise VisionException(message='You must set the ENDPOINT name')

#         self.url = '{}/{}'.format(
#             self.URL,
#             endpoint
#         )
#         if country:
#             self.url += '/{}'.format(country.business_area_code)
