import datetime

from django.apps import apps
from django.utils.lru_cache import lru_cache
from django.utils.translation import ugettext as _

from etools_validator.utils import check_rigid_related
from rest_framework import permissions
from rest_framework.permissions import BasePermission

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.libraries.djangolib.utils import get_all_field_names, is_user_in_groups
from etools.libraries.pythonlib.collections import HashableDict

# READ_ONLY_API_GROUP_NAME is the name of the permissions group that provides read-only access to some list views.
# Initially, this is only being used for PRP-related endpoints.


READ_ONLY_API_GROUP_NAME = 'Read-Only API'
SENIOR_MANAGEMENT_GROUP = 'Senior Management Team'
PARTNERSHIP_MANAGER_GROUP = 'Partnership Manager'
REPRESENTATIVE_OFFICE_GROUP = 'Representative Office'


class PMPPermissions:
    # this property specifies an array of model properties in order to check against the permission matrix. The fields
    # declared under this property need to be both property on the model and delcared in the permission matrix
    EXTRA_FIELDS = []
    actions_default_permissions = {
        'edit': True,
        'view': True,
        'required': False
    }
    possible_actions = ['edit', 'required', 'view']

    def __init__(self, user, instance, permission_structure, **kwargs):
        self.MODEL = apps.get_model(self.MODEL_NAME)
        self.user = user
        self.user_groups = list(self.user.groups.values_list('name', flat=True))
        self.instance = instance
        self.condition_group_valid = lru_cache(maxsize=16)(self.condition_group_valid)
        self.permission_structure = permission_structure
        self.all_model_fields = get_all_field_names(self.MODEL)
        self.all_model_fields += self.EXTRA_FIELDS

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
    EXTRA_FIELDS = ['sections_present', 'pd_outputs', 'final_partnership_review']

    def __init__(self, **kwargs):
        """
        :param kwargs: user, instance, permission_structure
        # FIXME: This documentation is out of date as the flag check has been commented out.
        if 'inbound_check' key, is sent in, that means that instance now contains all of the fields available in the
        validation: old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex permissions that can only be checked on save.
        for example: in this case certain field are editable only when user adds an amendment. that means that we would
        need access to the old amendments, new amendments in order to check this.
        """
        from etools.applications.partners.models import PartnerStaffMember

        super().__init__(**kwargs)

        # Inbound check flag is available here:
        # inbound_check = kwargs.get('inbound_check', False)

        def user_added_amendment(instance):
            return instance.in_amendment is True

        def prp_mode_off():
            return tenant_switch_is_active("prp_mode_off")

        def prp_server_on():
            return tenant_switch_is_active("prp_server_on")

        partner_staff_member_id = PartnerStaffMember.get_id_for_user(self.user)

        # focal points are prefetched, so just cast to array to collect ids
        partner_focal_points = [fp.id for fp in self.instance.partner_focal_points.all()]

        if partner_staff_member_id and partner_staff_member_id == self.instance.partner_authorized_officer_signatory_id:
            self.user_groups.extend(['Partner User', 'Partner Signer'])

        if partner_staff_member_id and partner_staff_member_id in partner_focal_points:
            self.user_groups.extend(['Partner User', 'Partner Focal Point'])

        self.user_groups = list(set(self.user_groups))

        self.condition_map = {
            'condition1': self.user in self.instance.unicef_focal_points.all(),
            'condition2': self.user in self.instance.partner_focal_points.all(),
            'contingency on': self.instance.contingency_pd is True,
            'not_in_amendment_mode': not user_added_amendment(self.instance),
            'not_ssfa': self.instance.document_type != self.instance.SSFA,
            'user_adds_amendment': user_added_amendment(self.instance),
            'prp_mode_on': not prp_mode_off(),
            'prp_mode_on+contingency_on': not prp_mode_off() and self.instance.contingency_pd,
            'prp_mode_off': prp_mode_off(),
            'prp_server_on': prp_server_on(),
            'user_adds_amendment+prp_mode_on': user_added_amendment(self.instance) and not prp_mode_off(),
            'termination_doc_attached': self.instance.termination_doc_attachment.exists(),
            'not_ended': self.instance.end >= datetime.datetime.now().date() if self.instance.end else False,
            'unicef_court': self.instance.unicef_court,
            'partner_court': not self.instance.unicef_court,
        }


