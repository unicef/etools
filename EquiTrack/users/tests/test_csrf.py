from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from rest_framework import status


class CSRFTest(TestCase):
    """
    Simple smoke-test to ensure that CSRF protection is working. This only tests
    the admin login URL, so it is by no means an exhaustive test.
    """
    def setUp(self):
        super(CSRFTest, self).setUp()
        # Ask the test client to enforce CSRF checks
        self.client = Client(enforce_csrf_checks=True)
        self.admin_login_url = reverse('admin:login')

    def test_get_login_form(self):
        "GET should succeed without CSRF token."
        rsp = self.client.get(self.admin_login_url)
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)

    def test_post_login_form_without_csrf(self):
        "POST should fail without CSRF token."
        rsp = self.client.post(self.admin_login_url)
        self.assertEqual(rsp.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_login_form_with_bad_csrf(self):
        "POST should fail with wrong CSRF token."
        bad_token = 'not-the-right-token'
        rsp = self.client.post(self.admin_login_url, data={'csrfmiddlewaretoken': bad_token})
        self.assertEqual(rsp.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_login_form_with_csrf(self):
        "POST should succeed with correct CSRF token."
        # GET request, to get the token
        rsp = self.client.get(self.admin_login_url)
        good_token = rsp.context['csrf_token']
        rsp = self.client.post(self.admin_login_url, data={'csrfmiddlewaretoken': good_token})
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)
