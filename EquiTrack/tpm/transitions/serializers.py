from rest_framework import serializers


class TPMVisitRejectSerializer(serializers.Serializer):
    reject_comment = serializers.CharField()
