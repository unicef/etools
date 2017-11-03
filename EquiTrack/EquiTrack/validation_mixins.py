from __future__ import unicode_literals
from __future__ import absolute_import

import copy
import logging

from django.apps import apps
from django.db.models import ObjectDoesNotExist
from django.db.models.fields.files import FieldFile
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django_fsm import (
    can_proceed, has_transition_perm,
    get_all_FIELD_transitions
)
from rest_framework.exceptions import ValidationError

from EquiTrack.parsers import parse_multipart_data
from utils.common.utils import get_all_field_names


def check_editable_fields(obj, fields):
    if not getattr(obj, 'old_instance', None):
        return False, fields
    for field in fields:
        old_instance = obj.old_instance
        if getattr(obj, field) != getattr(old_instance, field):
            return False, field
    return True, None


def check_required_fields(obj, fields):
    error_fields = []
    for f_name in fields:
        try:
            field = getattr(obj, f_name)
        except ObjectDoesNotExist:
            return False, f_name
        try:
            response = field.filter().count() > 0
        except AttributeError:
            if isinstance(field, FieldFile):
                response = getattr(field, 'name', None) or False
            else:
                response = field is not None
        if response is False:
            error_fields.append(f_name)

    if error_fields:
        return False, error_fields
    return True, None


def field_comparison(f1, f2):
    if isinstance(f1, FieldFile):
        new_file = getattr(f1, 'name', None)
        old_file = getattr(f2, 'name', None)
        if new_file != old_file:
            return False
    elif f1 != f2:
        return False
    return True


def check_rigid_related(obj, related):
    current_related = list(getattr(obj, related).filter())
    old_related = getattr(obj.old_instance, '{}_old'.format(related), None)
    if old_related is None:
        # if old related was not set as an attribute on the object, assuming no changes
        return True
    if len(current_related) != len(old_related):
        return False
    if len(current_related) == 0:
        return True

    field_names = get_all_field_names(current_related[0])
    current_related.sort(key=lambda x: x.id)
    old_related.sort(key=lambda x: x.id)
    comparison_map = zip(current_related, old_related)
    # check if any field on the related model was changed
    for i in comparison_map:
        for field in field_names:
            try:
                new_value = getattr(i[0], field)
            except ObjectDoesNotExist:
                new_value = None
            try:
                old_value = getattr(i[1], field)
            except ObjectDoesNotExist:
                old_value = None
            if not field_comparison(new_value, old_value):
                return False
    return True


def check_rigid_fields(obj, fields, old_instance=None, related=False):
    if not old_instance and not getattr(obj, 'old_instance', None):
        # since no old version of the object was passed in, we assume there were no changes
        return True, None
    for f_name in fields:
        old_instance = old_instance or obj.old_instance
        try:
            new_field = getattr(obj, f_name)
        except ObjectDoesNotExist:
            new_field = None
        try:
            old_field = getattr(old_instance, f_name)
        except ObjectDoesNotExist:
            # in case it's OneToOne related field
            old_field = None
        if hasattr(new_field, 'all'):
            # this could be a related field, unfortunately i can't figure out a isinstance check
            if related:
                if not check_rigid_related(obj, f_name):
                    return False, f_name

        elif not field_comparison(new_field, old_field):
            return False, f_name

    return True, None


