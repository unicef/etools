from django.urls import reverse

from rest_framework import status


class TestExportMixin(object):
    def _test_export(self, user, url_name, args=tuple(), kwargs=None, status_code=status.HTTP_200_OK):
        response = self.forced_auth_req(
            'get',
            reverse(url_name, args=args, kwargs=kwargs or {}),
            user=user
        )

        self.assertEqual(response.status_code, status_code)
        if status_code == status.HTTP_200_OK:
            self.assertIn(response._headers['content-disposition'][0], 'Content-Disposition')
