
from django.core.urlresolvers import resolve

from rest_framework.test import APIClient, force_authenticate, APIRequestFactory

from tenant_schemas.test.cases import TenantTestCase
from tenant_schemas.test.client import TenantClient


class APITenantClient(TenantClient, APIClient):
    def __init__(self, tenant, **defaults):
        super(APITenantClient, self).__init__(tenant=tenant, defaults=defaults)


class APITenantTestCase(TenantTestCase):
    """
    Base test case for testing APIs
    """
    client_class = APIClient

    def forced_auth_req(self, method, url, user=None, data=None, **kwargs):
        """
        Function that allows api methods to be called with forced authentication

        :param method: the HTTP method 'get'/'post'
        :type method: str
        :param url: the relative url to the base domain
        :type url: st
        :param user: optional user if not authenticated as the current user
        :type user: django.contrib.auth.models.User
        :param data: any data that should be passed to the API view
        :type data: dict
        """
        factory = APIRequestFactory()
        view_info = resolve(url)

        data = data or {}
        view = view_info.func
        req_to_call = getattr(factory, method)
        request = req_to_call(url, data, format='json', **kwargs)

        user = user or self.user
        force_authenticate(request, user=user)

        response = view(request, *view_info.args, **view_info.kwargs)
        response.render()

        return response
