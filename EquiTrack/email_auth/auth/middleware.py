from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.auth import authenticate, login


class TokenAuthenticationMiddleware(object):
    def process_request(self, request):
        token = request.GET.get(settings.EMAIL_AUTH_TOKEN_NAME)
        if token is None:
            return

        user = authenticate(url_auth_token=token)
        if user is None:
            return

        login(request, user)
