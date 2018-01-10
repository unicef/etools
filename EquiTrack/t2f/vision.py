from __future__ import unicode_literals

import logging
from collections import defaultdict
from decimal import Decimal
from functools import wraps

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail.message import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.db import connection
from django.db.models.query_utils import Q
from django.template.loader import render_to_string
from django.utils.datastructures import MultiValueDict
from django.utils.six import BytesIO

from t2f.models import Invoice
from users.models import Country as Workspace

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


log = logging.getLogger(__name__)

User = get_user_model()


class InvoiceUpdateError(Exception):
    def __init__(self, errors):
        self.errors = errors


def run_on_tenants(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        original_tenant = connection.tenant
        try:
            workspace_q = Q(business_area_code='') | Q(business_area_code__isnull=True) | Q(schema_name='public')
            for workspace in Workspace.objects.exclude(workspace_q):
                log.error('Setting tenant to %s', workspace.schema_name)
                connection.set_tenant(workspace)
                func(self, workspace, *args, **kwargs)
        finally:
            connection.set_tenant(original_tenant)
    return wrapper


class InvoiceExport(object):
    def generate_xml(self):
        root = ET.Element('ta_invoices')
        self.generate_invoices(root)
        return self.generate_tree(root)

    @run_on_tenants
    def generate_invoices(self, workspace, root):
        invoices_qs = Invoice.objects.filter(status__in=[Invoice.PENDING, Invoice.PROCESSING])
        for invoice in invoices_qs:
            self.generate_invoice_node(root, invoice)
        invoices_qs.update(status=Invoice.PROCESSING)

    def generate_invoice_node(self, root, invoice):
        main = ET.SubElement(root, 'ta_invoice')
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
        ET.SubElement(vendor, 'amount').text = str(invoice.amount.quantize(Decimal('1.000')))
        ET.SubElement(vendor, 'posting_key').text = self.get_posting_key(invoice.amount)
        ET.SubElement(vendor, 'vendor').text = invoice.vendor_number
        ET.SubElement(vendor, 'payment_terms')
        ET.SubElement(vendor, 'payment_method')
        ET.SubElement(vendor, 'part_type_bank')
        ET.SubElement(vendor, 'house_bank')

    def generate_expense_nodes(self, main, invoice):
        for item_no, invoice_item in enumerate(invoice.items.all(), start=1):
            self._generate_expense_node(main, invoice_item, item_no)

    def _generate_expense_node(self, main, invoice_item, item_no):
        expense = ET.SubElement(main, 'expense')
        ET.SubElement(expense, 'amount').text = str(invoice_item.amount.quantize(Decimal('1.000')))
        ET.SubElement(expense, 'item_no').text = str(item_no)
        ET.SubElement(expense, 'posting_key').text = self.get_posting_key(invoice_item.amount)
        ET.SubElement(expense, 'wbs').text = invoice_item.wbs.name
        ET.SubElement(expense, 'grant').text = invoice_item.grant.name
        ET.SubElement(expense, 'fund').text = invoice_item.fund.name

        invoice = invoice_item.invoice
        profile = invoice.travel.traveler.profile
        if invoice.vendor_number == profile.vendor_number:
            ET.SubElement(expense, 'pernr').text = profile.staff_id
        else:
            ET.SubElement(expense, 'pernr')

    def generate_tree(self, root):
        # https://docs.python.org/2/library/xml.etree.elementtree.html
        io = BytesIO()
        ET.ElementTree(root).write(io, encoding='UTF-8', xml_declaration=True)
        return io.getvalue()

    @staticmethod
    def get_posting_key(amount):
        return 'debit' if amount >= 0 else 'credit'


class InvoiceUpdater(object):
    REFERENCE_NUMBER_FIELD = 'reference_number'
    VISON_REFERENCE_NUMBER_FIELD = 'vision_invoice_number'
    STATUS_FIELD = 'status'
    MESSAGE_FIELD = 'message'

    def __init__(self, xml_data):
        self.root = ET.fromstring(xml_data)

    def update_invoices(self):
        possible_statuses = {s[0].lower() for s in Invoice.STATUS}

        invoice_grouping = defaultdict(list)
        errors = []

        for element in self.root:
            if element.tag != 'ta_invoice_ack':
                errors.append('Invalid tag: {}'.format(element.tag))
                continue

            # Parsing the incoming data and making error messages if needed
            required_tags = {self.REFERENCE_NUMBER_FIELD, self.STATUS_FIELD}
            optional_tags = {self.MESSAGE_FIELD, self.VISON_REFERENCE_NUMBER_FIELD}
            extra_elements = set()
            data_dict = MultiValueDict()
            for sub_element in element:
                if sub_element.tag in required_tags:
                    required_tags.remove(sub_element.tag)
                    data_dict.appendlist(sub_element.tag, sub_element.text)
                elif sub_element.tag in optional_tags:
                    data_dict.appendlist(sub_element.tag, sub_element.text)
                else:
                    extra_elements.add(sub_element.tag)

            if required_tags:
                errors.append('Missing tags: {}'.format(', '.join(required_tags)))

            if extra_elements:
                errors.append('Extra elements found: {}'.format(', '.join(extra_elements)))

            data_dict['status'] = data_dict['status'].lower()
            if data_dict['status'] not in possible_statuses:
                errors.append('Invalid invoice status: {}'.format(data_dict[self.STATUS_FIELD]))

            if errors:
                # To avoid key error just go on here
                continue

            business_area_code, _ = data_dict[self.REFERENCE_NUMBER_FIELD].split('/', 1)
            invoice_grouping[business_area_code].append(data_dict)

        if errors:
            raise InvoiceUpdateError(errors)

        self._update_invoices_in_tenants(invoice_grouping)

        if invoice_grouping:
            errors.append('Unknown workspaces: {}'.format(', '.join(invoice_grouping.keys())))
            raise InvoiceUpdateError(errors)

    @run_on_tenants
    def _update_invoices_in_tenants(self, workspace, invoice_grouping):
        if workspace.business_area_code not in invoice_grouping:
            return

        workspace_group = invoice_grouping.pop(workspace.business_area_code, [])
        for invoice_data in workspace_group:
            invoice_number = invoice_data[self.REFERENCE_NUMBER_FIELD]
            try:
                invoice = Invoice.objects.get(reference_number=invoice_number)
            except ObjectDoesNotExist:
                # TODO refine error handling
                log.error('Cannot find invoice with reference number %s', invoice_number)
                continue

            invoice.status = invoice_data[self.STATUS_FIELD]
            invoice.messages = invoice_data.getlist(self.MESSAGE_FIELD)
            invoice.vision_fi_id = invoice_data[self.VISON_REFERENCE_NUMBER_FIELD]
            invoice.save()

            if invoice.status == Invoice.ERROR:
                self.send_mail_for_error(workspace, invoice)

    def send_mail_for_error(self, workspace, invoice):
        url = reverse('t2f:invoices:details', kwargs={'invoice_pk': invoice.id})

        html_content = render_to_string('emails/failed_invoice_sync.html', {'invoice': invoice, 'url': url})

        recipients = User.objects.filter(profile__country=workspace,
                                         groups__name='Finance Focal Point').values_list('email', flat=True)

        # TODO what should it be?
        sender = ''
        msg = EmailMultiAlternatives('[Travel2Field VISION Error] {}'.format(invoice.reference_number),
                                     '',
                                     sender, recipients)
        msg.attach_alternative(html_content, 'text/html')

        try:
            msg.send(fail_silently=False)
        except ValidationError as exc:
            log.error('Was not able to send the email. Exception: %s', exc.message)
