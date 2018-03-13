from django.db.models import OneToOneField


def collect_parent_models(model, levels=None):
    result = []

    if levels == 0:
        return result
    elif levels:
        levels -= 1

    parent_models = model._meta.get_parent_list()

    for parent in parent_models:
        result.append(parent)
        if levels is not None and levels:
            result.extend(collect_parent_models(parent, levels))

    return result


def collect_child_models(model, levels=None):
    result = []

    if levels == 0:
        return result
    elif levels:
        levels -= 1

    related_objects = model._meta.get_all_related_objects()
    related_objects = [
        rel for rel in related_objects
        if isinstance(rel.field, OneToOneField)
        and issubclass(rel.field.model, model)
        and model is not rel.field.model
    ]

    for rel in related_objects:
        result.append(rel.field.model)
        if levels is not None and levels:
            result.extend(collect_child_models(rel.field.model, levels))

    return result
