from django.apps import apps
from rest_framework import permissions
from django.utils.lru_cache import lru_cache

from EquiTrack.utils import HashableDict
from EquiTrack.validation_mixins import check_rigid_related
from utils.common.utils import get_all_field_names


class PMPPermissions(object):
    actions_default_permissions = {
        'edit': True,
        'view': True,
        'required': False
    }
    possible_actions = ['edit', 'required', 'view']

    def __init__(self, user, instance, permission_structure, **kwargs):
        self.MODEL = apps.get_model(self.MODEL_NAME)
        self.user = user
        self.user_groups = self.user.groups.values_list('name', flat=True)
        self.instance = instance
        self.condition_group_valid = lru_cache(maxsize=16)(self.condition_group_valid)
        self.permission_structure = permission_structure
        self.all_model_fields = get_all_field_names(self.MODEL)

    def condition_group_valid(self, condition_group):
        if condition_group['status'] and condition_group['status'] != '*':
            if self.instance.status != condition_group['status']:
                return False
        if condition_group['group'] and condition_group['group'] != '*':
            if condition_group['group'] not in self.user_groups:
                return False
        if condition_group['condition'] and condition_group['condition'] != '*':
            # use the following commented line in case we want to not use a condition mapper and interpret the
            # condition directly from the sheet (not recommended)
            # if not eval(condition_group['condition'], globals=globals(), locals=locals()):
            if not self.condition_map[condition_group['condition']]:
                return False
        return True

    def get_field_permissions(self, action, field):
        condition_groups = field[action]

        # For a field and one action (start_date, can_view) you can't define both true conditions and false conditions
        # because if both groups fail, we can't know what to default to
        # this assertion should be in the ingestion script

        # if the "false" conditions were defined that means that by default allowed will be "true"
        # otherwise it means that the "true" conditions were defined and therefore default will be "false"
        default_return = bool(len(condition_groups['false']))

        for allowed in ['true', 'false']:
            for condition_group in condition_groups[allowed]:
                if self.condition_group_valid(HashableDict(condition_group)):
                    return True if allowed == 'true' else False

        return default_return

    def get_permissions(self):
        ps = self.permission_structure

        my_permissions = {}
        for action in self.possible_actions:
            my_permissions[action] = {}
            for field in self.all_model_fields:
                if field not in ps:
                    my_permissions[action][field] = self.actions_default_permissions[action]
                else:
                    my_permissions[action][field] = self.get_field_permissions(action, ps[field])
        return my_permissions


class InterventionPermissions(PMPPermissions):

    MODEL_NAME = 'partners.Intervention'

    def __init__(self, **kwargs):
        '''
        :param kwargs: user, instance, permission_structure
        if 'inbound_check' key, is sent in, that means that instance now contains all of the fields available in the
        validation: old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex permissions that can only be checked on save.
        for example: in this case certain field are editable only when user adds an amendment. that means that we would
        need access to the old amendments, new amendments in order to check this.
        '''
        super(InterventionPermissions, self).__init__(**kwargs)
        inbound_check = kwargs.get('inbound_check', False)

        def user_added_amendment(instance):
            assert inbound_check, 'this function cannot be called unless instantiated with inbound_check=True'
            # check_rigid_related checks if there were any changes from the previous
            # amendments if there were changes it returns False
            return not check_rigid_related(instance, 'amendments')

        self.condition_map = {
            'condition1': self.user in self.instance.unicef_focal_points.all(),
            'condition2': self.user in self.instance.partner_focal_points.all(),
            'contingency on': self.instance.contingency_pd is True,
            # this condition can only be checked on data save
            'user adds amendment': False if not inbound_check else user_added_amendment(self.instance)
        }


class AgreementPermissions(PMPPermissions):

    MODEL_NAME = 'partners.Agreement'

    def __init__(self, **kwargs):
        '''
        :param kwargs: user, instance, permission_structure
        if 'inbound_check' key, is sent in, that means that instance now contains all of the fields available in the
        validation: old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex permissions that can only be checked on save.
        for example: in this case certain field are editable only when user adds an amendment. that means that we would
        need access to the old amendments, new amendments in order to check this.
        '''
        super(AgreementPermissions, self).__init__(**kwargs)
        inbound_check = kwargs.get('inbound_check', False)

        def user_added_amendment(instance):
            assert inbound_check, 'this function cannot be called unless instantiated with inbound_check=True'
            # check_rigid_related checks if there were any changes from the previous
            # amendments if there were changes it returns False
            return not check_rigid_related(instance, 'amendments')

        self.condition_map = {
            'is type PCA or MOU': self.instance.agreement_type in [self.instance.PCA, self.instance.MOU],
            'is type MOU': self.instance.agreement_type == self.instance.MOU,
            # this condition can only be checked on data save
            'user adds amendment': False if not inbound_check else user_added_amendment(self.instance)
        }


class PartneshipManagerPermission(permissions.BasePermission):
    message = 'Accessing this item is not allowed.'

    def _has_access_permissions(self, user, object):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                object.partner.staff_members.values_list('id', flat=True):
            return True

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return request.user.is_staff
        else:
            return request.user.groups.filter(name='Partnership Manager').exists()

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and \
                request.user.groups.filter(name='Partnership Manager').exists()


class PartneshipManagerRepPermission(permissions.BasePermission):
    message = 'Accessing this item is not allowed.'

    def _has_access_permissions(self, user, object):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                object.partner.staff_members.values_list('id', flat=True):
            return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and \
                request.user.groups.filter(name__in=['Partnership Manager', 'Senior Management Team',
                                                     'Representative Office']).exists()
