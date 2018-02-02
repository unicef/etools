from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings

from EquiTrack.tests.mixins import FastTenantTestCase
from vision.adapters import manual as adapter


class TestManualDataLoader(FastTenantTestCase):
    def test_init_no_endpoint_no_object_number(self):
        with self.assertRaisesRegexp(
                adapter.VisionException,
                "You must set the ENDPOINT"
        ):
            adapter.ManualDataLoader()

    def test_init_no_endpoint(self):
        with self.assertRaisesRegexp(
                adapter.VisionException,
                "You must set the ENDPOINT"
        ):
            adapter.ManualDataLoader(object_number="123")

    def test_init(self):
        a = adapter.ManualDataLoader(endpoint="api", object_number="123")
        self.assertEqual(a.url, "{}/api/123".format(settings.VISION_URL))
