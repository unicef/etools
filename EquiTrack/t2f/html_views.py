from __future__ import unicode_literals

from django.views.generic.base import TemplateView

from django.http import HttpResponseForbidden
from t2f.models import Travel


class TravelEditView(TemplateView):
    template_name = "details.html"

    def get_context_data(self, **kwargs):
        kwargs = super(TravelEditView, self).get_context_data(**kwargs)

        travel_pk = kwargs.pop('travel_pk')
        travel = Travel.objects.get(pk=travel_pk)
        kwargs['travel'] = travel

        kwargs['processing_count'] = travel.invoices.filter(status='processing').count()
        kwargs['success_count'] = travel.invoices.filter(status='success').count()
        kwargs['error_count'] = travel.invoices.filter(status='error').count()

        return kwargs

    def get(self, request, *args, **kwargs):
        if not self.request.user or not self.request.user.is_staff:
            return HttpResponseForbidden()
        return super(TravelEditView, self).get(request, *args, **kwargs)
