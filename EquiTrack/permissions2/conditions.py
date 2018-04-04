from django.utils.six import python_2_unicode_compatible


@python_2_unicode_compatible
class BaseCondition(object):
    def to_internal_value(self):
        raise NotImplementedError

    def __str__(self):
        return self.to_internal_value()


class SimpleCondition(BaseCondition):
    predicate = NotImplemented

    def is_satisfied(self):
        raise NotImplemented

    def to_internal_value(self):
        if self.is_satisfied():
            return self.predicate
        else:
            return None


class TemplateCondition(BaseCondition):
    predicate_template = NotImplemented

    def get_context(self):
        raise NotImplemented

    def to_internal_value(self):
        return self.predicate_template.format(**self.get_context())


class GroupCondition(TemplateCondition):
    predicate_template = 'user.group="{group}"'

    def __init__(self, user):
        self.user = user

    def get_groups(self):
        return self.user.groups.values_list('name', flat=True)

    def to_internal_value(self):
        return [
            self.predicate_template.format(group=group)
            for group in self.get_groups()
        ]


class ObjectStatusCondition(TemplateCondition):
    predicate_template = '{obj}.status="{status}"'
    status_field = 'status'

    def __init__(self, obj):
        self.obj = obj

    def _get_parents(self, cls=None, depth=0):
        if not cls:
            parents = [[self.obj.__class__, 0]]
        else:
            parents = [[base, depth] for base in cls.__bases__]

        for base, depth in parents:
            parents.extend(self._get_parents(base, depth=depth+1))

        return parents

    def get_status_root(self):
        status_parents = list(filter(
            lambda p:
                hasattr(p[0], '_meta') and any(map(lambda f: f.name == 'status', p[0]._meta.fields)),
            self._get_parents()
        ))
        return max(*status_parents, key=lambda p: p[1])[0]

    def get_context(self):
        return {
            'obj': '{}_{}'.format(self.get_status_root()._meta.app_label, self.get_status_root()._meta.model_name),
            'status': getattr(self.obj, self.status_field),
        }


class ModuleCondition(SimpleCondition):
    def is_satisfied(self):
        return True


class NewObjectCondition(TemplateCondition):
    predicate_template = 'new {model}'

    def __init__(self, model=None):
        self.model = model

    def get_context(self):
        return {
            'model': '{}_{}'.format(self.model._meta.app_label, self.model._meta.model_name)
        }
