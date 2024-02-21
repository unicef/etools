from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class ActionPointCompleteSerializer(serializers.Serializer):
    completed_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    potential_verifier = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), required=False)

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if self.instance.high_priority and self.instance.author == validated_data['completed_by']:
            if validated_data.get('potential_verifier', None) is None:
                raise ValidationError(_("Potential verifier is required"))

        return validated_data
