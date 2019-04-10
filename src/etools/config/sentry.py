import sentry_sdk

from sentry_sdk import configure_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from django.db import connection
from django.conf import settings

if hasattr(settings, 'SENTRY_DSN'):
    def before_send(event, hint):
        with configure_scope() as scope:
            scope.set_extra("tenant", connection.tenant.schema_name)
            # event = scope.apply_to_event(event, hint)

        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        # by default this is False, must be set to True so the library attaches the request data to the event
        send_default_pii=True,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        before_send=before_send,
    )
