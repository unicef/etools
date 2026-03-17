import factory

from etools.applications.audit_log import models


class AuditLogEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AuditLogEntry

    object_id = factory.Sequence(lambda n: str(n))
    action = models.AuditLogEntry.ACTION_CREATE
    user = factory.SubFactory('etools.applications.users.tests.factories.UserFactory')
