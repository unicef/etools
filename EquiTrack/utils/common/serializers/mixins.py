from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.utils import model_meta


class UserContextSerializerMixin(object):
    def get_user(self):
        return self.context.get('user') or self.context.get('request').user


class PkSerializerMixin(object):
    _pk_field = None

    @property
    def pk_field(self):
        if self._pk_field:
            return self._pk_field

        assert hasattr(self, 'Meta'), (
            'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        assert hasattr(self.Meta, 'model'), (
            'Class {serializer_class} missing "Meta.model" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        if model_meta.is_abstract_model(self.Meta.model):
            raise ValueError(
                'Cannot use ModelSerializer with Abstract Models.'
            )

        model = self.Meta.model
        info = model_meta.get_field_info(model)

        if 'pk' in self.fields:
            self._pk_field = self.fields['pk']
            return self._pk_field

        if info.pk.name in self.fields:
            self._pk_field = self.fields[info.pk.name]
            return self._pk_field

        assert False, 'Serializer {serializer_class} doesn\'t contain primary key field. ' \
                      'Add `pk` or `{pk_name}` to fields attribute.'.format(serializer_class=self.__class__.__name__,
                                                                            pk_name=info.pk.name)