class AgreementPermissions(PMPPermissions):

    MODEL_NAME = 'partners.Agreement'

    def __init__(self, **kwargs):
        """
        :param kwargs: user, instance, permission_structure
        if 'inbound_check' key, is sent in, that means that instance now contains all of the fields available in the
        validation: old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex permissions that can only be checked on save.
        for example: in this case certain field are editable only when user adds an amendment. that means that we would
        need access to the old amendments, new amendments in order to check this.
        """
        super().__init__(**kwargs)
        inbound_check = kwargs.get('inbound_check', False)

        def termination_doc_attached():
            if self.instance.agreement_type != self.instance.PCA:
                return True
            if self.instance.termination_doc.exists():
                return True
            return False

        def user_added_amendment(instance):
            assert inbound_check, 'this function cannot be called unless instantiated with inbound_check=True'
            # check_rigid_related checks if there were any changes from the previous
            # amendments if there were changes it returns False
            return not check_rigid_related(instance, 'amendments')

        self.condition_map = {
            'is type PCA or MOU': self.instance.agreement_type in [self.instance.PCA, self.instance.MOU],
            'is type PCA or SSFA': self.instance.agreement_type in [self.instance.PCA, self.instance.SSFA],
            'is type SSFA': self.instance.agreement_type == self.instance.SSFA,
            'is type MOU': self.instance.agreement_type == self.instance.MOU,
            # this condition can only be checked on data save
            'user adds amendment': False if not inbound_check else user_added_amendment(self.instance),
            'termination_doc_attached': termination_doc_attached(),
        }


class PartnershipManagerPermission(permissions.BasePermission):
    """Applies general and object-based permissions.

    - For list views --
      - user must be staff or in 'Partnership Manager' group

    - For create views --
      - user must be in 'Partnership Manager' group

    - For retrieve views --
      - user must be (staff or in 'Partnership Manager' group) OR
                     (staff or listed as a partner staff member on the object)

    - For update/delete views --
      - user must be (in 'Partnership Manager' group) OR
                     (listed as a partner staff member on the object)
    """
    message = 'Accessing this item is not allowed.'

    def _has_access_permissions(self, user, obj):
        """True if --
              - user is staff OR
              - user is 'Partnership Manager' group member OR
              - user is listed as a partner staff member on the object, assuming the object has a partner attribute
        """
        has_access = user.is_staff or is_user_in_groups(user, [PARTNERSHIP_MANAGER_GROUP])
        if has_access:
            return True

        has_access = hasattr(obj, 'partner') and obj.partner.user_is_staff_member(user)
        return has_access

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return request.user.is_staff or is_user_in_groups(request.user, [PARTNERSHIP_MANAGER_GROUP])
        else:
            return is_user_in_groups(request.user, [PARTNERSHIP_MANAGER_GROUP])

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and \
                is_user_in_groups(request.user, [PARTNERSHIP_MANAGER_GROUP])


class PartnershipManagerRepPermission(permissions.BasePermission):
    message = 'Accessing this item is not allowed.'

    def _has_access_permissions(self, user, object):
        if user.is_staff or object.partner.user_is_staff_member(user):
            return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and is_user_in_groups(
                request.user,
                [
                    PARTNERSHIP_MANAGER_GROUP,
                    SENIOR_MANAGEMENT_GROUP,
                    REPRESENTATIVE_OFFICE_GROUP,
                ]
            )


class PartnershipSeniorManagerPermission(permissions.BasePermission):
    message = _('Accessing this item is not allowed.')

    def _has_access_permissions(self, user, object):
        if user.is_staff or object.partner.user_is_staff_member(user):
            return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and is_user_in_groups(
                request.user,
                [PARTNERSHIP_MANAGER_GROUP, SENIOR_MANAGEMENT_GROUP]
            )


class ListCreateAPIMixedPermission(permissions.BasePermission):
    """Permission class for ListCreate views that want to allow read-only access to some groups and read-write
    to others.

    GET users must be either (a) staff or (b) in the Limited API group.

    POST users must be staff.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated:
                if request.user.is_staff or is_user_in_groups(request.user, [READ_ONLY_API_GROUP_NAME]):
                    return True
            return False
        elif request.method == 'POST':
            # user must have have admin access
            return request.user.is_authenticated and request.user.is_staff
        else:
            # This class shouldn't see methods other than GET and POST, but regardless the answer is 'no you may not'.
            return False


class AllowSafeAuthenticated(permissions.BasePermission):
    """"only read peremissions if authenticated, no write"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated:
                return True
        return False


