from django.conf import settings
from django.shortcuts import HttpResponseRedirect

from social_core.exceptions import AuthCanceled
from social_django.middleware import SocialAuthExceptionMiddleware


class SocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    def process_exception(self, request, exception):
        if isinstance(exception, AuthCanceled):
            return HttpResponseRedirect(settings.LOGIN_URL)
        else:
            raise exception
