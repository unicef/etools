from datetime import date

from django.db import connection
from django.views.generic import TemplateView

from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.partners.models import Agreement
from etools.applications.users.models import Country, UserProfile
from etools.applications.vision.models import VisionSyncLog


class PortalDashView(TemplateView):
    template_name = 'portal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        last_ad = getattr(VisionSyncLog.objects.filter(successful=True, handler_name__in=[
            'ProgrammeSynchronizer', 'RAMSynchronizer', 'PartnerSynchronizer', 'FundReservationsSynchronizer',
            'FundCommitmentSynchronizer']).order_by('date_processed').last(), 'date_processed', '-')

        last_vision = getattr(VisionSyncLog.objects.filter(successful=True, handler_name__in=[
            'UserADSync', 'UserADSyncDelta']).order_by('date_processed').last(), 'date_processed', '-')

        context.update({
            'active_users': UserProfile.objects.filter(user__is_staff=True, user__is_active=True).count(),
            'countries': Country.objects.filter(vision_sync_enabled=True).count(),
            'last_ad_sync': last_ad,
            'last_vision_sync': last_vision,
        })
        return context


class ActiveUsers(APIView):
    """
    """
    model = UserProfile

    def get(self, request, **kwargs):
        country_list = Country.objects.values_list('name', flat=True)

        results = []
        for country in country_list:
            country_records = {}
            user_qry = UserProfile.objects.filter(
                user__is_staff=True,
                user__is_active=True,
                country__name=country
            )
            country_records[country] = {
                'total': user_qry.count()
            }

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
