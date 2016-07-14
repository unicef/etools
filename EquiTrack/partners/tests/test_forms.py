import datetime
from datetime import timedelta

from tenant_schemas.test.cases import TenantTestCase

from django.db.models.fields.related import ManyToManyField

from EquiTrack.factories import PartnershipFactory, AgreementFactory
from reports.models import ResultStructure
from partners.models import (
    PCA,
    Agreement,
    AmendmentLog,
    FundingCommitment,
    PartnershipBudget,
    AgreementAmendmentLog,
)
from partners.forms import AgreementForm


def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                data[f.name] = list(f.value_from_object(instance).values_list('pk', flat=True))
        else:
            data[f.name] = f.value_from_object(instance)
    return data


class TestAgreementForm(TenantTestCase):

    def setUp(self):
        self.date = datetime.date.today()
        self.tenant.country_short_code = 'LEBA'
        self.tenant.save()
        self.text = 'LEBA/{{}}{}01'.format(self.date.year)
        self.agreement = AgreementFactory()

    def create_form(self, data=None, instance=None, user=None):
        trip_dict = to_dict(self.trip)
        if data:
            for k, v in data.iteritems():
                trip_dict[k] = v

        instance = instance if instance else self.agreement
        form = AgreementForm(data=trip_dict, instance=instance)
        # form.request.user = user if user else self.agreement.owner
        return form

    def test_form_start_end_date_autopopulate(self):
        agr_dict = to_dict(self.agreement)
        agr_dict['agreement_type'] = Agreement.PCA
        agr_dict['signed_by_unicef_date'] = self.date - timedelta(days=1)
        agr_dict['signed_by_partner_date'] = self.date
        form = self.create_form(data=agr_dict)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.start, self.date)