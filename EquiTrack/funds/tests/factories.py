import datetime

import factory
from factory import fuzzy

from funds import models
from EquiTrack.factories import InterventionFactory


class DonorFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Donor

    name = fuzzy.FuzzyText(length=45)


class GrantFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Grant

    donor = factory.SubFactory(DonorFactory)
    name = fuzzy.FuzzyText(length=32)


class FundsCommitmentItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.FundsCommitmentItem

    fund_commitment = factory.SubFactory('funds.tests.factories.FundsCommitmentHeaderFactory')
    line_item = fuzzy.FuzzyText(length=5)


class FundsReservationHeaderFactory(factory.DjangoModelFactory):
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

    start_date = fuzzy.FuzzyDate(
        datetime.date(datetime.date.today().year, 1, 1) - datetime.timedelta(days=10),
        datetime.date(datetime.date.today().year, 1, 1)
    )
    end_date = fuzzy.FuzzyDate(
        datetime.date(datetime.date.today().year + 1, 1, 1),
        datetime.date(datetime.date.today().year + 1, 1, 1) + datetime.timedelta(days=10)
    )


class FundsReservationItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.FundsReservationItem

    fund_reservation = factory.SubFactory(FundsReservationHeaderFactory)
    line_item = fuzzy.FuzzyText(length=5)


class FundsCommitmentHeaderFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.FundsCommitmentHeader
