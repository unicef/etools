# Python imports

from django.test import SimpleTestCase

from EquiTrack.tests.mixins import URLAssertionMixin


class UrlsTestCase(URLAssertionMixin, SimpleTestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('dashboard', '', {}),
            ('load_result_structure', 'load-results/', {}),
            ('invalidate_cache', 'invalidate-cache/', {}),
            ('stats_user_counts', 'api/stats/usercounts/', {}),
            ('stats_agreements', 'api/stats/agreements/', {}),
        )
        self.assertReversal(names_and_paths, 'management:', '/api/management/')
