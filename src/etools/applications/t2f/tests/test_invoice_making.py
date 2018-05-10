
import xml.etree.ElementTree as ET
from datetime import datetime

from django.core.urlresolvers import reverse

from pytz import UTC

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.publics.models import TravelExpenseType
from etools.applications.publics.tests.factories import (PublicsCurrencyFactory, PublicsDSARateFactory,
                                                         PublicsDSARegionFactory, PublicsFundFactory,
                                                         PublicsGrantFactory, PublicsTravelExpenseTypeFactory,
                                                         PublicsWBSFactory,)
from etools.applications.t2f.helpers.invoice_maker import InvoiceMaker
from etools.applications.t2f.models import CostAssignment, Expense, Invoice, InvoiceItem, Travel
from etools.applications.t2f.tests.factories import ItineraryItemFactory
from etools.applications.t2f.vision import InvoiceUpdater
from etools.applications.users.tests.factories import UserFactory


class InvoiceMaking(BaseTenantTestCase):
    def setUp(self):
        super(InvoiceMaking, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.traveler = UserFactory()

        profile = self.traveler.profile
        profile.vendor_number = 'user0001'
        profile.save()

        country = profile.country
        country.business_area_code = '0060'
        country.save()

        dsa_region = PublicsDSARegionFactory()
        PublicsDSARateFactory(region=dsa_region)

        # Currencies
        self.huf = PublicsCurrencyFactory(name='HUF', code='huf')
        self.usd = PublicsCurrencyFactory(name='USD', code='usd')

        # Add wbs/grant/fund
        self.wbs_1 = PublicsWBSFactory(name='WBS #1')
        self.wbs_2 = PublicsWBSFactory(name='WBS #2')

        self.grant_1 = PublicsGrantFactory(name='Grant #1')
        self.grant_2 = PublicsGrantFactory(name='Grant #2')
        self.grant_3 = PublicsGrantFactory(name='Grant #3')

        self.wbs_1.grants.add(self.grant_1)
        self.wbs_2.grants.add(self.grant_2, self.grant_3)

        self.fund_1 = PublicsFundFactory(name='Fund #1')
        self.fund_2 = PublicsFundFactory(name='Fund #4')

        self.grant_1.funds.add(self.fund_1)
        self.grant_3.funds.add(self.fund_2)

        # Expense types
        self.et_t_food = PublicsTravelExpenseTypeFactory(
            title='Food',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        self.et_t_travel = PublicsTravelExpenseTypeFactory(
            title='Travel',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        self.et_t_other = PublicsTravelExpenseTypeFactory(
            title='Other',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )

        self.et_a_nico = PublicsTravelExpenseTypeFactory(
            title='Nico Travel',
            vendor_number='a_nico'
        )
        self.et_a_torben = PublicsTravelExpenseTypeFactory(
            title='Torben Travel',
            vendor_number='a_torben'
        )

        # Make a travel
        self.travel = Travel.objects.create(traveler=self.traveler,
                                            supervisor=self.unicef_staff,
                                            currency=self.huf)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 5, 10, tzinfo=UTC),
                             arrival_date=datetime(2017, 5, 11, tzinfo=UTC),
                             dsa_region=dsa_region)
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 5, 20, tzinfo=UTC),
                             arrival_date=datetime(2017, 5, 21, tzinfo=UTC),
                             dsa_region=dsa_region)

    def update_invoices(self, status='success'):
        root = ET.Element('ta_invoice_acks')
        for invoice in Invoice.objects.filter(status=Invoice.PROCESSING):
            main = ET.SubElement(root, 'ta_invoice_ack')
            ET.SubElement(main, InvoiceUpdater.REFERENCE_NUMBER_FIELD).text = invoice.reference_number
            ET.SubElement(main, InvoiceUpdater.STATUS_FIELD).text = status
            ET.SubElement(main, InvoiceUpdater.MESSAGE_FIELD).text = 'explanation'
            ET.SubElement(main, InvoiceUpdater.VISON_REFERENCE_NUMBER_FIELD).text = 'vision_fi'

        updater_xml_structure = ET.tostring(root)

        # Update invoices like vision would do it
        response = self.forced_auth_req('post', reverse('t2f:vision_invoice_update'),
                                        data=updater_xml_structure,
                                        user=self.unicef_staff,
                                        request_format=None,
                                        content_type='text/xml')
        self.assertEqual(response.status_code, 200, response.content)

    def make_invoices(self, travel):
        maker = InvoiceMaker(travel)
        maker.do_invoicing()

    def make_invoice_number(self, business_area_code, travel_reference_number, counter):
        return '{}/{}/{:02d}'.format(business_area_code,
                                     travel_reference_number,
                                     counter)

    def test_invoice_making(self):
        # Add expenses
        Expense.objects.create(travel=self.travel,
                               type=self.et_t_food,
                               currency=self.huf,
                               amount=35)

        Expense.objects.create(travel=self.travel,
                               type=self.et_t_travel,
                               currency=self.huf,
                               amount=50)

        expense_other = Expense.objects.create(travel=self.travel,
                                               type=self.et_t_other,
                                               currency=self.huf,
                                               amount=15)

        # Amount == None
        Expense.objects.create(travel=self.travel,
                               type=self.et_t_travel,
                               currency=self.huf,
                               amount=None)

        # Add cost assignments
        ca_1 = CostAssignment.objects.create(travel=self.travel,
                                             share=70,
                                             wbs=self.wbs_1,
                                             grant=self.grant_1,
                                             fund=self.fund_1)
        ca_2 = CostAssignment.objects.create(travel=self.travel,
                                             share=30,
                                             wbs=self.wbs_2,
                                             grant=self.grant_3,
                                             fund=self.fund_2)

        # Do the testing
        self.assertEqual(self.travel.invoices.all().count(), 0)
        self.assertEqual(InvoiceItem.objects.all().count(), 0)

        # Generate invoice
        self.make_invoices(self.travel)

        self.assertEqual(self.travel.invoices.all().count(), 1)
        self.assertEqual(InvoiceItem.objects.all().count(), 2)

        self.forced_auth_req('get', reverse('t2f:vision_invoice_export'), user=self.unicef_staff)

        self.assertEqual(Invoice.objects.filter(status=Invoice.PENDING).count(), 0)
        self.assertEqual(Invoice.objects.filter(status=Invoice.PROCESSING).count(), 1)
        self.assertEqual(Invoice.objects.filter(status=Invoice.SUCCESS).count(), 0)
        self.assertEqual(Invoice.objects.filter(status=Invoice.ERROR).count(), 0)

        last_invoice = Invoice.objects.last()
        self.assertEqual(last_invoice.reference_number,
                         self.make_invoice_number(self.traveler.profile.country.business_area_code,
                                                  self.travel.reference_number,
                                                  1))

        self.update_invoices()

        self.assertEqual(Invoice.objects.filter(status=Invoice.PENDING).count(), 0)
        self.assertEqual(Invoice.objects.filter(status=Invoice.PROCESSING).count(), 0)
        self.assertEqual(Invoice.objects.filter(status=Invoice.SUCCESS).count(), 1)
        self.assertEqual(Invoice.objects.filter(status=Invoice.ERROR).count(), 0)

        # Add more stuff
        expense_other.amount = 45
        expense_other.save()

        Expense.objects.create(travel=self.travel,
                               type=self.et_a_nico,
                               currency=self.huf,
                               amount=1000)
        Expense.objects.create(travel=self.travel,
                               type=self.et_a_torben,
                               currency=self.huf,
                               amount=500)

        # Generate invoice
        self.make_invoices(self.travel)

        self.update_invoices()

        self.assertEqual(Invoice.objects.filter(status=Invoice.PENDING).count(), 3)
        self.assertEqual(Invoice.objects.filter(status=Invoice.PROCESSING).count(), 0)
        self.assertEqual(Invoice.objects.filter(status=Invoice.SUCCESS).count(), 1)
        self.assertEqual(Invoice.objects.filter(status=Invoice.ERROR).count(), 0)

        self.assertEqual(self.travel.invoices.all().count(), 4)
        self.assertEqual(InvoiceItem.objects.all().count(), 8)

        preserved_existing_invoice_ids = [i.id for i in Invoice.objects.all()]

        last_invoice = Invoice.objects.last()
        self.assertEqual(last_invoice.reference_number,
                         self.make_invoice_number(self.traveler.profile.country.business_area_code,
                                                  self.travel.reference_number,
                                                  4))

        # Remove a cost assignment
        ca_1.share = 100
        ca_1.save()
        ca_2.delete()

        # Generate invoice
        self.make_invoices(self.travel)

        self.assertEqual(Invoice.objects.filter(status=Invoice.PENDING).count(), 3)
        self.assertEqual(Invoice.objects.filter(status=Invoice.PROCESSING).count(), 0)
        self.assertEqual(Invoice.objects.filter(status=Invoice.SUCCESS).count(), 1)
        self.assertEqual(Invoice.objects.filter(status=Invoice.ERROR).count(), 0)

        self.assertEqual(self.travel.invoices.all().count(), 4)
        self.assertEqual(InvoiceItem.objects.all().count(), 6)

        # Check here if any new invoice was generated and some was deleted
        existing_invoice_ids = [i.id for i in Invoice.objects.all()]
        self.assertNotEqual(existing_invoice_ids, preserved_existing_invoice_ids)

        last_invoice = Invoice.objects.last()
        self.assertEqual(last_invoice.reference_number,
                         self.make_invoice_number(self.traveler.profile.country.business_area_code,
                                                  self.travel.reference_number,
                                                  4))
