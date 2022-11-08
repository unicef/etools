from django.db import transaction


class InterventionVisionSynchronizerMixin:
    def save(self, *args, **kwargs):
        from etools.applications.partners.tasks import send_pd_to_vision

        instance = super().save(*args, **kwargs)
        transaction.on_commit(lambda: send_pd_to_vision.delay(instance.pk))
        return instance
