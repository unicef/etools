# Python imports
from __future__ import absolute_import, division, print_function

from datetime import datetime
from unittest import TestCase

from freezegun import freeze_time

from EquiTrack.utils import get_current_year, get_quarter


class TestUtils(TestCase):
    """
    Test utils function
    """

    @freeze_time("2013-05-26")
    def test_get_current_year(self):
        """test get current year function"""

        current_year = get_current_year()
        self.assertEqual(current_year, 2013)

    @freeze_time("2013-05-26")
    def test_get_quarter_default(self):

        """test current quarter function"""
        quarter = get_quarter()
        self.assertEqual(quarter, 'q2')

    def test_get_quarter(self):
        """test current quarter function"""
        quarter = get_quarter(datetime(2016, 10, 1))
        self.assertEqual(quarter, 'q4')
