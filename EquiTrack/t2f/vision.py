from __future__ import unicode_literals

from functools import wraps
import logging
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.models.query_utils import Q

from t2f.models import Invoice
from users.models import Country as Workspace

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


log = logging.getLogger(__name__)


def run_on_tenants(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        original_tenant = connection.tenant
        try:
            for workspace in Workspace.objects.exclude(Q(business_area_code='') | Q(business_area_code__isnull=True)):
                connection.set_tenant(workspace)
                func(self, workspace, *args, **kwargs)
        finally:
            connection.set_tenant(original_tenant)
    return wrapper


class InvoiceExport(object):
    def generate_xml(self):
        root = ET.Element('invoices')
        self.generate_invoices(root)
        return self.generate_tree(root)

    @run_on_tenants
    def generate_invoices(self, workspace, root):
        invoices_qs = Invoice.objects.filter(status__in=[Invoice.PENDING, Invoice.PROCESSING])
        for invoice in invoices_qs:
            self.generate_invoice_node(root, invoice)
        invoices_qs.update(status=Invoice.PROCESSING)

    def generate_invoice_node(self, root, invoice):
        main = ET.SubElement(root, 'invoice')
        self.generate_header_node(main, invoice)
        self.generate_vendor_node(main, invoice)
        self.generate_expense_nodes(main, invoice)

    def generate_header_node(self, main, invoice):
        header = ET.SubElement(main, 'header')
        ET.SubElement(header, 'reference_number').text = invoice.reference_number
        ET.SubElement(header, 'business_area').text = invoice.business_area
        ET.SubElement(header, 'currency').text = invoice.currency.code.upper()

    def generate_vendor_node(self, main, invoice):
        vendor = ET.SubElement(main, 'vendor')
        ET.SubElement(vendor, 'amount').text = str(invoice.amount)
        ET.SubElement(vendor, 'posting_key').text = self.get_posting_key(invoice.amount)
        ET.SubElement(vendor, 'vendor').text = invoice.vendor_number
        ET.SubElement(vendor, 'payment_terms')
        ET.SubElement(vendor, 'payment_method')
        ET.SubElement(vendor, 'part_type_bank')
        ET.SubElement(vendor, 'house_bank')

    def generate_expense_nodes(self, main, invoice):
        for item_no, invoice_item in enumerate(invoice.items.all()):
            self._generate_expense_node(main, invoice_item, item_no+1) # +1 to start from 1

    def _generate_expense_node(self, main, invoice_item, item_no):
        expense = ET.SubElement(main, 'expense')
        ET.SubElement(expense, 'amount').text = str(invoice_item.amount)
        ET.SubElement(expense, 'item_no').text = str(item_no)
        ET.SubElement(expense, 'posting_key').text = self.get_posting_key(invoice_item.amount)
        ET.SubElement(expense, 'wbs').text = invoice_item.wbs.name
        ET.SubElement(expense, 'grant').text = invoice_item.grant.name
        ET.SubElement(expense, 'fund').text = invoice_item.fund.name
        ET.SubElement(expense, 'pernr').text = invoice_item.invoice.travel.traveler.profile.staff_id

    def generate_tree(self, root):
        return ET.tostring(root, encoding='utf8', method='xml')

    @staticmethod
    def get_posting_key(amount):
        return 'debit' if amount >= 0 else 'credit'


class InvoiceUpdater(object):
    def __init__(self, xml_data):
        self.root = ET.fromstring(xml_data)

    def update_invoices(self):
        possible_statuses = {s[0] for s in Invoice.STATUS}

        invoice_grouping = defaultdict(list)

        for invoice_ack in self.root.iter('ta_invoice_ack'):
            invoice_number = invoice_ack.find('invoice_reference').text
            status = invoice_ack.find('status').text
            status = status.lower()

            if status not in possible_statuses:
                # TODO refine error handling
                log.error('Invalid invoice (%s) status: %s', invoice_number, status)
                continue

            data = {'invoice_number': invoice_number,
                    'status': status,
                    'message': getattr(invoice_ack.find('message'), 'text'),
                    'vision_fi_id': getattr(invoice_ack.find('vision_fi_doc'), 'text')}

            business_area_code, _ = invoice_number.split('/', 1)

            invoice_grouping[business_area_code].append(data)

        self._update_invoices_in_tenants(invoice_grouping)

    @run_on_tenants
    def _update_invoices_in_tenants(self, workspace, invoice_grouping):
        for invoice_data in invoice_grouping[workspace.business_area_code]:
            invoice_number = invoice_data['invoice_number']
            try:
                invoice = Invoice.objects.get(reference_number=invoice_number)
            except ObjectDoesNotExist:
                # TODO refine error handling
                log.error('Cannot find invoice with reference number %s', invoice_number)
                continue

            invoice.status = invoice_data['status']
            invoice.message = invoice_data['message']
            invoice.vision_fi_id = invoice_data['vision_fi_id']
            invoice.save()
