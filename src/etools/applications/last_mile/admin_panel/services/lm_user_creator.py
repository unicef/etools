import random

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction

from etools.applications.last_mile import models
from etools.applications.users.models import Country, Group, Realm


class LMUserCreator:

    def generate_password(self):
        return get_user_model().objects.make_random_password(length=random.randint(10, 16), allowed_chars='abcdefghjkmnpqrstuvwxyz0123456789.,!#$%^&*()')

    def create(self, validated_data):
        user_profile = validated_data.pop('profile', {})
        point_of_interests = validated_data.pop('point_of_interests', None)
        country_schema = validated_data.pop('country_schema')
        created_by = validated_data.pop('created_by')
        validated_data['password'] = make_password(self.generate_password())
        group = Group.objects.get(name="IP LM Editor")

        organizations = user_profile.pop('organizations', None)

        country = Country.objects.get(schema_name=country_schema)

        with transaction.atomic():
            user = get_user_model().objects.create(
                **validated_data
            )
            user.profile.country = country
            if user_profile.get('organization'):
                user.profile.organization = user_profile['organization']
            else:
                user.profile.organization = organizations[0]
            user.profile.job_title = user_profile['job_title']
            user.profile.phone_number = user_profile['phone_number']
            if user_profile.get('organization'):
                Realm.objects.create(
                    user=user,
                    country=country,
                    organization=user_profile['organization'],
                    group=group,
                )
            else:
                realms_to_create = []
                for organization in organizations:
                    realms_to_create.append(Realm(user=user, country=country, organization=organization, group=group))
                Realm.objects.bulk_create(realms_to_create)
            user.is_active = False
            user.save()
            user.profile.save()
            list_user_pois = []
            if point_of_interests:
                for poi_id in point_of_interests:
                    list_user_pois.append(models.UserPointsOfInterest(
                        user=user,
                        point_of_interest_id=poi_id.id if isinstance(poi_id, models.PointOfInterest) else poi_id
                    ))
                models.UserPointsOfInterest.objects.bulk_create(list_user_pois)
            models.Profile.objects.create(
                user=user,
                created_by=created_by
            )

        return user
