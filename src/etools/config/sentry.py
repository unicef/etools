import sentry_sdk
from sentry_sdk import configure_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from django.conf import settings

if settings.SENTRY_DSN:
    def _before_send(event, hint):
        request = getattr(event, 'request', None)
        if request:
            if getattr(request, 'tenant', None):
                with configure_scope() as scope:
                    scope.set_extra("tenant", event.request.tenant.name)
        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        send_default_pii=True,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        before_send=_before_send,
    )
