from __future__ import unicode_literals

import logging

from django.core.exceptions import ObjectDoesNotExist

from t2f.models import Invoice

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


log = logging.getLogger(__name__)


class InvoiceExport(object):
    def __init__(self, invoice_list):
        self.invoice_list = invoice_list

    def generate_xml(self):
        root = ET.Element('invoices')

        for invoice in self.invoice_list:
            self.generate_invoice_structure(root, invoice)

        return self.generate_tree(root)

    def generate_invoice_structure(self, root, invoice):
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

        for invoice_ack in self.root.iter('ta_invoice_ack'):
            invoice_number = invoice_ack.find('invoice_reference').text
            status = invoice_ack.find('status').text
            message = invoice_ack.find('message').text
            vision_fi_id = invoice_ack.find('vision_fi_doc').text

            try:
                invoice = Invoice.objects.get(reference_number=invoice_number)
            except ObjectDoesNotExist:
                log.error('Cannot find invoice with reference number %s', invoice_number)
                continue

            status = status.lower()

            if status not in possible_statuses:
                log.error('Invalid invoice (%s) status: %s', invoice_number, status)
                continue

            invoice.status = status
            invoice.message = message
            invoice.vision_fi_id = vision_fi_id
            invoice.save()
