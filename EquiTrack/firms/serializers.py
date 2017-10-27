from __future__ import absolute_import

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .utils import generate_username
from utils.writable_serializers.serializers import WritableNestedSerializerMixin
from users.models import UserProfile


class UserProfileSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = UserProfile
        fields = ['job_title', 'phone_number']
        extra_kwargs = {
            'job_title': {
                'label': _('Position'),
            },
            'phone_number': {
                'label': _('Phone Number'),
            }
        }


class UserSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    email = serializers.EmailField(
        label=_('E-mail Address'), validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta(WritableNestedSerializerMixin.Meta):
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active', 'profile']
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False, 'label': _('First Name')},
            'last_name': {'required': True, 'allow_blank': False, 'label': _('Last Name')},
        }

    def create(self, validated_data):
        validated_data.setdefault('username', generate_username())
        return super(UserSerializer, self).create(validated_data)


class BaseStaffMemberSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    user = UserSerializer()

    class Meta(WritableNestedSerializerMixin.Meta):
        fields = [
            'id', 'user',
        ]
