
import datetime

import factory
from factory import fuzzy

from etools.applications.funds import models
from etools.applications.partners.tests.factories import InterventionFactory


class DonorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Donor

    name = fuzzy.FuzzyText(length=45)


class GrantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Grant

    donor = factory.SubFactory(DonorFactory)
    name = fuzzy.FuzzyText(length=32)


class FundsCommitmentItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FundsCommitmentItem

    fund_commitment = factory.SubFactory('etools.applications.funds.tests.factories.FundsCommitmentHeaderFactory')
    line_item = fuzzy.FuzzyText(length=5)


class FundsReservationHeaderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FundsReservationHeader

    intervention = factory.SubFactory(InterventionFactory)
    vendor_code = fuzzy.FuzzyText(length=20)
    fr_number = fuzzy.FuzzyText(length=20)
    document_date = datetime.date(datetime.date.today().year, 1, 1)
    fr_type = fuzzy.FuzzyText(length=20)
    currency = fuzzy.FuzzyText(length=20)
    document_text = fuzzy.FuzzyText(length=20)

    # this is the field required for validation
    intervention_amt = fuzzy.FuzzyDecimal(1, 300)
    # overall_amount
    total_amt = fuzzy.FuzzyDecimal(1, 300)
    actual_amt = fuzzy.FuzzyDecimal(1, 300)
    outstanding_amt = fuzzy.FuzzyDecimal(1, 300)

    total_amt_local = fuzzy.FuzzyDecimal(1, 300)
    actual_amt_local = fuzzy.FuzzyDecimal(1, 300)
    outstanding_amt_local = fuzzy.FuzzyDecimal(1, 300)

    start_date = fuzzy.FuzzyDate(
        datetime.date(datetime.date.today().year, 1, 1) - datetime.timedelta(days=10),
        datetime.date(datetime.date.today().year, 1, 1)
    )
    end_date = fuzzy.FuzzyDate(
        datetime.date(datetime.date.today().year + 1, 1, 1),
        datetime.date(datetime.date.today().year + 1, 1, 1) + datetime.timedelta(days=10)
    )


class FundsReservationItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FundsReservationItem

    fund_reservation = factory.SubFactory(FundsReservationHeaderFactory)
    line_item = fuzzy.FuzzyInteger(low=1, high=300)


class FundsCommitmentHeaderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FundsCommitmentHeader
