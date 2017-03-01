from __future__ import unicode_literals

from time import time
from StringIO import StringIO

from t2f.vision import InvoiceUpdater

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import TravelExpenseType
from t2f.helpers import InvoiceMaker

from t2f.models import Travel, Expense, CostAssignment, InvoiceItem, Invoice
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory, WBSFactory, GrantFactory, FundFactory


class VisionXML(APITenantTestCase):
    def setUp(self):
        super(VisionXML, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.traveler = UserFactory()

        profile = self.traveler.profile
        profile.vendor_number = 'user0001'
        profile.save()

        country = profile.country
        country.business_area_code = '0060'
        country.save()

    def make_invoice_updater(self):
        root = ET.Element('ta_invoice_acks')
        for invoice in Invoice.objects.filter(status=Invoice.PROCESSING):
            main = ET.SubElement(root, 'ta_invoice_ack')
            ET.SubElement(main, InvoiceUpdater.REFERENCE_NUMBER_FIELD).text = invoice.reference_number
            ET.SubElement(main, InvoiceUpdater.STATUS_FIELD).text = 'success'
            ET.SubElement(main, InvoiceUpdater.MESSAGE_FIELD).text = 'explanation'
            ET.SubElement(main, InvoiceUpdater.VISON_REFERENCE_NUMBER_FIELD).text = 'vision_fi'

        return ET.tostring(root)

    def test_invoice_making(self):
        def make_invoices(travel):
            maker = InvoiceMaker(travel)
            maker.do_invoicing()

        # Currencies
        huf = CurrencyFactory(name='HUF',
                              code='huf')

        # Add wbs/grant/fund
        wbs_1 = WBSFactory(name='WBS #1')
        grant_1 = GrantFactory(name='Grant #1')
        wbs_1.grants.add(grant_1)
        fund_1 = FundFactory(name='Fund #1')
        grant_1.funds.add(fund_1)

        # Expense types
        et_t_food = ExpenseTypeFactory(title='Food', vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)

        # Make a travel
        travel = Travel.objects.create(traveler=self.traveler,
                                       supervisor=self.unicef_staff,
                                       currency=huf)

        # Add expenses
        Expense.objects.create(travel=travel,
                               type=et_t_food,
                               document_currency=huf,
                               account_currency=huf,
                               amount=35)

        # Add cost assignments
        CostAssignment.objects.create(travel=travel,
                                      share=100,
                                      wbs=wbs_1,
                                      grant=grant_1,
                                      fund=fund_1)

        # Generate invoice
        make_invoices(travel)

        response = self.forced_auth_req('get', reverse('t2f:vision_invoice_export'), user=self.unicef_staff)
        xml_data = response.content

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
        xml_data = response.content

        self.assertEqual(xml_data, "<?xml version='1.0' encoding='UTF-8'?>\n<ta_invoices />")
