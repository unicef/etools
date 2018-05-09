from django.utils.six import python_2_unicode_compatible

from etools.applications.permissions2.utils import collect_parent_models, get_model_target


@python_2_unicode_compatible
class BaseCondition(object):
    def to_internal_value(self):
        raise NotImplementedError

    def __str__(self):
        return self.to_internal_value()


class SimpleCondition(BaseCondition):
    """
    Condition that returns it's predicate if satisfied.
    """
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
    """
    Add user groups to permissions context
    """
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
    """
    Add instance status into permissions context.
    """
    predicate_template = '{obj}.status="{status}"'
    status_field = 'status'

    def __init__(self, obj):
        self.obj = obj

    def get_status_root(self):
        """
        Determine first parent class where `status` field was implemented.
        Required for correct inheritance handling.
        """
        status_parents = list(filter(
            lambda parent:
                hasattr(parent, '_meta') and any(map(lambda field: field.name == 'status', parent._meta.fields)),
            [self.obj] + collect_parent_models(self.obj)
        ))

        return status_parents[-1]

    def get_context(self):
        """
        Collect context for predicate template
        :return:
        """
        return {
            'obj': get_model_target(self.get_status_root()),
            'status': getattr(self.obj, self.status_field),
        }


class ModuleCondition(SimpleCondition):
    """
    Divide permissions for shared models.

    class AuditModuleCondition(ModuleCondition):
        predicate = 'module="audit"'
    """

    def is_satisfied(self):
        return True


class NewObjectCondition(TemplateCondition):
    """
    Identify `new` instance state.
    """
    predicate_template = 'new {model}'

    def __init__(self, model=None):
        self.model = model

    def get_context(self):
        return {
            'model': get_model_target(self.model)
        }
