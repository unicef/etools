import os.path
from datetime import datetime, timedelta

from azure.storage.blob import BlobPermissions
from django.utils.deconstruct import deconstructible

from azure.storage import AccessPolicy, SharedAccessSignature
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connection = None

    def url(self, name, expire=None):
        if hasattr(self.connection, 'make_blob_url'):
            name = self._get_valid_path(name)

            if expire is None:
                expire = self.expiration_secs
            make_blob_url_kwargs = {}
            if expire:
                sap = AccessPolicy(
                    permission=self.azure_access_policy_permission,
                    expiry=(datetime.utcnow() + timedelta(seconds=self.ap_expiry)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    start=(datetime.utcnow() + timedelta(seconds=-120)).strftime('%Y-%m-%dT%H:%M:%SZ')
                )

                sas_token = self.service.generate_blob_shared_access_signature(
                    self.azure_container, name, BlobPermissions.WRITE, expiry=self._expire_at(expire), sap)
                make_blob_url_kwargs['sas_token'] = sas_token

            if self.azure_protocol:
                make_blob_url_kwargs['protocol'] = self.azure_protocol
            return self.service.make_blob_url(
                container_name=self.azure_container,
                blob_name=name,
                **make_blob_url_kwargs)

        else:
            return "{}{}/{}".format(setting('MEDIA_URL'), self.azure_container, name)


    # def url(self, name):
    #     if hasattr(self.connection, 'make_blob_url'):
    #         if self.auto_sign:
    #             access_policy = AccessPolicy()
    #             access_policy.start = (datetime.utcnow() + timedelta(seconds=-120)).strftime('%Y-%m-%dT%H:%M:%SZ')
    #             access_policy.expiry = (datetime.utcnow() + timedelta(seconds=self.ap_expiry)).strftime('%Y-%m-%dT%H:%M:%SZ')
    #             access_policy.permission = self.azure_access_policy_permission
    #             sap = SharedAccessPolicy(access_policy)
    #             sas_token = self.connection.generate_shared_access_signature(
    #                 self.azure_container,
    #                 blob_name=name,
    #                 shared_access_policy=sap,
    #             )
    #         else:
    #             sas_token = None
    #         return self.connection.make_blob_url(
    #             container_name=self.azure_container,
    #             blob_name=name,
    #             protocol=self.azure_protocol,
    #             sas_token=sas_token,
    #         )
    #     else:
    #         return "{}{}/{}".format(setting('MEDIA_URL'), self.azure_container, name)
