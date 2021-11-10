from rest_framework import serializers

from etools.applications.hact.models import HactHistory


class HactHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = HactHistory
        fields = (
            "id",
            "year",
            "created",
            "modified",
            "partner_values",
        )


class AggregateHactSerializer(serializers.ModelSerializer):

    class Meta:
        model = HactHistory
        fields = (
            "id",
            "year",
            "created",
            "modified",
            "partner_values",
        )


class HactHistoryExportSerializer(serializers.BaseSerializer):
    @property
    def data(self):
        return self.to_presentation(self.initial_data)

    def to_representation(self, data):
        return [x[1] for x in data.partner_values]
