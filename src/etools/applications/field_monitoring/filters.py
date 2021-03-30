from django_filters import FilterSet, rest_framework as filters
from unicef_attachments.models import AttachmentLink


class FMAttachmentLinksFilterSet(FilterSet):
    pk__in = filters.BaseInFilter(field_name='attachment_id')

    class Meta:
        model = AttachmentLink
        fields = ('pk__in',)