class ValidatorViewMixin(object):

    def _parse_data(self, request):
        dt_cp = request.data
        for k in dt_cp:
            if dt_cp[k] in ['', 'null']:
                dt_cp[k] = None
            elif dt_cp[k] == 'true':
                dt_cp[k] = True
            elif dt_cp[k] == 'false':
                dt_cp[k] = False

        dt = parse_multipart_data(dt_cp)
        return dt

    def up_related_field(self, mother_obj, field, fieldClass, fieldSerializer, rel_prop_name, reverse_name,
                         partial=False, nested_related_names=None):
        if not field:
            return

        if isinstance(field, list):
            for item in field:
                item.update({reverse_name: mother_obj.pk})
                nested_related_data = {}
                if nested_related_names:
                    nested_related_data = {k: v for k, v in item.items() if k in nested_related_names}
                if item.get('id', None):
                    try:
                        instance = fieldClass.objects.get(id=item['id'])
                    except fieldClass.DoesNotExist:
                        instance = None

                    instance_serializer = fieldSerializer(instance=instance,
                                                          data=item,
                                                          partial=partial,
                                                          context=nested_related_data)
                else:
                    instance_serializer = fieldSerializer(data=item,
                                                          context=nested_related_data)

                try:
                    instance_serializer.is_valid(raise_exception=True)
                    # ValidationError can be raised by one of the sub-related fields inside the serializer on save
                    instance_serializer.save()
                except ValidationError as e:
                    e.detail = {rel_prop_name: e.detail}
                    raise e
        else:
            # This is in case we have a OneToOne field
            field.update({reverse_name: mother_obj.pk})
            nested_related_data = {}
            if nested_related_names:
                nested_related_data = {k: v for k, v in field.items() if k in nested_related_names}
            if field.get('id', None):
                try:
                    instance = fieldClass.objects.get(id=field['id'])
                except fieldClass.DoesNotExist:
                    instance = None

                instance_serializer = fieldSerializer(instance=instance,
                                                      data=field,
                                                      partial=partial,
                                                      context=nested_related_data)
            else:
                instance_serializer = fieldSerializer(data=field,
                                                      context=nested_related_data)

            try:
                instance_serializer.is_valid(raise_exception=True)
                # ValidationError can be raised by one of the sub-related fields inside the serializer on save
                instance_serializer.save()
            except ValidationError as e:
                e.detail = {rel_prop_name: e.detail}
                raise e

    def my_create(self, request, related_f, nested_related_names=None, **kwargs):
        my_relations = {}
        partial = kwargs.pop('partial', False)
        data = self._parse_data(request)

        for f in related_f:
            my_relations[f] = data.pop(f, [])

        main_serializer = self.get_serializer(data=data)
        main_serializer.context['skip_global_validator'] = True
        main_serializer.is_valid(raise_exception=True)

        main_object = main_serializer.save()

        def _get_model_for_field(field):
            return main_object.__class__._meta.get_field(field).related_model

        def _get_reverse_for_field(field):
            return main_object.__class__._meta.get_field(field).remote_field.name
        for k, v in my_relations.iteritems():
            self.up_related_field(main_object, v, _get_model_for_field(k), self.SERIALIZER_MAP[k],
                                  k, _get_reverse_for_field(k), partial, nested_related_names)

        return main_serializer

    def my_update(self, request, related_f, nested_related_names=None, **kwargs):
        partial = kwargs.pop('partial', False)
        data = self._parse_data(request)

        my_relations = {}
        for f in related_f:
            my_relations[f] = data.pop(f, [])

        old_instance = self.get_object()
        instance = self.get_object()
        main_serializer = self.get_serializer(instance, data=data, partial=partial)
        main_serializer.context['skip_global_validator'] = True
        main_serializer.is_valid(raise_exception=True)

        main_object = main_serializer.save()

        for k in my_relations.iterkeys():
            try:
                rel_field_val = getattr(old_instance, k)
            except ObjectDoesNotExist:
                pass
            else:
                prop = '{}_old'.format(k)

                try:
                    val = list(rel_field_val.all())
                except AttributeError:
                    # This means OneToOne field
                    val = rel_field_val

                setattr(old_instance, prop, val)

        def _get_model_for_field(field):
            return main_object.__class__._meta.get_field(field).related_model

        def _get_reverse_for_field(field):
            return main_object.__class__._meta.get_field(field).remote_field.name

        for k, v in my_relations.iteritems():
            self.up_related_field(main_object, v, _get_model_for_field(k), self.SERIALIZER_MAP[k],
                                  k, _get_reverse_for_field(k), partial, nested_related_names)

        return self.get_object(), old_instance, main_serializer


