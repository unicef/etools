from __future__ import absolute_import, division, print_function, unicode_literals

from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from model_utils.models import TimeStampedModel


@python_2_unicode_compatible
class SecurityToken(TimeStampedModel):
    token = models.UUIDField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='security_tokens')
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return '{token.user.email}: {token.token}'.format(token=self)

    @classmethod
    def generate_token(cls, user):
        while True:
            new_token = uuid4()
            if not cls.objects.filter(token=new_token).exists():
                break

        return cls.objects.create(user=user, token=new_token)
