from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import serializers


class EngagementCancelSerializer(serializers.Serializer):
    cancel_comment = serializers.CharField()
