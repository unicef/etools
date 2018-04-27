from django.conf import settings
from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin

from drfpasswordless.utils import authenticate_by_token


class TokenAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        token = request.GET.get(settings.EMAIL_AUTH_TOKEN_NAME)
        if token is None:
            return

        user = authenticate_by_token(token)
        if user is None:
            return

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
