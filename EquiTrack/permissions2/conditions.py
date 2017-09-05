from django.db import models
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


class BaseRoleCondition(TemplateCondition):
    user_roles = NotImplemented
    predicate_template = 'user.role="{role}"'

    def __init__(self, user):
        self.user = user

    @classmethod
    def _get_user_type(cls, user):
        """
        Return user type based on user's groups.
        :param user:
        :return:
        """
        when_mapping = [
            models.When(name=name, then=models.Value(i))
            for i, name in enumerate(reversed(cls.user_roles))
        ]
        group = user.groups.annotate(
            order=models.Case(*when_mapping, default=models.Value(-1), output_field=models.IntegerField())
        ).order_by('-order').first()

        if not group:
            return None

        return group.name

    def get_context(self):
        return {
            'role': self._get_user_type(self.user)
        }


class ObjectStatusCondition(TemplateCondition):
    predicate_template = '{obj}.status="{status}"'
    status_field = 'status'

    def __init__(self, obj):
        self.obj = obj

    def get_context(self):
        return {
            'obj': '{}_{}'.format(self.obj._meta.app_label, self.obj._meta.model_name),
            'status': getattr(self.obj, self.status_field),
        }


class ModuleCondition(SimpleCondition):
    def is_satisfied(self):
        return True


class TPMModuleCondition(ModuleCondition):
    predicate = 'module="tpm"'


class TPMStaffMemberCondition(SimpleCondition):
    predicate = 'user in tpm_tpmpartner.staff_members'

    def __init__(self, partner, user):
        self.partner = partner
        self.user = user

    def is_satisfied(self):
        return self.user.pk in self.partner.staff_members.values_list('user', flat=True)


class TPMVisitUNICEFFocalPointCondition(SimpleCondition):
    predicate = 'user in tpm_tpmvisit.unicef_focal_points'

    def __init__(self, visit, user):
        self.visit = visit
        self.user = user

    def is_satisfied(self):
        return self.user in self.visit.unicef_focal_points.all()


class TPMVisitTPMFocalPointCondition(SimpleCondition):
    predicate = 'user in tpm_tpmvisit.tpm_partner_focal_points'

    def __init__(self, visit, user):
        self.visit = visit
        self.user = user

    def is_satisfied(self):
        return self.user.pk in self.visit.tpm_partner_focal_points.values_list('user', flat=True)


class TPMRoleCondition(BaseRoleCondition):
    user_roles = [
        'PME',
        'Third Party Monitor',
        'UNICEF User',
    ]


class NewObjectCondition(TemplateCondition):
    predicate_template = 'new {model}'

    def __init__(self, model=None):
        self.model = model

    def get_context(self):
        return {
            'model': '{}_{}'.format(self.model.app_label, self.model.model_name)
        }
