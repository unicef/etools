from __future__ import absolute_import, division, print_function, unicode_literals

from unittest import TestCase

from vision import client


class TestVisionClient(TestCase):
    def setUp(self):
        self.client = client.VisionAPIClient()

    def test_init(self):
        c = client.VisionAPIClient()
        self.assertTrue(c.base_url)

    def test_init_auth(self):
        """Check that auth attribute if username and password provided"""
        c = client.VisionAPIClient(username="test", password="123")
        self.assertTrue(c.base_url)
        self.assertIsInstance(c.auth, client.HTTPDigestAuth)

    def test_build_path_none(self):
        """If no path provided, use base_url attribute"""
        path = self.client.build_path()
        self.assertEqual(path, self.client.base_url)

    def test_build_path(self):
        path = self.client.build_path("api")
        self.assertEqual(path, "{}api".format(self.client.base_url))
