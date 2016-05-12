__author__ = 'jcranwellward'
import datetime

from django.views.generic import TemplateView
from django.db.models import Q
from django.contrib.admin.models import LogEntry

from partners.models import PCA, PartnerOrganization
from reports.models import Sector, ResultStructure, Indicator
from locations.models import CartoDBTable, GatewayType, Governorate, Region
from funds.models import Donor
from trips.models import Trip, ActionPoint


class MainView(TemplateView):
    template_name = 'choose_login.html'


class DashboardView(TemplateView):
    """
    Returns context for the dashboard template
    """
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):

        sectors = {}
        now = datetime.datetime.now()
        structure_id = self.request.GET.get('structure')
        if structure_id is None and ResultStructure.objects.count():
            structure_id = ResultStructure.objects.filter(
                from_date__lte=now,
                to_date__gte=now
            ).values_list('id',  flat=True).first()
        try:
            current_structure = ResultStructure.objects.get(id=structure_id)
        except ResultStructure.DoesNotExist:
            current_structure = None
        for sector in Sector.objects.all():
            indicators = sector.indicator_set.filter(
                view_on_dashboard=True,
            )
            if current_structure:
                indicators = indicators.filter(
                    result_structure=current_structure
                )
            if not indicators:
                continue

            sectors[sector.name] = []
            for indicator in indicators:
                programmed = indicator.programmed(
                    result_structure=current_structure
                )
                current = indicator.progress(
                    result_structure=current_structure
                )
                sectors[sector.name].append(
                    {
                        'indicator': indicator,
                        'programmed': programmed,
                        'current': current
                    }
                )

        return {
            'sectors': sectors,
            'current_structure': current_structure,
            'structures': ResultStructure.objects.all(),
            'pcas': {
                'active': PCA.objects.filter(
                    result_structure=current_structure,
                    status=PCA.ACTIVE,
                ).count(),
                'implemented': PCA.objects.filter(
                    result_structure=current_structure,
                    status=PCA.IMPLEMENTED,
                ).count(),
                'in_process': PCA.objects.filter(
                    result_structure=current_structure,
                    status=PCA.IN_PROCESS,
                ).count(),
                'cancelled': PCA.objects.filter(
                    result_structure=current_structure,
                    status=PCA.CANCELLED,
                ).count(),
            }
        }


class MapView(TemplateView):

    template_name = 'map.html'

    def get_context_data(self, **kwargs):
        return {
            'tables': CartoDBTable.objects.all(),
            'gateway_list': GatewayType.objects.all(),
            'governorate_list': Governorate.objects.all(),
            'sectors_list': Sector.objects.all(),
            'result_structure_list': ResultStructure.objects.all(),
            'region_list': Region.objects.all(),
            'partner_list': PartnerOrganization.objects.all(),
            'indicator_list': Indicator.objects.all(),
            'donor_list': Donor.objects.all(),
            'lat': self.request.user.profile.country.latitude,
            'lng': self.request.user.profile.country.longitude,
            'zoom': self.request.user.profile.country.initial_zoom,
        }


class CmtDashboardView(MapView):

    template_name = 'cmt_dashboard.html'


class UserDashboardView(TemplateView):
    template_name = 'user_dashboard.html'

    def get_context_data(self, **kwargs):
        user = self.request.user

        return {
            'trips_current': Trip.objects.filter(
                Q(status=Trip.PLANNED) | Q(status=Trip.SUBMITTED) | Q(status=Trip.APPROVED),
                owner=user),
            'trips_previous': Trip.objects.filter(
                Q(status=Trip.COMPLETED) | Q(status=Trip.CANCELLED),
                owner=user),
            'trips_supervised': user.supervised_trips.filter(
                Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED)),
            'log': LogEntry.objects.select_related().filter(
                user=self.request.user).order_by("-id")[:10],
            'pcas': PCA.objects.filter(unicef_managers=user).filter(
                Q(status=PCA.ACTIVE) | Q(status=PCA.IN_PROCESS)
            ).order_by("number", "-created_at")[:10],
            'action_points': ActionPoint.objects.filter(
                Q(status='open') | Q(status='ongoing'),
                person_responsible=user).order_by("-due_date")[:10]
        }


class HACTDashboardView(TemplateView):

    template_name = 'hact/dashboard.html'

    def get_context_data(self, **kwargs):
        return {
            'partners': PartnerOrganization.objects.filter(
                documents__status__in=[
                    PCA.ACTIVE,
                    PCA.IMPLEMENTED
                ]
            ).distinct()
        }
