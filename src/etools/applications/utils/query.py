from django.contrib.contenttypes.models import ContentType
from django.db import models


def has_related_records(queryset, model, avoid_self=True):
    all_impacted_records = []
    # Get all related objects' content types
    related_content_types = ContentType.objects.filter(
        models.Q(model__in=[field.related_model._meta.object_name.lower() for field in model._meta.get_fields()
                            if field.one_to_many or field.many_to_many])
    )
    related_content_types = [rct for rct in related_content_types if rct.model_class()]
    if avoid_self:
        related_content_types = [rct for rct in related_content_types if rct.model_class() != model]

    # Iterate over related content types and check for related records
    for related_content_type in related_content_types:
        related_model = related_content_type.model_class()
        rel_model_fields = related_model._meta.get_fields(include_hidden=True)
        rel_field_names = [f.name for f in rel_model_fields if f.remote_field and f.remote_field.model == model]
        # Check if there are any related records for the current queryset
        for related_field_name in rel_field_names:
            print(f'model {related_model} field: {related_field_name}')

            if related_model.objects.filter(**{f'{related_field_name}__in': queryset}).exists():
                all_impacted_records += related_model.objects.filter(**{f'{related_field_name}__in': queryset}).\
                    values_list(f'{related_field_name}__pk', flat=True)

    if all_impacted_records:
        return True, all_impacted_records
    return False, None
