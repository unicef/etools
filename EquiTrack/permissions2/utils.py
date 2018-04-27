from django.db.models import OneToOneField


def collect_parent_models(model, levels=None):
    """
    Recursively collect list of parent models.
    :param model:
    :param levels:
    :return:
    """
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
    """
    Recursively collect list of child models.
    :param model:
    :param levels:
    :return:
    """
    result = []

    if levels == 0:
        return result
    elif levels:
        levels -= 1

    related_objects = [
        f for f in model._meta.get_fields()
        if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
    ]
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


def get_model_target(model):
    """
    Return string target for selected model.
    example: audit_engagement
    :param model: model class or instance
    :return: str
    """
    return '{}_{}'.format(model._meta.app_label, model._meta.model_name)
