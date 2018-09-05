import os
from datetime import datetime
from io import BytesIO
from unittest import skipIf
from urllib.parse import urlparse

from django.test import override_settings, TestCase

from storages.utils import setting

from etools.libraries.azure_storage_backend import EToolsAzureStorage

TEST_FILENAME = 'test.tmp'
TEST_FILECONTENT = b'a'
TEST_FILESIZE = len('a')


@skipIf(not os.environ.get('AZURE_ACCOUNT_NAME'), reason='Skipped as not Azure connection informations available')
@override_settings(AZURE_ACCOUNT_NAME=os.environ.get('AZURE_ACCOUNT_NAME', ''),
                   AZURE_ACCOUNT_KEY=os.environ.get('AZURE_ACCOUNT_KEY', ''),
                   AZURE_CONTAINER=os.environ.get('AZURE_CONTAINER', ''),
                   AZURE_SSL=True, AZURE_AUTO_SIGN=False,
                   AZURE_ACCESS_POLICY_PERMISSION=os.environ.get('AZURE_ACCESS_POLICY_PERMISSION', ''),
                   AZURE_ACCESS_POLICY_EXPIRY=3600)
class TestAzureStorage(TestCase):
    def setUp(self):
        super().setUp()
        self.backend = self.get_backend()
        self.resource = self.backend.save(TEST_FILENAME, BytesIO(TEST_FILECONTENT))

    def get_backend(self):
        ret = EToolsAzureStorage()
        ret.account_name = setting("AZURE_ACCOUNT_NAME")
        ret.account_key = setting("AZURE_ACCOUNT_KEY")
        ret.azure_container = setting("AZURE_CONTAINER")
        ret.azure_ssl = setting("AZURE_SSL")
        ret.auto_sign = setting("AZURE_AUTO_SIGN")
        ret.azure_access_policy_permission = setting("AZURE_ACCESS_POLICY_PERMISSION")
        ret.ap_expiry = setting("AZURE_ACCESS_POLICY_EXPIRY")
        return ret

    # def resource(self):
    #     ret = self.backend.save(TEST_FILENAME, BytesIO(TEST_FILECONTENT))
    # yield ret
    # backend.delete(ret)

    def test_azure_protocol(self):
        assert self.backend.azure_protocol == 'https'

    def test_save_file(self):
        assert self.backend.save(TEST_FILENAME, BytesIO(TEST_FILECONTENT))

    def test_exists(self, resource):
        assert self.backend.exists(resource)

    def test_delete(self):
        assert self.backend.exists(self.resource)  # sanity check/test readability
        self.backend.delete(self.resource)
        assert not self.backend.exists(self.resource)

    def test_size(self):
        assert self.backend.size(self.resource) == str(TEST_FILESIZE)

    def test_url(self, resource):
        assert self.backend.url(
            resource) == f'https://{setting("AZURE_ACCOUNT_NAME")}.blob.core.windows.net/{setting("AZURE_CONTAINER")}/{resource}'

    def test_url2(self, resource):
        self.backend.auto_sign = True
        "?st=2018-05-06T20%3A55%3A30Z&se=2018-05-06T21%3A57%3A30Z&sp=policy1&sv=2014-02-14&sr=b&sig=JBPY0PEbtzolve/9aoouRTKOLJ514aT1e6ApSIkSqoU%3D"
        url = self.backend.url(resource)
        parts = urlparse(url)

        assert parts.hostname == f'{setting("AZURE_ACCOUNT_NAME")}.blob.core.windows.net'
        assert parts.scheme == 'https'
        assert parts.path == f'/{setting("AZURE_CONTAINER")}/{TEST_FILENAME}'
        assert parts.query

    def test_modified_time(self, resource):
        assert isinstance(self.backend.modified_time(resource), datetime)
