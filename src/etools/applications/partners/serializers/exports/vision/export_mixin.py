from django.db import connection, transaction

from rest_framework import serializers


class InterventionVisionSynchronizerMixin(serializers.ModelSerializer):
    def save(self, **kwargs):
        from etools.applications.partners.tasks import send_pd_to_vision

        instance = super().save(**kwargs)
        transaction.on_commit(lambda: send_pd_to_vision.delay(connection.tenant.name, instance.pk))
        return instance
