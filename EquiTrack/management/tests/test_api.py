# Python imports
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from unittest import TestCase

from EquiTrack.tests.mixins import URLAssertionMixin


class UrlsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('dashboard', '', {}),
            ('load_result_structure', 'load-results/', {}),
            ('invalidate_cache', 'invalidate-cache/', {}),
            ('stats_user_counts', 'api/stats/usercounts/', {}),
            ('stats_trips', 'api/stats/trips/', {}),
            ('stats_agreements', 'api/stats/agreements/', {}),
            )
        self.assertReversal(names_and_paths, 'management:', '/api/management/')

    url(r'^$', PortalDashView.as_view()),
    url(r'^load-results/$', LoadResultStructure.as_view(), name='load_result_structure'),
    url(r'^invalidate-cache/$', InvalidateCache.as_view(), name='invalidate_cache'),
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view(), name='stats_user_counts'),
    url(r'^api/stats/trips/$', TripsStatisticsView.as_view(), name='stats_trips'),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view(), name='stats_agreements'),
