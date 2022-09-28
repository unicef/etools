from etools.applications.ecn.api import ECNAPI
from etools.applications.ecn.serializers import InterventionSerializer
from etools.applications.partners.models import Intervention


class InterventionNotReadyException(Exception):
    pass


class ECNSynchronizer:
    def __init__(self, user):
        self.user = user

    def request_ecn(self, number):
        return ECNAPI(self.user).get_intervention(number)

    def parse(self, data, **kwargs):
        serializer = InterventionSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.save(**kwargs)

    def synchronize(self, number, agreement, sections, locations, offices):
        data = self.request_ecn(number)
        if not data:
            return None

        if 'status' not in data or data['status'] != 'completed':
            raise InterventionNotReadyException

        save_extra_kwargs = {
            'document_type': Intervention.PD,
            'status': Intervention.DRAFT,
            'agreement': agreement,
            'sections': sections,
            'offices': offices,
            'flat_locations': locations,
        }
        intervention = self.parse(data, **save_extra_kwargs)
        # reload instance to properly fetch all related objects
        return Intervention.objects.detail_qs().get(id=intervention.id)
