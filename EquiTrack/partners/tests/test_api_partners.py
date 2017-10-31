from __future__ import unicode_literals

from unittest import TestCase

from EquiTrack.tests.mixins import URLAssertionMixin


class URLsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('partner-assessment', 'assessments/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/partners/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')
