__author__ = 'RobertAvram'



from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import (
    Country,
    Section,
    UserProfile
)


class ActiveUsersSection(APIView):
    model = UserProfile

    def get(self, request, **kwargs):
        # get all the countries:
        country_list = Country.objects.values_list('name', flat=True)

        # get all sections:
        section_list = Section.objects.values_list('name', flat=True)

        country_records = {}
        for country in country_list:
            # create the first filter
            user_qry = UserProfile.objects.filter(
                user__is_staff=True,
                user__is_active=True,
                country__name=country
            )
            country_records[country] = {
                'total': user_qry.count()
            }

            section_users = {}
            for section in section_list:
                section_qry = user_qry.filter(
                    section__name=section,
                )
                section_users[section] = section_qry.count()

            country_records[country]['sections'] = section_users

        return Response(country_records)