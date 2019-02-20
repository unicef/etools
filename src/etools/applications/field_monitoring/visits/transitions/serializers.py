from rest_framework import serializers


class VisitRejectSerializer(serializers.Serializer):
    reject_comment = serializers.CharField()


class VisitRejectReportSerializer(serializers.Serializer):
    report_reject_comment = serializers.CharField()


class VisitCancelSerializer(serializers.Serializer):
    cancel_comment = serializers.CharField()