def _unicode_if(s):
    '''Given a string (str or unicode), always returns a unicode version of that string, converting it if necessary.

    This function is Python 2- and 3-compatible.
    '''
    # Under Python 2, we can use isinstance(s, unicode), but that syntax doesn't work under Python 3 because the
    # unicode type doesn't exist (only str which is Unicode by default). Instead I rely on the quirk that Python 2
    # str instances lack a method (.isnumeric()) that exists on Python 2 unicode instances and Python 3 str instances.
    return s if hasattr(s, 'isnumeric') else s.decode('utf-8')


@python_2_unicode_compatible
class _BaseStateError(BaseException):
    '''Base class for state-related exceptions. Accepts only one param which must be a list of strings.'''
    def __init__(self, message=[]):
        if not isinstance(message, list):
            raise TypeError('{} takes a list of errors not {}'.format(self.__class__, type(message)))
        super(_BaseStateError, self).__init__(message)

    def __str__(self):
        # There's only 1 arg, and it must be a list of messages. Under Python 2, that list might be a mix of unicode
        # and str instances, so we have to combine them carefully to avoid encode/decode errors.
        return u'\n'.join([_unicode_if(msg) for msg in self.args[0]])


class TransitionError(_BaseStateError):
    pass


class StateValidError(_BaseStateError):
    pass


class BasicValidationError(BaseException):
    def __init__(self, message=''):
        super(BasicValidationError, self).__init__(message)


def error_string(function):
    def wrapper(*args, **kwargs):
        try:
            valid = function(*args, **kwargs)
        except BasicValidationError as e:
            return (False, [str(e)])
        else:
            if valid and type(valid) is bool:
                return (True, [])
            else:
                return (False, [function.__name__])
    return wrapper


def transition_error_string(function):
    def wrapper(*args, **kwargs):
        try:
            valid = function(*args, **kwargs)
        except TransitionError as e:
            return (False, [str(e)])

        if valid and type(valid) is bool:
            return (True, [])
        else:
            return (False, ['generic_transition_fail'])
    return wrapper


def state_error_string(function):
    def wrapper(*args, **kwargs):
        try:
            valid = function(*args, **kwargs)
        except StateValidError as e:
            return (False, [str(e)])

        if valid and type(valid) is bool:
            return (True, [])
        else:
            return (False, ['generic_state_validation_fail'])
    return wrapper


def update_object(obj, kwdict):
    for k, v in kwdict.iteritems():
        setattr(obj, k, v)


