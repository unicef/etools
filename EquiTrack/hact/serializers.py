import json
from rest_framework import serializers

from hact.models import HactHistory


class HactHistorySerializer(serializers.ModelSerializer):
    partner_values = serializers.SerializerMethodField()

    def get_partner_values(self, obj):
        return json.loads(obj.partner_values) if isinstance(obj.partner_values, unicode) else obj.partner_values

    class Meta:
        model = HactHistory
        fields = (
            "id",
            "year",
            "created",
            "modified",
            "partner_values",
        )