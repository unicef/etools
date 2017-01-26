from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import get_object_or_404

from actstream.managers import ActionManager, stream


# Referred to https://github.com/justquick/django-activity-stream/issues/232
class CustomDataActionManager(ActionManager):

    @stream
    def custom_data_model_stream(self, model_name, **kwargs):
        obj_content = get_object_or_404(ContentType, model=model_name)
        return self.public(
            (Q(target_content_type=obj_content) |
             Q(action_object_content_type=obj_content) |
             Q(actor_content_type=obj_content)),
            **kwargs
        )

    @stream
    def custom_data_model_detail_stream(self, model_name, obj_id, **kwargs):
        obj_content = get_object_or_404(ContentType, model=model_name)
        obj = obj_content.get_object_for_this_type(pk=obj_id)

        return obj.target_actions.public(**kwargs)
