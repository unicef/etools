from copy import copy

from django.contrib.auth import get_user_model

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin

from etools.applications.comments.models import Comment
from etools.applications.users.serializers import MinimalUserSerializer

User = get_user_model()


class BaseCommentSerializer(UserContextSerializerMixin, serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True)
    users_related = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(many=True),
        write_field=serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False),
    )

    class Meta:
        model = Comment
        fields = (
            'id', 'user', 'users_related',
            'text', 'state',
        )
        extra_kwargs = {
            'state': {'read_only': True},
        }

    def create(self, validated_data):
        validated_data['user'] = self.get_user()
        return super().create(validated_data)


class CommentSerializer(BaseCommentSerializer):
    class Meta(BaseCommentSerializer.Meta):
        fields = BaseCommentSerializer.Meta.fields + (
            'parent', 'related_to_description', 'related_to',
        )


class NewCommentSerializer(BaseCommentSerializer):
    class Meta(BaseCommentSerializer.Meta):
        fields = BaseCommentSerializer.Meta.fields + (
            'parent', 'related_to_description', 'related_to',
        )
        extra_kwargs = copy(BaseCommentSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'parent': {'required': False},
            'related_to_description': {'required': False},
            'related_to': {'required': False},
        })

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if 'parent' in validated_data:
            parent = validated_data['parent']
            validated_data['related_to'] = parent.related_to
            validated_data['related_to_description'] = parent.related_to_description

        return validated_data


class CommentEditSerializer(BaseCommentSerializer):
    class Meta(BaseCommentSerializer.Meta):
        fields = BaseCommentSerializer.Meta.fields + (
            'parent', 'related_to_description', 'related_to',
        )
        extra_kwargs = copy(BaseCommentSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'parent': {'read_only': True},
            'related_to_description': {'read_only': True},
            'related_to': {'read_only': True},
        })