class ReadOnlyAPIUser(permissions.BasePermission):
    """Permission class for Views that only allow read and only for backend api users or superusers
        GET users must be either (a) superusers or (b) in the Limited API group.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_authenticated:
                if request.user.is_superuser or is_user_in_groups(request.user, [READ_ONLY_API_GROUP_NAME]):
                    return True
            return False
        else:
            # This class shouldn't see methods other than GET, but regardless the answer is 'no you may not'.
            return False


def intervention_field_is_editable_permission(field):
    """
    Check the user is able to edit selected monitoring activity field.
    View should either implement get_root_object to return instance of Intervention (if view is nested),
    or return Intervention instance via get_object (can be used for detail actions).
    """

    from etools.applications.partners.models import Intervention

    class FieldPermission(BasePermission):
        def has_permission(self, request, view):
            if not view.kwargs:
                # This is needed for swagger to be able to build the correct structure
                # https://github.com/unicef/etools/pull/2540/files#r356446025
                return True

            if hasattr(view, 'get_root_object'):
                instance = view.get_root_object()
            else:
                instance = view.get_object()

            ps = Intervention.permission_structure()
            permissions = InterventionPermissions(
                user=request.user, instance=instance, permission_structure=ps
            )
            return permissions.get_permissions()['edit'].get(field)

    return FieldPermission


class IsPartnerUser(BasePermission):
    def has_permission(self, request, view):
        from etools.applications.partners.models import PartnerStaffMember

        return request.user.is_authenticated and bool(PartnerStaffMember.get_for_user(request.user))

    def has_object_permission(self, request, view, obj):
        return True


def view_action_permission(*actions):
    class ViewActionPermission(BasePermission):
        def has_permission(self, request, view):
            return hasattr(view, 'action') and view.action in actions

    return ViewActionPermission


def user_group_permission(*groups):
    class UserGroupPermission(BasePermission):
        def has_permission(self, request, view):
            return request.user.is_authenticated and is_user_in_groups(request.user, groups)

    return UserGroupPermission


class UserIsPartnerStaffMemberPermission(BasePermission):
    def has_permission(self, request, view):
        from etools.applications.partners.models import PartnerStaffMember

        return bool(PartnerStaffMember.get_for_user(request.user))


class UserIsNotPartnerStaffMemberPermission(BasePermission):
    def has_permission(self, request, view):
        from etools.applications.partners.models import PartnerStaffMember

        return not bool(PartnerStaffMember.get_for_user(request.user))


class UserIsObjectPartnerStaffMember(UserIsPartnerStaffMemberPermission):
    def has_object_permission(self, request, view, obj):
        from etools.applications.partners.models import PartnerStaffMember

        if not hasattr(obj, 'partner'):
            return False

        partner_staff_members = obj.partner.staff_members.values_list('id', flat=True)
        return PartnerStaffMember.get_id_for_user(request.user) in partner_staff_members


class UserIsStaffPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff


class IsSafeMethodPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsUnsafeMethodPermission(BasePermission):
    def has_permission(self, request, view):
        return request.method not in permissions.SAFE_METHODS


"""
PartnershipManagerPermission is too broad, so we can't just add partners and be sure it wouldn't have side effects.
Rewritten using smaller permissions from comment describing how it should work.

Applies general and object-based permissions.

- For list views --
  - user must be staff or in 'Partnership Manager' group

- For create views --
  - user must be in 'Partnership Manager' group

- For retrieve views --
  - user must be (staff or in 'Partnership Manager' group) OR
                 (staff or listed as a partner staff member on the object)
    # equals to: staff or in 'Partnership Manager' group or listed as a partner staff member on the object

- For update/delete views --
  - user must be (in 'Partnership Manager' group) OR
                 (listed as a partner staff member on the object)
"""
PartnershipManagerRefinedPermission = (
    view_action_permission('metadata') |
    (view_action_permission('list') & (UserIsStaffPermission | user_group_permission('Partnership Manager'))) |
    (view_action_permission('create') & user_group_permission('Partnership Manager')) |
    (
        view_action_permission('retrieve') &
        (UserIsStaffPermission | user_group_permission('Partnership Manager') | UserIsObjectPartnerStaffMember)
    ) |
    (
        view_action_permission('update', 'partial_update', 'delete') &
        (user_group_permission('Partnership Manager') | UserIsObjectPartnerStaffMember)
    )
)

# allow partners to load list ONLY for interventions to keep everything else working right as before; at least for now
PMPInterventionPermission = (
    PartnershipManagerRefinedPermission | (view_action_permission('list') & UserIsPartnerStaffMemberPermission)
)
