from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from partners.models import (
    Intervention,
)


class PDDetailsWrapperRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = {'pd-details': data}
        return super(PDDetailsWrapperRenderer, self).render(data, accepted_media_type, renderer_context)


class PRPInterventionListSerializer(serializers.ModelSerializer):

    start_date = serializers.DateField(source='start')
    end_date = serializers.DateField(source='end')

    class Meta:
        model = Intervention
        fields = (
            'id', 'title', 'offices', 'number',
            # 'partner_org',
            'unicef_focal_points',
            # 'agreement_auth_officers',
            # 'focal_points',
            'start_date', 'end_date',
        )
