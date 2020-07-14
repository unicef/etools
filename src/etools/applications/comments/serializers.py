from django.contrib.auth import get_user_model

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin

from etools.applications.comments.models import Comment
from etools.applications.users.serializers import MinimalUserSerializer

User = get_user_model()


class CommentSerializer(UserContextSerializerMixin, serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True)
    users_related = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(many=True),
        write_field=serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False),
    )

    class Meta:
        model = Comment
        fields = (
            'id', 'user', 'users_related',
            'related_to_description', 'related_to',
            'text', 'state',
        )
        extra_kwargs = {
            'state': {'read_only': True},
        }

    def create(self, validated_data):
        validated_data['user'] = self.get_user()
        return super().create(validated_data)
