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


class SimpleProfileSerializer(serializers.ModelSerializer):

    user_id = serializers.CharField(source="user.id")
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    class Meta:
        model = UserProfile
        fields = (
            'user_id',
            'full_name'
        )


class UserSerializer(serializers.ModelSerializer):

    # profile = serializers.SerializerMethodField('get_profile')
    # It is redundant to specify `get_profile` on SerializerMethodField
    # because it is the same as the default method name.
    profile = serializers.SerializerMethodField()

    def get_profile(self, user):
        try:
            return UserProfileSerializer(
                user.profile
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