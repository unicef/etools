# Python imports
from __future__ import absolute_import, division, print_function

from unittest import TestCase

from freezegun import freeze_time

from EquiTrack.utils import get_current_quarter, get_current_year


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
    def test_get_current_quarter(self):

        """test current quarter function"""
        quarter = get_current_quarter()
        self.assertEqual(quarter, 'q2')
