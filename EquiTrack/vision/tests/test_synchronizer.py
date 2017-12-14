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
        self.assertEqual(loader.url, FAUX_VISION_URL + 'GetSomeStuff_JSON')

    @override_settings(VISION_URL=FAUX_VISION_URL)
    def test_instantiation_with_country(self):
        '''Ensure I can create a loader that specifies a country'''
        test_country = Country.objects.all()[0]
        test_country.business_area_code = 'ABC'
        test_country.save()

        loader = VisionDataLoader(country=test_country, endpoint='GetSomeStuff_JSON')
        self.assertEqual(loader.url, FAUX_VISION_URL + 'GetSomeStuff_JSON/ABC')

    def test_instantiation_url_construction(self):
        '''Ensure loader URL is constructed correctly regardless of whether or not base URL ends with a slash'''
        for faux_vision_url in ('https://api.example.com/foo.svc/',
                                'https://api.example.com/foo.svc'):
            with override_settings(VISION_URL=faux_vision_url):
                loader = VisionDataLoader(endpoint='GetSomeStuff_JSON')
                self.assertEqual(loader.url, 'https://api.example.com/foo.svc/GetSomeStuff_JSON')
