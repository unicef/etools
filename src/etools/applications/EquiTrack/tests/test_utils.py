from datetime import datetime

from django.test import SimpleTestCase

from freezegun import freeze_time

from etools.applications.EquiTrack import utils

PATH_SET_TENANT = "etools.applications.libraries.tenant_support.set_tenant"


class TestUtils(SimpleTestCase):
    """
    Test utils function
    """

    @freeze_time("2013-05-26")
    def test_get_current_year(self):
        """test get current year function"""

        current_year = utils.get_current_year()
        self.assertEqual(current_year, 2013)

    @freeze_time("2013-05-26")
    def test_get_quarter_default(self):
        """test current quarter function"""
        quarter = utils.get_quarter()
        self.assertEqual(quarter, 'q2')

    def test_get_quarter(self):
        """test current quarter function"""
        quarter = utils.get_quarter(datetime(2016, 10, 1))
        self.assertEqual(quarter, 'q4')
