__author__ = 'RobertAvram'


from datetime import date, timedelta
from django.db import connection
from django.http import HttpResponse
from django.conf import settings

from django.views.generic import View
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


class PortalDashView(View):

    def get(self, request):
        with open(settings.SITE_ROOT + '/templates/frontend/management/management.html', 'r') as my_f:
            result = my_f.read()
        return HttpResponse(result)

class ActiveUsersSection(APIView):
    model = UserProfile

    def get(self, request, **kwargs):
        # get all the countries:
        country_list = Country.objects.values_list('name', flat=True)

        # get all sections:
        section_list = Section.objects.values_list('name', flat=True)

        results = []
        for country in country_list:
            country_records = {}
            # create the first filter
            user_qry = UserProfile.objects.filter(
                user__is_staff=True,
                user__is_active=True,
                country__name=country
            )
            country_records[country] = {
                'total': user_qry.count()
            }

            sections = []
            for section in section_list:
                section_qry = user_qry.filter(
                    section__name=section,
                )
                section_users = {
                    'name': section,
                    'count': section_qry.count()
                }
                sections.append(section_users)

            country_records[country]['sections'] = sections
            results.append({'countryName': country,
                            'records': country_records[country]})

        return Response(results)


class TripsStatisticsView(APIView):
    model = Trip

    def get(self, request, **kwargs):
        # get all the countries:
        country_list = Country.objects.filter(buisness_area_code__gt=0).all()
        results = []
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
            country_approved_count = Trip.objects.filter(
                status=Trip.APPROVED
            ).count()
            country_all_count = Trip.objects.count()

            # get all sections:
            section_list = Section.objects.values_list('name', flat=True)
            section_results = []
            for section in section_list:
                section_completed_count = Trip.objects.filter(
                    section__name=section,
                    status=Trip.COMPLETED
                ).count()
                section_approved_count = Trip.objects.filter(
                    section__name=section,
                    status=Trip.APPROVED
                ).count()
                section_planned_count = Trip.objects.filter(
                    section__name=section,
                    status=Trip.PLANNED
                ).count()
                section_total_count = Trip.objects.filter(
                    section__name=section
                ).count()
                section_results.append({
                    "name": section,
                    "completed": section_completed_count,
                    "approved": section_approved_count,
                    "planned": section_planned_count,
                    "total": section_total_count
                })

            trips_by_country = {
                'planned': country_planned_count,
                'completed': country_completed_count,
                'approved': country_approved_count,
                'total': country_all_count,
            }
            results.append({
                'countryName': country.name,
                'totals': trips_by_country,
                'sections': section_results
            })
        return Response(results)


class AgreementsStatisticsView(APIView):
    model = Agreement

    def get(self, request, **kwargs):
        today = date.today()
        # get all the countries:
        country_list = Country.objects.filter(buisness_area_code__gt=0).all()
        results = []
        for country in country_list:
            # set tenant for country
            connection.set_tenant(country)
            # get count for agreements
            country_agreements_count = Agreement.objects.filter(
                start__lt=today,
                end__gt=today
            ).count()

            results.append({
                "countryName": country.name,
                "totalAgreements": country_agreements_count
            })
        return Response(results)


class InterventionsStatisticsView(APIView):
    model = PCA

    def get(self, request, **kwargs):
        # get all the countries:
        country_list = Country.objects.filter(buisness_area_code__gt=0).all()
        results = []
        for country in country_list:
            # set tenant for country
            connection.set_tenant(country)
            # get count for agreements
            country_interventions_count = PCA.objects.filter(
                status=PCA.ACTIVE
            ).count()

            results.append({
                "countryName": country.name,
                "totalActiveInterventions": country_interventions_count
            })
        return Response(results)

