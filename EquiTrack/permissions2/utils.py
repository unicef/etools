def collect_parent_models(model):
    result = [model]
    parent_models = model._meta.get_parent_list()
    for parent in parent_models:
        result += collect_parent_models(parent)
    return result
