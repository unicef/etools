from factory.base import FactoryMetaClass


class StatusFactoryMetaClass(FactoryMetaClass):
    """
    Factory metaclass to generate object in correct status with dependent attributes.
    When new object is generated, metaclass check for corresponding factory in provided status_factories
    and if found, generate instance using it.
    """

    def __call__(cls, **kwargs):
        status = kwargs.pop('status', None)
        factory = cls._status_factories.get(status)
        if factory:
            return factory(**kwargs)

        return super().__call__(**kwargs)

    def __new__(mcs, class_name, bases, attrs):
        # hide status_factories property to avoid it being consumed by model.create
        status_factories = attrs.pop('status_factories', {})
        new_class = super().__new__(mcs, class_name, bases, attrs)
        new_class._status_factories = status_factories
        return new_class
