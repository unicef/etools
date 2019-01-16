from model_utils.managers import InheritanceManager


class InheritedModelMixin(object):
    """
    Mixin for easier access to subclasses. Designed to be tightly used with InheritanceManager
    """

    def get_subclass(self):
        if not self.pk:
            return self

        manager = self._meta.model._default_manager
        if not isinstance(manager, InheritanceManager):
            return self

        return manager.get_subclass(pk=self.pk)
