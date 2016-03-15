
from django.core.urlresolvers import resolve

from rest_framework.test import APIClient, force_authenticate, APIRequestFactory

from tenant_schemas.test.cases import TenantTestCase


class APITenantTestCase(TenantTestCase):
    """
    Base test case for testing APIs
    """
    client_class = APIClient

    def forced_auth_req(self, method, url, user=None, data={}):
        """
        Function that allows api methods to be called with forced authentication

        :param method: the HTTP method 'get'/'post'
        :param url: the relative url to the base domain
        :param user: optional user if not authenticated as the current user
        :param data: any data that should be passed to the API view
        :return:
        """
        factory = APIRequestFactory()
        view_info = resolve(url)

        view = view_info.func
        req_to_call = getattr(factory, method)
        request = req_to_call(url, data, format='json')

        user = user if user else self.user
        force_authenticate(request, user=user)

        return view(request, *view_info.args, **view_info.kwargs)

