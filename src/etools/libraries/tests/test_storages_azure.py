import os
from datetime import datetime
from io import BytesIO
from unittest.mock import Mock
from urllib.parse import urlparse

from django.test import override_settings, TestCase

import responses
from storages.utils import setting

from etools.libraries.azure_storage_backend import EToolsAzureStorage

TEST_FILENAME = 'test.tmp'
TEST_FILECONTENT = b'a'
TEST_FILESIZE = len('a')


@override_settings(
    AZURE_ACCOUNT_NAME='123',
    AZURE_ACCOUNT_KEY=os.environ.get('AZURE_ACCOUNT_KEY', ''),
    AZURE_CONTAINER='unicef',
    AZURE_SSL=True,
    AZURE_AUTO_SIGN=False,
    AZURE_ACCESS_POLICY_PERMISSION=os.environ.get('AZURE_ACCESS_POLICY_PERMISSION', ''),
    AZURE_ACCESS_POLICY_EXPIRY=3600
)
class TestAzureStorage(TestCase):
    @responses.activate
    def setUp(self):
        super().setUp()
        self.url = 'https://123.blob.core.windows.net/unicef/test.tmp'
        responses.add(
            responses.PUT,
            self.url,
            "",
            status=201,
            headers={
                "Date": 'Fri, 09 Nov 2018 22:57:38 GMT',
                "ETag": '"0x8D64696BF6CEB80"',
                "Last-Modified": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "Server": "Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0",
                "x-ms-blob-append-offset": "0",
                "x-ms-blob-committed-block-count": '1',
                "x-ms-request-id": "b74641f8-d01e-000e-7b7f-782320000000",
                "x-ms-server-encrypted": 'true',
                "x-ms-version": '2018-03-28',
            }
        )
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
        ret.get_available_name = Mock(return_value="test.tmp")
        return ret

    # def resource(self):
    #     ret = self.backend.save(TEST_FILENAME, BytesIO(TEST_FILECONTENT))
    # yield ret
    # backend.delete(ret)

    def test_azure_protocol(self):
        assert self.backend.azure_protocol == 'https'

    @responses.activate
    def test_save_file(self):
        responses.add(
            responses.PUT,
            self.url,
            "",
            status=201,
            headers={
                "Date": 'Fri, 09 Nov 2018 22:57:38 GMT',
                "ETag": '"0x8D64696BF6CEB80"',
                "Last-Modified": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "Server": "Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0",
                "x-ms-blob-append-offset": "0",
                "x-ms-blob-committed-block-count": '1',
                "x-ms-request-id": "b74641f8-d01e-000e-7b7f-782320000000",
                "x-ms-server-encrypted": 'true',
                "x-ms-version": '2018-03-28',
            }
        )
        assert self.backend.save(TEST_FILENAME, BytesIO(TEST_FILECONTENT))

    @responses.activate
    def test_exists(self):
        responses.add(
            responses.HEAD,
            self.url,
            b"",
            status=200,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": f"{TEST_FILESIZE}",
                "Content-Type": "application/octet-stream",
                "Date": 'Fri, 09 Nov 2018 22:57:38 GMT',
                "ETag": '"0x8D64696BF6CEB80"',
                "Last-Modified": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "Server": "Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0",
                "Vary": "Origin",
                "x-ms-access-tier": "Hot",
                "x-ms-access-tier-inferred": 'true',
                "x-ms-blob-committed-block-count": '1',
                "x-ms-blob-type": "AppendBlob",
                "x-ms-creation-time": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "x-ms-lease-state": "available",
                "x-ms-lease-status": "unlocked",
                "x-ms-request-id": "b74641f8-d01e-000e-7b7f-782320000000",
                "x-ms-server-encrypted": 'true',
                "x-ms-version": '2018-03-28',
            }
        )
        assert self.backend.exists(self.resource)

    @responses.activate
    def test_delete(self):
        responses.add(
            responses.HEAD,
            self.url,
            b"",
            status=200,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": f"{TEST_FILESIZE}",
                "Content-Type": "application/octet-stream",
                "Date": 'Fri, 09 Nov 2018 22:57:38 GMT',
                "ETag": '"0x8D64696BF6CEB80"',
                "Last-Modified": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "Server": "Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0",
                "Vary": "Origin",
                "x-ms-access-tier": "Hot",
                "x-ms-access-tier-inferred": 'true',
                "x-ms-blob-committed-block-count": '1',
                "x-ms-blob-type": "AppendBlob",
                "x-ms-creation-time": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "x-ms-lease-state": "available",
                "x-ms-lease-status": "unlocked",
                "x-ms-request-id": "b74641f8-d01e-000e-7b7f-782320000000",
                "x-ms-server-encrypted": 'true',
                "x-ms-version": '2018-03-28',
            }
        )
        responses.add(responses.HEAD, self.url, b"", status=404)
        responses.add(responses.DELETE, self.url, b"", status=204)
        assert self.backend.exists(self.resource)  # sanity check/test readability
        self.backend.delete(self.resource)
        assert not self.backend.exists(self.resource)

    @responses.activate
    def test_size(self):
        responses.add(
            responses.HEAD,
            self.url,
            b"",
            status=200,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": f"{TEST_FILESIZE}",
                "Content-Type": "application/octet-stream",
                "Date": 'Fri, 09 Nov 2018 22:57:38 GMT',
                "ETag": '"0x8D64696BF6CEB80"',
                "Last-Modified": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "Server": "Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0",
                "Vary": "Origin",
                "x-ms-access-tier": "Hot",
                "x-ms-access-tier-inferred": 'true',
                "x-ms-blob-committed-block-count": '1',
                "x-ms-blob-type": "AppendBlob",
                "x-ms-creation-time": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "x-ms-lease-state": "available",
                "x-ms-lease-status": "unlocked",
                "x-ms-request-id": "b74641f8-d01e-000e-7b7f-782320000000",
                "x-ms-server-encrypted": 'true',
                "x-ms-version": '2018-03-28',
            }
        )
        assert self.backend.size(self.resource) == str(TEST_FILESIZE)

    def test_url(self):
        assert self.backend.url(self.resource) == 'https://{}.blob.core.windows.net/{}/{}'.format(
            setting("AZURE_ACCOUNT_NAME"),
            setting("AZURE_CONTAINER"),
            self.resource
        )

    def test_url2(self):
        self.backend.auto_sign = True
        "?st=2018-05-06T20%3A55%3A30Z&se=2018-05-06T21%3A57%3A30Z&sp=policy1&sv=2014-02-14&sr=b&sig=JBPY0PEbtzolve/9aoouRTKOLJ514aT1e6ApSIkSqoU%3D"
        url = self.backend.url(self.resource)
        parts = urlparse(url)

        assert parts.hostname == f'{setting("AZURE_ACCOUNT_NAME")}.blob.core.windows.net'
        assert parts.scheme == 'https'
        assert parts.path == f'/{setting("AZURE_CONTAINER")}/{TEST_FILENAME}'
        assert parts.query

    @responses.activate
    def test_modified_time(self):
        responses.add(
            responses.HEAD,
            self.url,
            b"",
            status=200,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": f"{TEST_FILESIZE}",
                "Content-Type": "application/octet-stream",
                "Date": 'Fri, 09 Nov 2018 22:57:38 GMT',
                "ETag": '"0x8D64696BF6CEB80"',
                "Last-Modified": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "Server": "Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0",
                "Vary": "Origin",
                "x-ms-access-tier": "Hot",
                "x-ms-access-tier-inferred": 'true',
                "x-ms-blob-committed-block-count": '1',
                "x-ms-blob-type": "AppendBlob",
                "x-ms-creation-time": 'Fri, 09 Nov 2018 22:57:39 GMT',
                "x-ms-lease-state": "available",
                "x-ms-lease-status": "unlocked",
                "x-ms-request-id": "b74641f8-d01e-000e-7b7f-782320000000",
                "x-ms-server-encrypted": 'true',
                "x-ms-version": '2018-03-28',
            }
        )
        assert isinstance(self.backend.modified_time(self.resource), datetime)
