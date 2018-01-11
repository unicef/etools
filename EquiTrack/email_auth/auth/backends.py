from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.utils import timezone


class SecurityTokenAuthBackend(ModelBackend):
    def authenticate(self, url_auth_token=None, **kwargs):
        UserModel = get_user_model()

        user = UserModel.objects.filter(
            security_tokens__token=url_auth_token, security_tokens__is_used=False,
            security_tokens__created__gt=timezone.now() - settings.EMAIL_AUTH_TOKEN_LIFETIME
        ).first()

        if not user:
            return None

        user.security_tokens.update(is_used=True)
        return user
