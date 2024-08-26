import os.path
from datetime import datetime, timedelta, UTC

from django.utils.deconstruct import deconstructible

from azure.storage.blob import BlobClient, generate_blob_sas
from storages.backends.azure_storage import AzureStorage
from storages.utils import setting


def clean_name(name):
    return os.path.normpath(name).replace("\\", "/")


@deconstructible
class EToolsAzureStorage(AzureStorage):
    account_name = setting("AZURE_ACCOUNT_NAME")
    account_key = setting("AZURE_ACCOUNT_KEY")
    azure_container = setting("AZURE_CONTAINER")
    azure_ssl = setting("AZURE_SSL")

    auto_sign = setting("AZURE_AUTO_SIGN")
    azure_access_policy_permission = setting("AZURE_ACCESS_POLICY_PERMISSION")
    ap_expiry = setting("AZURE_ACCESS_POLICY_EXPIRY")

    def __init__(self, **settings):
        super().__init__(**settings)
        self._service_client = None
        self._client = None

    # modification of original url method with auto sign
    # https://github.com/jschneier/django-storages/blob/1.13.2/storages/backends/azure_storage.py#L301
    # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/storage/azure-storage-blob/migration_guide.md
    def url(self, name, expire=None, parameters=None):
        if hasattr(self.custom_client, 'get_blob_client'):
            name = self._get_valid_path(name)

            credential = None
            if self.auto_sign:
                start = (datetime.now(UTC) + timedelta(seconds=-120)).strftime('%Y-%m-%dT%H:%M:%SZ')
                expiry = (datetime.now(UTC) + timedelta(seconds=self.ap_expiry)).strftime('%Y-%m-%dT%H:%M:%SZ')
                sas_token = generate_blob_sas(
                    self.account_name,
                    self.azure_container,
                    name,
                    account_key=self.account_key,
                    permission=self.azure_access_policy_permission,
                    expiry=expiry,
                    start=start,
                )
                credential = sas_token

            container_blob_url = self.custom_client.get_blob_client(name).url
            return BlobClient.from_blob_url(container_blob_url, credential=credential).url
        else:
            return "{}{}/{}".format(setting('MEDIA_URL'), self.azure_container, name)
