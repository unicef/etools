
import xml.etree.ElementTree as ET
from datetime import datetime

from django.core.urlresolvers import reverse

from pytz import UTC

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import URLAssertionMixin
from etools.applications.publics.models import TravelExpenseType
from etools.applications.publics.tests.factories import (PublicsCurrencyFactory, PublicsDSARateFactory,
                                                         PublicsDSARegionFactory, PublicsFundFactory,
                                                         PublicsGrantFactory, PublicsTravelExpenseTypeFactory,
                                                         PublicsWBSFactory,)
from etools.applications.t2f.helpers.invoice_maker import InvoiceMaker
from etools.applications.t2f.models import CostAssignment, Expense, Invoice, Travel
from etools.applications.t2f.tests.factories import ItineraryItemFactory
from etools.applications.t2f.vision import InvoiceUpdater
from etools.applications.users.tests.factories import UserFactory


class VisionXML(URLAssertionMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.traveler = UserFactory()

        profile = cls.traveler.profile
        profile.vendor_number = 'user0001'
        profile.staff_id = 'staff001'
        profile.save()

        country = profile.country
        country.business_area_code = '0060'
        country.save()

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('vision_invoice_export', 'vision_invoice_export/', {}),
            ('vision_invoice_update', 'vision_invoice_update/', {}),
        )
        self.assertReversal(names_and_paths, 't2f:', '/api/t2f/')

    def make_invoice_updater(self, status=Invoice.SUCCESS):
        root = ET.Element('ta_invoice_acks')
        for invoice in Invoice.objects.filter(status__in=[Invoice.PROCESSING, Invoice.PENDING]):
            main = ET.SubElement(root, 'ta_invoice_ack')
            ET.SubElement(main, InvoiceUpdater.REFERENCE_NUMBER_FIELD).text = invoice.reference_number
            ET.SubElement(main, InvoiceUpdater.STATUS_FIELD).text = status
            ET.SubElement(main, InvoiceUpdater.MESSAGE_FIELD).text = 'explanation'
            ET.SubElement(main, InvoiceUpdater.VISON_REFERENCE_NUMBER_FIELD).text = 'vision_fi'

        return ET.tostring(root)

    def make_invoices(self, travel):
        maker = InvoiceMaker(travel)
        maker.do_invoicing()

    def prepare_travel(self):
        # Currencies
        huf = PublicsCurrencyFactory(name='HUF', code='huf')

        # Add wbs/grant/fund
        wbs_1 = PublicsWBSFactory(name='WBS #1')
        grant_1 = PublicsGrantFactory(name='Grant #1')
        wbs_1.grants.add(grant_1)
        fund_1 = PublicsFundFactory(name='Fund #1')
        grant_1.funds.add(fund_1)

        dsa_region = PublicsDSARegionFactory()
        PublicsDSARateFactory(region=dsa_region)

        # Expense types
        et_t_food = PublicsTravelExpenseTypeFactory(
            title='Food',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )

        # Make a travel
        travel = Travel.objects.create(traveler=self.traveler,
                                       supervisor=self.unicef_staff,
                                       currency=huf)

        # Add expenses
        Expense.objects.create(travel=travel,
                               type=et_t_food,
                               currency=huf,
                               amount=35)

        ItineraryItemFactory(travel=travel,
                             departure_date=datetime(2017, 5, 10, tzinfo=UTC),
                             arrival_date=datetime(2017, 5, 11, tzinfo=UTC),
                             dsa_region=dsa_region)
        ItineraryItemFactory(travel=travel,
                             departure_date=datetime(2017, 5, 20, tzinfo=UTC),
                             arrival_date=datetime(2017, 5, 21, tzinfo=UTC),
                             dsa_region=dsa_region)

        # Add cost assignments
        CostAssignment.objects.create(travel=travel,
                                      share=100,
                                      wbs=wbs_1,
                                      grant=grant_1,
                                      fund=fund_1)

        return travel

    def test_invoice_making(self):
        travel = self.prepare_travel()

        # Generate invoice
        self.make_invoices(travel)

        response = self.forced_auth_req('get', reverse('t2f:vision_invoice_export'), user=self.unicef_staff)
        xml_data = response.content.decode('utf-8')

        self.assertFalse(xml_data.startswith('"'))
        self.assertFalse(xml_data.endswith('"'))

        updater_xml_structure = self.make_invoice_updater()

        # Update invoices like vision would do it
        self.forced_auth_req('post', reverse('t2f:vision_invoice_update'),
                             data=updater_xml_structure,
                             user=self.unicef_staff,
                             request_format=None,
                             content_type='text/xml')

        response = self.forced_auth_req('get', reverse('t2f:vision_invoice_export'), user=self.unicef_staff)
        xml_data = response.content.decode('utf-8')

        self.assertEqual(xml_data, "<?xml version='1.0' encoding='utf-8'?>\n<ta_invoices />")

    def test_error_mail(self):
        travel = self.prepare_travel()

        self.make_invoices(travel)

        updater_xml_structure = self.make_invoice_updater(Invoice.ERROR)

        # Update invoices like vision would do it
        response = self.forced_auth_req('post', reverse('t2f:vision_invoice_update'),
                                        data=updater_xml_structure,
                                        user=self.unicef_staff,
                                        request_format=None,
                                        content_type='text/xml')
        self.assertEqual(response.status_code, 200)

    def test_personal_number_usage(self):
        travel = self.prepare_travel()

        travel_agent_expense_type = PublicsTravelExpenseTypeFactory(
            title='Travel Agent',
            vendor_number='trav01'
        )

        eur = PublicsCurrencyFactory(name='EUR', code='eur')

        # Add expenses
        Expense.objects.create(travel=travel,
                               type=travel_agent_expense_type,
                               currency=eur,
                               amount=35)

        # Generate invoice
        self.make_invoices(travel)

        response = self.forced_auth_req('get', reverse('t2f:vision_invoice_export'), user=self.unicef_staff)
        xml_data = response.content.decode('utf-8')

        self.assertEqual(xml_data.count('<pernr />'), 1)
        self.assertEqual(xml_data.count('<pernr>{}</pernr>'.format(self.traveler.profile.staff_id)), 1)
