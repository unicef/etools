from django.contrib.auth import get_user_model
from django.db import transaction

from etools.applications.last_mile import models
from etools.applications.users.models import Country, Group, Realm


class LMUserCreator:

    def create(self, validated_data):
        user_profile = validated_data.pop('profile', {})
        point_of_interests = validated_data.pop('point_of_interests', None)
        country_schema = validated_data.pop('country_schema')
        created_by = validated_data.pop('created_by')
        group = Group.objects.get(name="IP LM Editor")

        country = Country.objects.get(schema_name=country_schema)

        with transaction.atomic():
            user = get_user_model().objects.create(
                **validated_data
            )
            user.profile.country = country
            user.profile.organization = user_profile['organization']
            user.profile.job_title = user_profile['job_title']
            user.profile.phone_number = user_profile['phone_number']
            Realm.objects.create(
                user=user,
                country=country,
                organization=user_profile['organization'],
                group=group,
            )
            user.is_active = False
            user.save()
            user.profile.save()
            user.profile.organization.partner.points_of_interest.set(point_of_interests)
            models.Profile.objects.create(
                user=user,
                created_by=created_by
            )

        return user
