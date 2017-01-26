from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import get_object_or_404

from actstream.managers import ActionManager, stream


class CustomDataActionManager(ActionManager):

    @stream
    def custom_data_model_stream(self, content_type_id, **kwargs):
        obj_content = get_object_or_404(ContentType, pk=content_type_id)
        return self.public(
            (Q(target_content_type=obj_content) |
             Q(action_object_content_type=obj_content) |
             Q(actor_content_type=obj_content)),
            **kwargs
        )
