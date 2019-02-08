import hashlib
from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()


class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class HashableDict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))


def get_current_year():
    return datetime.today().year


def get_quarter(retrieve_date=None):
    if not retrieve_date:
        retrieve_date = datetime.today()
    month = retrieve_date.month
    if 0 < month <= 3:
        quarter = 'q1'
    elif 3 < month <= 6:
        quarter = 'q2'
    elif 6 < month <= 9:
        quarter = 'q3'
    else:
        quarter = 'q4'
    return quarter


def h11(w):
    return hashlib.md5(w).hexdigest()[:9]
