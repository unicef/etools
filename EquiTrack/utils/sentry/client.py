from raven.contrib.django.raven_compat import DjangoClient


class EToolsSentryClient(DjangoClient):

    def get_data_from_request(self, request):
        result = super(EToolsSentryClient, self).get_data_from_request(request)
        if getattr(request, 'tenant', None):
            if 'extra' not in result:
                result['extra'] = {}
            result['extra']['tenant'] = request.tenant.name
        return result
