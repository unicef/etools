from rest_framework import serializers


class TPMVisitRejectSerializer(serializers.Serializer):
    reject_comment = serializers.CharField()


class TPMVisitApproveSerializer(serializers.Serializer):
    mark_as_programmatic_visit = serializers.ListField(child=serializers.IntegerField(), required=False)
    approval_comment = serializers.CharField(required=False)
    notify_focal_point = serializers.BooleanField(required=False)
    notify_tpm_partner = serializers.BooleanField(required=False)
