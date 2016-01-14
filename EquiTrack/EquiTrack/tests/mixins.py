from django.core.management import call_command
from django.db import connection

from django.test import TestCase

from rest_framework.test import APIRequestFactory, APIClient, force_authenticate

from tenant_schemas.test.cases import TenantTestCase


class APITenantTestCase(TenantTestCase):
    client_class = APIClient

    def forced_auth_req(self, method, url, handler, user=None, data={}):
        factory = self.factory()
        view = handler.as_view()
        req_to_call = getattr(factory, method)
        request = req_to_call(url, data)
        user = user if user else self.user
        force_authenticate(request, user=user)
        return view(request)

