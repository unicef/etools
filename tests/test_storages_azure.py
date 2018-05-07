# -*- coding: utf-8 -*-
import os
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

import pytest

from storages.backends.azure_storage import AzureStorage
from storages.utils import setting

TEST_FILENAME = 'test.tmp'
TEST_FILECONTENT = b'a'
TEST_FILESIZE = len('a')

pytestmark = pytest.mark.skipif(not os.environ.get('AZURE_ACCOUNT_NAME'),
                                reason='Skipped as not Azure connection informations available')


@pytest.fixture()
def configure(settings):
    settings.AZURE_ACCOUNT_NAME = os.environ['AZURE_ACCOUNT_NAME']
    settings.AZURE_ACCOUNT_KEY = os.environ['AZURE_ACCOUNT_KEY']
    settings.AZURE_CONTAINER = os.environ['AZURE_CONTAINER']
    settings.AZURE_SSL = True
    settings.AZURE_AUTO_SIGN = False
    settings.AZURE_ACCESS_POLICY_PERMISSION = os.environ['AZURE_ACCESS_POLICY_PERMISSION']
    settings.AZURE_ACCESS_POLICY_EXPIRY = 3600


@pytest.fixture()
def backend(configure):
    ret = AzureStorage()
    ret.account_name = setting("AZURE_ACCOUNT_NAME")
    ret.account_key = setting("AZURE_ACCOUNT_KEY")
    ret.azure_container = setting("AZURE_CONTAINER")
    ret.azure_ssl = setting("AZURE_SSL")
    ret.auto_sign = setting("AZURE_AUTO_SIGN")
    ret.azure_access_policy_permission = setting("AZURE_ACCESS_POLICY_PERMISSION")
    ret.ap_expiry = setting("AZURE_ACCESS_POLICY_EXPIRY")
    return ret


@pytest.fixture()
def resource(backend):
    ret = backend.save(TEST_FILENAME, BytesIO(TEST_FILECONTENT))
    yield ret
    backend.delete(ret)


def test_azure_protocol(backend):
    assert backend.azure_protocol == 'https'


def test_save_file(backend):
    assert backend.save(TEST_FILENAME, BytesIO(TEST_FILECONTENT))


def test_exists(backend, resource):
    assert backend.exists(resource)


def test_delete(backend, resource):
    assert backend.exists(resource)  # sanity check/test readability
    backend.delete(resource)
    assert not backend.exists(resource)

def test_size(backend, resource):
    assert backend.size(resource) == str(TEST_FILESIZE)


def test_url(backend, resource):
    assert backend.url(
        resource) == f'https://{setting("AZURE_ACCOUNT_NAME")}.blob.core.windows.net/{setting("AZURE_CONTAINER")}/{resource}'


def test_url2(backend, resource):
    backend.auto_sign = True
    "?st=2018-05-06T20%3A55%3A30Z&se=2018-05-06T21%3A57%3A30Z&sp=policy1&sv=2014-02-14&sr=b&sig=JBPY0PEbtzolve/9aoouRTKOLJ514aT1e6ApSIkSqoU%3D"
    url = backend.url(resource)
    parts = urlparse(url)

    assert parts.hostname == f'{setting("AZURE_ACCOUNT_NAME")}.blob.core.windows.net'
    assert parts.scheme == 'https'
    assert parts.path == f'/{setting("AZURE_CONTAINER")}/{TEST_FILENAME}'
    assert parts.query


def test_modified_time(backend, resource):
    assert isinstance(backend.modified_time(resource), datetime)
