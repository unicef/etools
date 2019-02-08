from django.conf import settings
from django.contrib.sites.models import Site


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()
