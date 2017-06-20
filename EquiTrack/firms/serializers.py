from __future__ import absolute_import

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .utils import generate_username
from utils.writable_serializers.serializers import WritableNestedSerializerMixin
from users.models import UserProfile


class UserProfileSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = UserProfile
        fields = ['job_title', 'phone_number']


class UserSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all())])

    class Meta(WritableNestedSerializerMixin.Meta):
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active', 'profile']

    def create(self, validated_data):
        validated_data.setdefault('username', generate_username())
        return super(UserSerializer, self).create(validated_data)


class BaseStaffMemberSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    user = UserSerializer()

    class Meta(WritableNestedSerializerMixin.Meta):
        fields = [
            'id', 'user',
        ]
