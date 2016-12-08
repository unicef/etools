
__author__ = 'jcranwellward'

from rest_framework import serializers

from et2f.models import UserTypes
from .models import User, UserProfile, Group, Office, Section


class UserProfileSerializer(serializers.ModelSerializer):

    office = serializers.CharField(source='office.name')
    section = serializers.CharField(source='section.name')
    country_name = serializers.CharField(source='country.name')

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
        )


class SimpleProfileSerializer(serializers.ModelSerializer):

    user_id = serializers.CharField(source="user.id")
    email = serializers.CharField(source="user.email")
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    class Meta:
        model = UserProfile
        fields = (
            'user_id',
            'full_name',
            'username',
            'email'
        )


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(source='get_full_name')
    roles = serializers.SerializerMethodField('get_assigned_roles')

    class Meta:
        model = User
        exclude = ('password', 'groups', 'user_permissions')

    def get_assigned_roles(self, obj):
        roles = [UserTypes.ANYONE]
        if obj.groups.filter(name='Representative Office').exists():
            roles.append(UserTypes.REPRESENTATIVE)
        return roles


class SectionSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Section
        fields = (
            'id',
            'name'
        )


class OfficeSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Office
        fields = (
            'id',
            'name',
            # 'zonal_chief'
        )


class UserProfileCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        exclude = (
            'id',
            'user',
        )


class GroupSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, group):
        return [perm.id for perm in group.permissions.all()]

    def create(self, validated_data):
        try:
            group = Group.objects.create(**validated_data)

        except Exception as ex:
            raise serializers.ValidationError({'group': ex.message})

        return group

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            'permissions'
        )


class UserCreationSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    groups = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()
    profile = UserProfileCreationSerializer()

    def get_groups(self, user):
        return [grp.id for grp in user.groups.all()]

    def get_user_permissions(self, user):
        return [perm.id for perm in user.user_permissions.all()]

    def create(self, validated_data):
        try:
            user_profile = validated_data.pop('profile')
        except KeyError:
            user_profile = {}

        try:
            countries = user_profile.pop('countries_available')
        except KeyError:
            countries = []

        try:
            user = User.objects.create(**validated_data)
            user.profile.country = user_profile['country']
            user.profile.office = user_profile['office']
            user.profile.section = user_profile['section']
            user.profile.partner_staff_member = 0
            user.profile.job_title = user_profile['job_title']
            user.profile.phone_number = user_profile['phone_number']
            user.profile.country_override = user_profile['country_override']
            user.profile.installation_id = user_profile['installation_id']
            for country in countries:
                user.profile.countries_available.add(country)

            user.save()
            user.profile.save()

        except Exception as ex:
            raise serializers.ValidationError({'user': ex.message})

        return user

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'is_superuser',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'groups',
            'user_permissions',
            'profile'
        )
