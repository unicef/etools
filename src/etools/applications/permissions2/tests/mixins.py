from rest_framework import status


class TransitionPermissionTestCaseMetaclass(type):
    @staticmethod
    def _collect_transitions(model):
        transitions = []
        for attr_name in dir(model):
            attr = getattr(model, attr_name, None)

            if hasattr(attr, '_django_fsm'):
                transitions.append(attr_name)

        return transitions

    @staticmethod
    def _annotate_test(klass, obj_status, transition):
        def test(self):
            obj = self.create_object(transition, **{
                self.status_field.name: obj_status,
            })

            result = self.do_transition(obj, transition)

            success, message = self.check_result(result, obj, transition)

            self.assertTrue(success, message)

        model = klass.model
        model_name = model._meta.model_name
        test_name = 'test_{}_for_{}_{}'.format(transition, obj_status, model_name)
        setattr(klass, test_name, test)

    def __new__(cls, name, bases, attrs):
        abstract = attrs.get('abstract', False)

        newclass = super().__new__(cls, name, bases, attrs)

        if abstract:
            return newclass

        newclass.transitions = cls._collect_transitions(newclass.model)
        newclass.status_field = getattr(newclass.model, newclass.transitions[0])._django_fsm.field
        newclass.statuses = list(zip(*newclass.status_field.choices))[0]

        for obj_status in newclass.statuses:
            for transition in newclass.transitions:
                cls._annotate_test(newclass, obj_status, transition)

        return newclass


class TransitionPermissionsTestCaseMixin(object, metaclass=TransitionPermissionTestCaseMetaclass):
    """
    TestCase mixin for dynamic transitions testing.
    All you need is to specify list of allowed transitions and user to be used.
    All tests will be generated automatically with correct output depending from user role.
    """
    abstract = True
    model = NotImplemented
    factory = NotImplemented

    def create_object(self, transition, **kwargs):
        return self.factory(**kwargs)

    def do_transition(self, obj, transition):
        raise NotImplementedError

    def check_result(self, result, obj, transition):
        allowed = (obj.status, transition) in self.ALLOWED_TRANSITION
        success = result.status_code == status.HTTP_200_OK
        forbidden = result.status_code == status.HTTP_403_FORBIDDEN

        model_name = obj._meta.verbose_name

        if allowed and not success:
            return False, 'Error on {} {} {} by {}.\n{}: {}'.format(transition, obj.status, model_name, self.user_role,
                                                                    result.status_code, result.content)

        if not allowed and success:
            return False, 'Success for not allowed transition. {} can\'t {} {} {}.'.format(self.user_role, transition,
                                                                                           obj.status, model_name)

        if not allowed and not forbidden:
            return False, 'Error on {} {} {} by {}.\n{}: {}'.format(transition, obj.status, model_name, self.user_role,
                                                                    result.status_code, result.content)

        return True, ''

    def get_extra_obj_attrs(self, **kwargs):
        attrs = {}
        attrs.update(kwargs)
        return attrs
