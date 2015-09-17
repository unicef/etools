__author__ = 'jcranwellward'

from rest_framework import serializers

from .models import User, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):

    office = serializers.CharField(source='office.name')
    section = serializers.CharField(source='section.name')

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
        )


class UserSerializer(serializers.ModelSerializer):

    # profile = serializers.SerializerMethodField('get_profile')
    # It is redundant to specify `get_profile` on SerializerMethodField
    # because it is the same as the default method name.
    profile = serializers.SerializerMethodField()

    def get_profile(self, user):
        try:
            return UserProfileSerializer(
                user.get_profile()
            ).data
        except Exception:
            return None

    class Meta:
        model = User
        exclude = (
            'password',
            'groups',
            'user_permissions'
        )