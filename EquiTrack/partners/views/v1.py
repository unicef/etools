from __future__ import absolute_import
from __future__ import unicode_literals
from collections import namedtuple

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView, View
from django.utils.http import urlsafe_base64_decode

from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets, mixins
from partners.models import (
    Agreement,
    FileType,
)
from partners.serializers.v1 import FileTypeSerializer, AgreementNestedSerializer
from EquiTrack.utils import get_data_from_insight, load_internal_pdf_template


class PCAPDFView(RetrieveAPIView):
    languages = ("arabic", "english", "french", "portuguese",
                 "russian", "spanish", "ifrc_english", "ifrc_french")

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        try:
            ctx_data = self.get_context_data(**kwargs)

            if ctx_data['error'] is not None:
                return HttpResponse(ctx_data['error'])
            else:
                pdf_response = load_internal_pdf_template("agreements", ctx_data)

                # return HttpResponse(pdf_response, content_type='application/pdf')
                if pdf_response.status_code == status.HTTP_200_OK:
                    return HttpResponse(pdf_response, content_type='application/pdf')
                else:
                    return HttpResponse('PDF generation service returned an invalid response.')
        except:
            return HttpResponse('PDF generation encountered an unexpected error.')

    def get_context_data(self, **kwargs):
        agr_id = self.kwargs.get('agr')
        lang = self.request.GET.get('lang', None)
        error = None

        if lang not in self.languages:
            return {"error": "Language does not exist for given query parameter lang={}".format(lang)}

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

        country_programme = {}
        country_programme.update({
            "from_date": agreement.country_programme.from_date.strftime("%Y"),
            "to_date": agreement.country_programme.to_date.strftime("%Y"),
        })

        serialized_agreement = AgreementNestedSerializer(agreement, read_only=True)

        return {
            "error": error,
            "pagesize": "Letter",
            "title": "Partnership",
            "language": lang,
            "agreement": serialized_agreement.data,
            "bank_details": bank_objects,
            "cp": country_programme,
            "auth_officers": officers_list,
            "country": self.request.tenant.long_name,
        }


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
