from django.db.models import CharField, EmailField


class LowerCaseMixin:

    def pre_save(self, model_instance, add):
        """ Returns field's value just before saving. """
        attr = getattr(model_instance, self.attname)
        if attr is not None:
            attr = attr.lower()
            setattr(model_instance, self.attname, attr)
        return attr

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            value = value.lower()
        return value


class LowerCaseField(LowerCaseMixin, CharField):
    pass


class LowerCaseEmailField(LowerCaseMixin, EmailField):
    pass
