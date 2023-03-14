from django.db import connection, transaction

from rest_framework import serializers


class InterventionVisionSynchronizerMixin(serializers.ModelSerializer):

    def get_intervention(self):
        raise NotImplementedError

    def save(self, **kwargs):
        from etools.applications.partners.tasks import send_pd_to_vision

        instance = super().save(**kwargs)
        intervention = self.get_intervention()
        transaction.on_commit(lambda: send_pd_to_vision.delay(connection.tenant.name, intervention.pk))
        return instance
