__author__ = 'RobertAvram'


from django.db import connection

from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import (
    Country,
    Section,
    UserProfile
)
from trips.models import (
    Trip,
)
from partners.models import (
    Agreement,
    PCA
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


class TripsStatisticsView(APIView):
    model = Trip

    def get(self, request, **kwargs):
        # get all the countries:
        country_list = Country.objects.all()
        trips_by_country = {}
        for country in country_list:
            # set tenant for country
            connection.set_tenant(country)
            # get count for trips
            country_planned_count = Trip.objects.filter(
                status=Trip.PLANNED
            ).count()
            country_completed_count = Trip.objects.filter(
                status=Trip.COMPLETED
            ).count()
            country_all_count = Trip.objects.count()

            trips_by_country[country.name] = {
                'planned': country_planned_count,
                'completed': country_completed_count,
                'total': country_all_count
            }
        return Response(trips_by_country)


class AgreementsStatisticsView(APIView):
    model = Agreement

    def get(self, request, **kwargs):
        # get all the countries:
        country_list = Country.objects.all()
        agreements_by_country = {}
        for country in country_list:
            # set tenant for country
            connection.set_tenant(country)
            # get count for agreements
            country_agreements_count = Agreement.objects.count()

            agreements_by_country[country.name] = {
                "total_agreements": country_agreements_count
            }
        return Response(agreements_by_country)


class InterventionsStatisticsView(APIView):
    model = PCA

    def get(self, request, **kwargs):
        # get all the countries:
        country_list = Country.objects.all()
        interventions_by_country = {}
        for country in country_list:
            # set tenant for country
            connection.set_tenant(country)
            # get count for interventions
            country_interventions_count = Agreement.objects.count()

            interventions_by_country[country.name] = {
                "total_interventions": country_interventions_count
            }
        return Response(interventions_by_country)

