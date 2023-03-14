from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from rest_framework import serializers
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.users.models import UserProfile
from etools.applications.users.validators import EmailValidator


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


class UserSerializer(
        WritableNestedSerializerMixin,
        serializers.ModelSerializer,
):
    profile = UserProfileSerializer(required=False)
    email = serializers.EmailField(validators=[EmailValidator()])

    class Meta(WritableNestedSerializerMixin.Meta):
        model = get_user_model()
        fields = ['pk', 'first_name', 'last_name', 'email', 'is_active', 'profile', 'full_name']
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False, 'label': _('First Name')},
            'last_name': {'required': True, 'allow_blank': False, 'label': _('Last Name')},
        }

    def create(self, validated_data):
        email = validated_data.get('email', None)
        validated_data.setdefault('username', email)
        return super().create(validated_data)


class BaseStaffMemberSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    user = UserSerializer()

    class Meta(WritableNestedSerializerMixin.Meta):
        fields = [
            'id', 'user',
        ]
