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
            list_user_pois = []
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
