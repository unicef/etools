from django.db import connection, transaction


class InterventionVisionSynchronizerMixin:
    def save(self, *args, **kwargs):
        from etools.applications.partners.tasks import send_pd_to_vision

        instance = super().save(*args, **kwargs)
        transaction.on_commit(lambda: send_pd_to_vision.delay(connection.tenant.name, instance.pk))
        return instance
