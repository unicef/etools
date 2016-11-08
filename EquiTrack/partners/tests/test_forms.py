import datetime
from datetime import timedelta

#from tenant_schemas.test.cases import TenantTestCase
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from django.db.models.fields.related import ManyToManyField

from EquiTrack.factories import PartnershipFactory, AgreementFactory, ResultStructureFactory, CountryProgrammeFactory
from partners.models import (
    PartnerOrganization,
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
    fixtures = ['initial_data.json']
    def setUp(self):
        self.date = datetime.date.today()
        self.tenant.country_short_code = 'LEBA'
        self.tenant.save()
        self.text = 'LEBA/{{}}{}01'.format(self.date.year)
        self.agreement = AgreementFactory()
        self.result_structure = ResultStructureFactory()
        self.country_programme = CountryProgrammeFactory()

    def create_form(self, data=None, instance=None, user=None):
        agr_dict = to_dict(self.agreement)
        if data:
            for k, v in data.iteritems():
                agr_dict[k] = v

        instance = instance if instance else self.agreement
        form = AgreementForm(data=agr_dict, instance=instance)
        # form.request.user = user if user else self.agreement.owner
        return form

    def test_form_start__date_signed_partner(self):
        agr_dict = to_dict(self.agreement)
        partner = PartnerOrganization.objects.get(id=self.agreement.partner.id)
        partner.partner_type = u'Civil Society Organization'
        partner.save()

        agr_dict['agreement_type'] = Agreement.PCA
        agr_dict['signed_by_unicef_date'] = self.date - timedelta(days=1)
        agr_dict['signed_by_partner_date'] = self.date
        # agr_dict['end'] = self.date + timedelta(days=50)
        form = self.create_form(data=agr_dict)
        self.assertTrue(form.is_valid())
        agr = form.save()
        self.assertEqual(agr.start, agr_dict['signed_by_partner_date'])
        self.assertIsNotNone(agr.end)

    def test_form_start__date_signed_unicef(self):
        agr_dict = to_dict(self.agreement)
        partner = PartnerOrganization.objects.get(id=self.agreement.partner.id)
        partner.partner_type = u'Civil Society Organization'
        partner.save()

        agr_dict['agreement_type'] = Agreement.PCA
        agr_dict['signed_by_unicef_date'] = self.date
        agr_dict['signed_by_partner_date'] = self.date - timedelta(days=1)
        form = self.create_form(data=agr_dict)
        self.assertTrue(form.is_valid())
        agr = form.save()
        self.assertEqual(agr.start, agr_dict['signed_by_unicef_date'])
        self.assertIsNotNone(agr.end)

    def test_start_greater_than_end(self):
        agr_dict = to_dict(self.agreement)
        partner = PartnerOrganization.objects.get(id=self.agreement.partner.id)
        partner.partner_type = u'Civil Society Organization'
        partner.save()

        agr_dict['start'] = self.date + timedelta(days=1)
        agr_dict['end'] = self.date
        form = self.create_form(data=agr_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['end'][0],
            AgreementForm.ERROR_MESSAGES['end_date']
        )

    def test_start_greater_than_signed_dates(self):
        agr_dict = to_dict(self.agreement)
        partner = PartnerOrganization.objects.get(id=self.agreement.partner.id)
        partner.partner_type = u'Civil Society Organization'
        partner.save()
        agr_dict['start'] = self.date
        agr_dict['end'] = self.date + timedelta(days=10)
        agr_dict['signed_by_unicef_date'] = self.date
        agr_dict['signed_by_partner_date'] = self.date + timedelta(days=1)
        form = self.create_form(data=agr_dict)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['start'][0],
            AgreementForm.ERROR_MESSAGES['start_date_val']
        )


