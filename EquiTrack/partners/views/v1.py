from __future__ import absolute_import
from __future__ import unicode_literals
from collections import namedtuple

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView, View
from django.utils.http import urlsafe_base64_decode

from rest_framework import viewsets, mixins
from easy_pdf.views import PDFTemplateView

from partners.models import (
    Agreement,
    FileType,
)
from partners.serializers.v1 import FileTypeSerializer
from EquiTrack.utils import get_data_from_insight


class PCAPDFView(PDFTemplateView):
    template_name = "partners/pca/english_pdf.html"
    # TODO add proper templates for different languages
    language_templates_mapping = {
        "arabic": "partners/pca/arabic_pdf.html",
        "english": "partners/pca/english_pdf.html",
        "french": "partners/pca/french_pdf.html",
        "portuguese": "partners/pca/portuguese_pdf.html",
        "russian": "partners/pca/russian_pdf.html",
        "spanish": "partners/pca/spanish_pdf.html",
        "ifrc_english": "partners/pca/ifrc_english_pdf.html",
        "ifrc_french": "partners/pca/ifrc_french_pdf.html"
    }

    def get_context_data(self, **kwargs):
        agr_id = self.kwargs.get('agr')
        lang = self.request.GET.get('lang', None)
        error = None

        try:
            self.template_name = self.language_templates_mapping[lang]
        except KeyError:
            return {"error": "Cannot find document with given query parameter lang={}".format(lang)}

        try:
            agreement = Agreement.objects.get(id=agr_id)
        except Agreement.DoesNotExist:
            return {"error": 'Agreement with specified ID does not exist'}

        if not agreement.partner.vendor_number:
            return {"error": "Partner Organization has no vendor number stored, please report to an etools focal point"}

        valid_response, response = get_data_from_insight('GetPartnerDetailsInfo_json/{vendor_code}',
                                                         {"vendor_code": agreement.partner.vendor_number})

        if not valid_response:
            return {"error": response}
        try:
            banks_records = response["ROWSET"]["ROW"]["VENDOR_BANK"]["VENDOR_BANK_ROW"]
        except (KeyError, TypeError):
            return {"error": 'Response returned by the Server does not have the necessary values to generate PCA'}

        bank_key_values = [
            ('bank_address', "BANK_ADDRESS"),
            ('bank_name', 'BANK_NAME'),
            ('account_title', "ACCT_HOLDER"),
            ('routing_details', "SWIFT_CODE"),
            ('account_number', "BANK_ACCOUNT_NO")
        ]
        Bank = namedtuple('Bank', ' '.join([i[0] for i in bank_key_values]))
        bank_objects = []
        for b in banks_records:
            b["BANK_ADDRESS"] = ', '.join(b[key] for key in ['STREET', 'CITY'] if key in b)
            bank_objects.append(Bank(*[b[i[1]] for i in bank_key_values]))

        officers_list = []
        for officer in agreement.authorized_officers.all():
            officers_list.append(
                {'first_name': officer.first_name,
                 'last_name': officer.last_name,
                 'email': officer.email,
                 'title': officer.title}
            )

        font_path = settings.SITE_ROOT + '/assets/fonts/'

        return super(PCAPDFView, self).get_context_data(
            error=error,
            pagesize="Letter",
            title="Partnership",
            agreement=agreement,
            bank_details=bank_objects,
            cp=agreement.country_programme,
            auth_officers=officers_list,
            country=self.request.tenant.long_name,
            font_path=font_path,
            **kwargs
        )


class PortalDashView(View):

    def get(self, request):
        with open(settings.SITE_ROOT + '/templates/frontend/partner/partner.html', 'r') as my_f:
            result = my_f.read()
        return HttpResponse(result)


class PortalLoginFailedView(TemplateView):

    template_name = "partner_loginfailed.html"

    def get_context_data(self, **kwargs):
        context = super(PortalLoginFailedView, self).get_context_data(**kwargs)
        context['email'] = urlsafe_base64_decode(context['email'])
        return context


class FileTypeViewSet(
        mixins.RetrieveModelMixin,
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        viewsets.GenericViewSet):
    """
    Returns a list of all Partner file types
    """
    queryset = FileType.objects.all()
    serializer_class = FileTypeSerializer
