from datetime import date

from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.views.generic import View

from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import (
    Country,
    Section,
    UserProfile
)
from partners.models import (
    Agreement,
)


class PortalDashView(View):

    def get(self, request):
        with open(settings.SITE_ROOT + '/templates/frontend/management/management.html', 'r') as my_f:
            result = my_f.read()
        return HttpResponse(result)


class ActiveUsersSection(APIView):
    """
    Gets the list of active Users in all countries
    """
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


class AgreementsStatisticsView(APIView):
    """
    Gets the list of all Agreements in all countries
    """
    model = Agreement

    def get(self, request, **kwargs):
        today = date.today()
        # get all the countries:
        country_list = Country.objects.exclude(schema_name='public').all()
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