class CompleteValidation(object):
    PERMISSIONS_CLASS = None

    def __init__(self, new, user=None, old=None, instance_class=None, stateless=False, disable_rigid_check=False):
        if old and isinstance(old, dict):
            raise TypeError('if old is transmitted to complete validation it needs to be a model instance')

        if isinstance(new, dict):
            # logging.debug('instance is dict')
            # logging.debug(old)
            if not old and not instance_class:
                try:
                    instance_class = apps.get_model(getattr(self, 'VALIDATION_CLASS'))
                except LookupError:
                    raise TypeError('Object transmitted for validation cannot be dict if instance_class is not defined')
            new_id = new.get('id', None) or new.get('pk', None)
            if new_id:
                # logging.debug('newid')
                # let it raise the error if it does not exist
                old_instance = old if old and old.id == new_id else instance_class.objects.get(id=new_id)
                new_instance = instance_class.objects.get(id=new_id)
                update_object(new_instance, new)

            else:
                # logging.debug('no id')
                old_instance = old
                # TODO: instance_class(**new) can't be called like that if models have m2m fields
                # Workaround for now is not to call the validator from the serializer on new instances
                new_instance = copy.deepcopy(old) if old else instance_class(**new)
                if old:
                    update_object(new_instance, new)
            new = new_instance
            old = old_instance

        self.stateless = stateless
        self.new = new
        if not self.stateless:
            self.new_status = self.new.status
        self.skip_transition = not old
        self.skip_permissions = not user

        # TODO: on old for related fields add the _old values in order to check for rigid fields if validator
        # was not called through the view using the viewmixin
        self.old = old
        if not self.stateless:
            self.old_status = self.old.status if self.old else None
        self.user = user

        # permissions to be set in each function that is needed, this attribute can change values as auto-update goes
        # through different statuses
        self.permissions = None
        self.disable_rigid_check = disable_rigid_check

    def get_permissions(self, instance):
        if self.PERMISSIONS_CLASS:
            p = self.PERMISSIONS_CLASS(
                user=self.user,
                instance=instance,
                permission_structure=self.new.permission_structure(),
                inbound_check=True)
            return p.get_permissions()
        return None

    def check_transition_conditions(self, transition):
        if not transition:
            return True
        return can_proceed(transition)

    def check_transition_permission(self, transition):
        if not transition:
            return True
        return has_transition_perm(transition, self.user)

    @cached_property
    def transition(self):
        return self._get_fsm_defined_transitions(self.old_status, self.new_status)

    @transition_error_string
    def transitional_validation(self):
        # set old status to get proper transitions
        self.new.status = self.old.status

        # set old instance on instance to make it available to the validation functions
        setattr(self.new, 'old_instance', self.old)
        self.permissions = self.get_permissions(self.new)

        # check conditions and permissions
        conditions_check = self.check_transition_conditions(self.transition)

        if self.skip_permissions:
            permissions_check = True
        else:
            permissions_check = self.check_transition_permission(self.transition)

        # cleanup
        delattr(self.new, 'old_instance')
        self.permissions = None
        self.new.status = self.new_status
        return conditions_check and permissions_check

    @state_error_string
    def state_valid(self):
        if not self.basic_validation[0]:
            return self.basic_validation

        result = True
        # set old instance on instance to make it available to the validation functions
        setattr(self.new, 'old_instance', self.old)
        self.permissions = self.get_permissions(self.new)

        funct_name = "state_{}_valid".format(self.new_status)
        # logging.debug('in state_valid finding function: {}'.format(funct_name))
        function = getattr(self, funct_name, None)
        if function:
            result = function(self.new, user=self.user)

        # cleanup
        delattr(self.new, 'old_instance')
        self.permissions = None
        # logging.debug('result is: {}'.format(result))
        return result

    def _get_fsm_defined_transitions(self, source, target):
        all_transitions = get_all_FIELD_transitions(self.new, self.new.__class__._meta.get_field('status'))
        for transition in all_transitions:
            if transition.source == source and target in transition.target:
                return getattr(self.new, transition.method.__name__)

    @transition_error_string
    def auto_transition_validation(self, potential_transition):
        # logging.debug('in auto transition validation {}'.format(potential_transition)

        result = self.check_transition_conditions(potential_transition)
        # logging.debug("check_transition_conditions returned: {}".format(result))
        return result

    def _first_available_auto_transition(self):

        potential = getattr(self.new.__class__, 'AUTO_TRANSITIONS', {})

        # ptt: Potential Transition To List
        list_of_status_choices = [i[0] for i in self.new.__class__._meta.get_field('status').choices]
        pttl = [i for i in potential.get(self.new.status, [])
                if i in list_of_status_choices]

        for potential_transition_to in pttl:
            # test to see if it's a viable transition:
            # template = "test to see if transition is possible : {} -> {}"
            # logging.debug(template.format(self.new.status, potential_transition_to))
            # try to find a possible transition... if no possible transition (transition was not defined on the model
            # it will always validate
            possible_fsm_transition = self._get_fsm_defined_transitions(self.new.status, potential_transition_to)
            if not possible_fsm_transition:
                template = "transition: {} -> {} is possible since there was no transition defined on the model"
                logging.debug(template.format(self.new.status, potential_transition_to))
            if self.auto_transition_validation(possible_fsm_transition)[0]:
                # get the side effects function if any
                SIDE_EFFECTS_DICT = getattr(self.new.__class__, 'TRANSITION_SIDE_EFFECTS', {})
                transition_side_effects = SIDE_EFFECTS_DICT.get(potential_transition_to, [])
                # logging.debug("transition is possible  {} -> {}".format(self.new.status, potential_transition_to))

                return True, potential_transition_to, transition_side_effects
            # logging.debug("transition is not possible : {} -> {}".format(self.new.status, potential_transition_to))
        return None, None, None

    def _make_auto_transition(self):
        valid_available_transition, new_status, auto_update_functions = self._first_available_auto_transition()
        if not valid_available_transition:
            return False
        else:
            # logging.debug("valid potential transition happening {}->{}".format(self.new.status, new_status))
            originals = self.new.status, self.new_status
            self.new.status = new_status
            self.new_status = new_status

            # logging.debug("making sure new state is valid: {}".format(self.new.status))
            state_valid = self.state_valid()
            # logging.debug("new state  {} is valid: {}".format(self.new.status, state_valid[0]))
            if not state_valid[0]:
                # set stuff back
                # logging.debug("state invalid because {}".format(state_valid[1]))
                self.new.status, self.new_status = originals
                return False

            # if all good run all the autoupdates on that status
            for function in auto_update_functions:
                # logging.debug("auto updating functions for transition")
                function(self.new, old_instance=self.old, user=self.user)
            return True

    def make_auto_transitions(self):
        # logging.debug("*************** STARTING AUTO TRANSITIONS *****************")
        any_transition_made = False

        # disable rigid_check in auto-transitions as they do not apply
        originial_rigid_check_setting = self.disable_rigid_check
        self.disable_rigid_check = True

        while self._make_auto_transition():
            any_transition_made = True

        # template = "*************** ENDING AUTO TRANSITIONS ***************** auto_transitioned: {}"
        # logging.debug(template.format(any_transition_made))

        # reset rigid check:
        self.disable_rigid_check = originial_rigid_check_setting
        return any_transition_made

    @cached_property
    def basic_validation(self):
        '''
        basic set of validations to make sure new state is correct
        :return: True or False
        '''

        setattr(self.new, 'old_instance', self.old)
        self.permissions = self.get_permissions(self.new)
        errors = []
        for validation_function in self.BASIC_VALIDATIONS:
            a = error_string(validation_function)(self.new)
            errors += a[1]
        delattr(self.new, 'old_instance')
        self.permissions = None
        return not len(errors), errors

    def map_errors(self, errors):
        return [self.VALID_ERRORS.get(error, error) for error in errors]

    def _apply_current_side_effects(self):
        # check if there was any transition so far:
        if self.old_status == self.new_status:
            return
        else:
            SIDE_EFFECTS_DICT = getattr(self.new.__class__, 'TRANSITION_SIDE_EFFECTS', {})
            transition_side_effects = SIDE_EFFECTS_DICT.get(self.new_status, [])
            for side_effect_function in transition_side_effects:
                side_effect_function(self.new, old_instance=self.old, user=self.user)

    @cached_property
    def total_validation(self):
        if not self.basic_validation[0]:
            return False, self.map_errors(self.basic_validation[1])

        if not self.skip_transition and not self.stateless:
            transitional = self.transitional_validation()
            if not transitional[0]:
                return False, self.map_errors(transitional[1])

        if not self.stateless:
            state_valid = self.state_valid()
            if not state_valid[0]:
                return False, self.map_errors(state_valid[1])

            # before checking if any further transitions can be made, if the current instance just transitioned,
            # apply side-effects:
            # TODO.. this needs to be re-written and have a consistent way to include side-effects on both
            # auto-transition / manual transition
            self._apply_current_side_effects()

            if self.make_auto_transitions():
                self.new.save()
        return True, []

    @property
    def is_valid(self):
        return self.total_validation[0]

    @property
    def errors(self):
        return self.total_validation[1]
