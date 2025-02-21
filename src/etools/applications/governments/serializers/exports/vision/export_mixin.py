from django.db import connection, transaction

from rest_framework import serializers

from etools.applications.environment.helpers import tenant_switch_is_active


class InterventionVisionSynchronizerMixin(serializers.ModelSerializer):

    def get_intervention(self):
        raise NotImplementedError

    def save(self, **kwargs):
        from etools.applications.partners.tasks import send_pd_to_vision

        instance = super().save(**kwargs)
        intervention = self.get_intervention()

        if not tenant_switch_is_active('disable_pd_vision_sync'):
            transaction.on_commit(lambda: send_pd_to_vision.delay(connection.tenant.name, intervention.pk))

        return instance
