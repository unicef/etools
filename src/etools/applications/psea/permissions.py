from etools_validator.utils import check_rigid_related

from etools.applications.partners.permissions import PMPPermissions


class AssessmentPermissions(PMPPermissions):
    MODEL_NAME = 'psea.Assessment'

    def __init__(self, **kwargs):
        """
        :param kwargs: user, instance, permission_structure
        if 'inbound_check' key, is sent in, that means that instance now
        contains all of the fields available in the validation:
        old_instance, old.instance.property_old in case of related fields.
        the reason for this is so that we can check the more complex
        permissions that can only be checked on save.
        for example: in this case certain field are editable only when user
        adds an amendment. that means that we would need access to the old
        amendments, new amendments in order to check this.
        """
        super().__init__(**kwargs)
        inbound_check = kwargs.get('inbound_check', False)

        def user_belongs(instance):
            assert inbound_check, 'this function cannot be called unless instantiated with inbound_check=True'
            # check_rigid_related checks if there were any changes from
            # the previous amendments if there were changes it returns False
            return not check_rigid_related(instance, 'assessment')

        self.condition_map = {
            'user belongs': False if not inbound_check else user_belongs(
                self.instance,
            )
        }
