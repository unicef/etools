from collections import namedtuple

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.utils.http import urlsafe_base64_decode
from django.views.generic import TemplateView, View

from easy_pdf.views import PDFTemplateView
from rest_framework import mixins, viewsets
from unicef_vision.utils import get_data_from_insight

from etools.applications.partners.models import Agreement, FileType
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP
from etools.applications.partners.serializers.v1 import FileTypeSerializer


class PCAPDFView(LoginRequiredMixin, PDFTemplateView):
    agreement = None
    template_name = "pca/english_pdf.html"
    # TODO add proper templates for different languages
    language_templates_mapping = {
        "arabic": "pca/arabic_pdf.html",
        "english": "pca/english_pdf.html",
        "french": "pca/french_pdf.html",
        "portuguese": "pca/portuguese_pdf.html",
        "russian": "pca/russian_pdf.html",
        "spanish": "pca/spanish_pdf.html",
        "ifrc_english": "pca/ifrc_english_pdf.html",
        "ifrc_french": "pca/ifrc_french_pdf.html"
    }

    def get_pdf_filename(self):
        if self.agreement:
            return '{0.reference_number}-{0.partner}.pdf'.format(self.agreement)
        return 'export.pdf'

    def get_context_data(self, **kwargs):
        agr_id = self.kwargs.get('agr')
        lang = self.request.GET.get('lang', 'english') or 'english'
        terms_acknowledged = self.request.GET.get('terms_acknowledged', 'false')
        error = None

        if terms_acknowledged.lower() != 'true':
            return {"error": "Terms to be acknowledged"}

        try:
            self.template_name = self.language_templates_mapping[lang]
        except KeyError:
            return {"error": "Cannot find document with given query parameter lang={}".format(lang)}

        try:
            self.agreement = Agreement.objects.get(id=agr_id)
        except Agreement.DoesNotExist:
            return {"error": 'Agreement with specified ID does not exist'}

        if not self.agreement.partner.vendor_number:
            return {"error": "Partner Organization has no vendor number stored, please report to an etools focal point"}

        if not self.agreement.authorized_officers.exists():
            return {"error": 'Partner Organization has no "Authorized Officers selected" selected'}

        url = 'partners/?vendor={vendor_code}'
        data = {"vendor_code": self.agreement.partner.vendor_number}
        if settings.INSIGHT_BANK_KEY:
            url += '&key={key}'
            data["key"] = settings.INSIGHT_BANK_KEY

        bank_objects = []
        if not settings.PCA_SKIP_FINANCIAL_DATA:
            valid_response, response = get_data_from_insight(url, data)
            if not valid_response:
                return {"error": response}
            try:
                banks_records = response["ROWSET"]["ROW"]["VENDOR_BANK"]["VENDOR_BANK_ROW"]
                if isinstance(banks_records, dict):
                    banks_records = [banks_records]
            except (KeyError, TypeError):
                return {"error": 'Response returned by the Server does not have the necessary values to generate PCA'}

            bank_key_values = [
                ('bank_address', "STREET"),
                ('bank_name', 'BANK_NAME'),
                ('account_title', "ACCT_HOLDER"),
                ('routing_details', "SWIFT_CODE"),
                ('account_number', "BANK_ACCOUNT_NO"),
                ('account_currency', "BANK_ACCOUNT_CURRENCY"),
                ('tax_number_5', "TAX_NUMBER_5"),
            ]
            Bank = namedtuple('Bank', ' '.join([i[0] for i in bank_key_values]))

            tax_number_5 = None
            if self.request.tenant.business_area_code == '3920' and response["ROWSET"]["ROW"]['TAX_NUMBER_5']:
                tax_number_5 = response["ROWSET"]["ROW"]['TAX_NUMBER_5']
            for b in banks_records:
                if isinstance(b, dict):
                    b["BANK_ADDRESS"] = ', '.join(b[key] for key in ['STREET', 'CITY'] if key in b and b[key])
                    b["ACCT_HOLDER"] = b["ACCT_HOLDER"] if "ACCT_HOLDER" in b else ""
                    # TODO: fix currency field name when we have it
                    b["BANK_ACCOUNT_CURRENCY"] = b["BANK_ACCOUNT_CURRENCY"] if "BANK_ACCOUNT_CURRENCY" in b else ""
                    b["TAX_NUMBER_5"] = tax_number_5

                    bank_objects.append(Bank(*[b[i[1]] for i in bank_key_values]))

        officers_list = []
        for officer in self.agreement.authorized_officers.filter(is_active=True):
            officers_list.append(
                {'first_name': officer.first_name,
                 'last_name': officer.last_name,
                 'email': officer.email,
                 'title': officer.profile.job_title}
            )

        font_path = settings.PACKAGE_ROOT + '/assets/fonts/'

        if not self.request.user.groups.filter(name=PARTNERSHIP_MANAGER_GROUP).exists():
            return {"error": 'Partnership Manager role required for pca export.'}

        self.agreement.terms_acknowledged_by = self.request.user
        self.agreement.save()

        return super().get_context_data(
            error=error,
            pagesize="Letter",
            title="Partnership",
            agreement=self.agreement,
            bank_details=bank_objects,
            cp=self.agreement.country_programme,
            auth_officers=officers_list,
            country=self.request.tenant.long_name,
            font_path=font_path,
            **kwargs
        )


class PortalDashView(View):

    def get(self, request):
        with open(settings.PACKAGE_ROOT + '/templates/frontend/partner/partner.html', 'r') as my_f:
            result = my_f.read()
        return HttpResponse(result)


class PortalLoginFailedView(TemplateView):

    template_name = "partner_loginfailed.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
