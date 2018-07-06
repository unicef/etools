from django.conf import settings
from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin

from drfpasswordless.utils import authenticate_by_token
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class TokenAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        token = request.GET.get(settings.EMAIL_AUTH_TOKEN_NAME)
        if token is None:
            return

        try:
            # attempt to auth via authtoken
            token_auth = TokenAuthentication()
            user, _ = token_auth.authenticate_credentials(token)
        except AuthenticationFailed:
            # attempt to auth by drfpasswordless
            user = authenticate_by_token(token)

        if user is None:
            return

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
