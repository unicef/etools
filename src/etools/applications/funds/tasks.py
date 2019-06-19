import datetime

from django.db import connection

from etools.applications.funds.models import FundsReservationHeader
from etools.applications.funds.synchronizers import DelegatedFundReservationsSynchronizer

from etools.applications.users.models import Country
from etools.config.celery import app


def sync_single_delegated_fr(business_area_code, fr_number):
    handler = DelegatedFundReservationsSynchronizer(
        business_area_code=business_area_code,
        object_number=fr_number
    )
    handler.sync()


@app.task(name="sync_business_area_delegated_frs")
def sync_country_delegated_fr(business_area_code):
    # this does not acct for leap years but roughly should be good enough
    one_year_back = (datetime.datetime.now() - datetime.timedelta(weeks=52)).date()

    for country in Country.objects.exclude(name='Global', vision_sync_enabled=False).\
            filter(business_area_code=business_area_code):
        connection.set_tenant(country)

        qs = FundsReservationHeader.objects.exclude(completed_flag=True).filter(delegated=True, end_date__gt=one_year_back)
        for delegated_fr in qs.values_list('fr_number', flat=True):
            sync_single_delegated_fr(country.business_area_code, delegated_fr)


@app.task(name="sync_all_delegated_frs")
def sync_all_delegated_frs():
    """Check validity and save changed status (if any) for agreements that meet all of the following criteria --
        - signed
        - end date is after today
        - type != SSFA
    """
    qs = Country.objects.exclude(name='Global', vision_sync_enabled=False)
    for country in qs.all():
        sync_country_delegated_fr.delay(country.business_area_code)
