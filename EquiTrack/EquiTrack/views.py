import datetime

from django.views.generic import TemplateView
from django.db.models import Q
from django.contrib.admin.models import LogEntry
from partners.models import PCA, PartnerOrganization, GwPCALocation
from reports.models import Sector, Indicator
from locations.models import CartoDBTable, GatewayType
from funds.models import Donor
from trips.models import Trip, ActionPoint


class MainView(TemplateView):
    template_name = 'choose_login.html'

class OutdatedBrowserView(TemplateView):
    template_name = 'outdated_browser.html'
