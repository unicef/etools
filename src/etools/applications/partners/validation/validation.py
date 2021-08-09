from django.utils.functional import cached_property

from etools.applications.partners.validation.decorators import transition_error_dict, state_error_dict


class DetailedErrorValidationMixin(object):
    @transition_error_dict
    def transitional_validation(self):
        return super().transitional_validation()

    @state_error_dict
    def state_valid(self):
        return super().state_valid()

    @transition_error_dict
    def auto_transition_validation(self, potential_transition):
        return super().auto_transition_validation(potential_transition)

    @cached_property
    def basic_validation(self):
        # todo: replace a = error_string(validation_function)(self.new)
        return super().basic_validation

    def map_errors(self, errors):
        return [self.VALID_ERRORS.get(error, error) if isinstance(error, str) else error for error in errors]
