from __future__ import division

__author__ = 'jcranwellward'
import datetime
import json
import platform

from dealer.git import git

from django.views.generic import TemplateView
from django.db.models import Q
from django.contrib.admin.models import LogEntry
from django.http.response import HttpResponse

from partners.models import PCA, PartnerOrganization, PCASectorOutput, GwPCALocation
from reports.models import Sector, ResultStructure, Indicator
from locations.models import CartoDBTable, GatewayType, Governorate, Region
from funds.models import Donor
from trips.models import Trip, ActionPoint


class DashboardView(TemplateView):
    """
    Returns context for the dashboard template
    """
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):

        sectors = {}
        now = datetime.datetime.now()
        structure = self.request.GET.get('structure')
        if structure is None and ResultStructure.objects.count():
            structure = ResultStructure.objects.filter(
                from_date__lte=now,
                to_date__gte=now
            )[0].id
        try:
            current_structure = ResultStructure.objects.get(id=structure)
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
                    amendment_number=0,
                ).count(),
                'implemented': PCA.objects.filter(
                    result_structure=current_structure,
                    status=PCA.IMPLEMENTED,
                    amendment_number=0,
                ).count(),
                'in_process': PCA.objects.filter(
                    result_structure=current_structure,
                    status=PCA.IN_PROCESS,
                ).count(),
                'cancelled': PCA.objects.filter(
                    result_structure=current_structure,
                    status=PCA.CANCELLED,
                    amendment_number=0,
                ).count(),
            }
        }


class PartnershipsView(DashboardView):

    template_name = 'partnerships/dashboard.html'

    def get_context_data(self, **kwargs):
        data = super(PartnershipsView, self).get_context_data(**kwargs)

        active_partnerships = PCA.objects.filter(
            status=PCA.ACTIVE,
            partnership_type__in=[PCA.PD, PCA.SHPD, PCA.SSFA, PCA.DCT]
        )
        today = datetime.datetime.today()
        active_this_year = active_partnerships.filter(
            start_date__year=today.year
        )
        active_last_year = active_partnerships.filter(
            start_date__year=today.year-1
        )
        expire_in_two_months = active_partnerships.filter(
            end_date__range=[today, today + datetime.timedelta(days=60)]
        )

        govs = {}
        for gov in Governorate.objects.all():
            govs[gov.name] = GwPCALocation.objects.filter(governorate=gov, pca__status=PCA.ACTIVE).distinct('pca').count()

        data['govs'] = govs

        partners = {}
        partner_types = dict(PartnerOrganization.PARTNER_TYPES)
        for type, label in partner_types.iteritems():
            partners[label] = active_partnerships.filter(partner__type=type).count()

        data['partners'] = partners

        # (1) Number and value of Active Partnerships for this year
        data['active_count'] = active_partnerships.count()
        data['active_value'] = sum([pd.total_budget for pd in active_partnerships.all()])
        data['active_percentage'] = "{0:.0f}%".format(active_partnerships.count()/active_partnerships.count() * 100)

        # (2a) Number and value of Approved Partnerships this year
        data['active_this_year_count'] = active_this_year.count()
        data['active_this_year_value'] = sum([pd.total_budget for pd in active_this_year.all()])
        data['active_this_year_percentage'] = "{0:.0f}%".format(active_this_year.count()/active_partnerships.count() * 100)

        # (2a) Number and value of Approved Partnerships this year
        data['active_last_year_count'] = active_last_year.count()
        data['active_last_year_value'] = sum([pd.total_budget for pd in active_last_year.all()])
        data['active_last_year_percentage'] = "{0:.0f}%".format(active_last_year.count()/active_partnerships.count() * 100)

        # (3) Number and Value of Expiring Partnerships in next two months
        data['expire_in_two_months_count'] = expire_in_two_months.count()
        data['expire_in_two_months_value'] = sum([pd.total_budget for pd in expire_in_two_months.all()])
        data['expire_in_two_months_percentage'] = "{0:.0f}%".format(expire_in_two_months.count()/active_partnerships.count() * 100)

        return data


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
            'output_list': PCASectorOutput.objects.all(),
            'donor_list': Donor.objects.all()
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
            'pcas': PCA.objects.filter(
                unicef_managers=user, status=PCA.ACTIVE
            ).order_by("number", "-amendment_number")[:10],
            'action_points': ActionPoint.objects.filter(
                Q(status='open') | Q(status='ongoing'),
                person_responsible=user).order_by("-due_date")[:10]
        }


def magic_info(request):
    """
    Return JSON string with some basic state information about this server.

    You must be logged in as a staff user to access this URL.
    """
    if not request.user.is_staff:
        return HttpResponse("You must be logged in as a superuser to "
                            "perform this operation!", status=403)

    info = {'commit_id': git.revision,
            'os': platform.system(),
            'arch': platform.machine(),
            'hostname': platform.node(),
            'python': platform.python_version(),
            'server': request.META['SERVER_NAME'],
            'server_port': request.META['SERVER_PORT'],
            }

    return HttpResponse(json.dumps(info), content_type="text/json")
