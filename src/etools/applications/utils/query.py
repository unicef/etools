from django.contrib.contenttypes.models import ContentType
from django.db import models


def has_related_records(queryset, model, avoid_self=True, model_relations_to_ignore=[]):
    '''
    Function that returns a tuple, whether the queryset has records that other models foreign key into (or m2m)
    (Bool - whether it has any records, [list of pks] - all records that other model instances relating to them)
    '''
    all_impacted_records = []
    # Get all related objects' content types
    related_content_types = ContentType.objects.filter(
        models.Q(model__in=[field.related_model._meta.object_name.lower() for field in model._meta.get_fields()
                            if field.one_to_many or field.many_to_many])
    )
    # filter out all deprecated models that no longer exit. rct.model_class would return None if they are no longer
    related_content_types = [rct for rct in related_content_types if rct.model_class()]
    if avoid_self:
        related_content_types = [rct for rct in related_content_types if rct.model_class() != model]
    if model_relations_to_ignore:
        related_content_types = [rct for rct in related_content_types if rct.model_class() not in model_relations_to_ignore]
    # Iterate over related content types and check for related records
    for related_content_type in related_content_types:
        related_model = related_content_type.model_class()
        rel_model_fields = related_model._meta.get_fields(include_hidden=True)
        rel_field_names = [f.name for f in rel_model_fields if f.remote_field and f.remote_field.model == model]
        # Check if there are any related records for the current queryset
        for related_field_name in rel_field_names:
            # (f'model {related_model} field: {related_field_name}') - "model Intervention field flat_locations"
            if related_model.objects.filter(**{f'{related_field_name}__in': queryset}).exists():
                all_impacted_records += related_model.objects.filter(**{f'{related_field_name}__in': queryset}).\
                    values_list(f'{related_field_name}__pk', flat=True)
    if all_impacted_records:
        return True, list(set(all_impacted_records))
    return False, []


def get_all_items_related(record):
    results = []
    model = record._meta.model
    related_content_types = ContentType.objects.filter(
        models.Q(model__in=[field.related_model._meta.object_name.lower() for field in model._meta.get_fields()
                            if field.one_to_many or field.many_to_many])
    )
    related_content_types = [rct for rct in related_content_types if rct.model_class()]
    for related_content_type in related_content_types:
        related_model = related_content_type.model_class()
        rel_model_fields = related_model._meta.get_fields(include_hidden=True)
        rel_field_names = [f.name for f in rel_model_fields if f.remote_field and f.remote_field.model == model]
        for related_field_name in rel_field_names:
            print("rel", related_model, related_field_name)
            if related_model.objects.filter(**{f'{related_field_name}__in': [record]}).exists():
                results.append((related_model, related_model.objects.filter(**{f'{related_field_name}__in': [record]})))
    return results
