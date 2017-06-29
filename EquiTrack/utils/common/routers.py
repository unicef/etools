from rest_framework_nested import routers


class NestedComplexRouter(routers.NestedSimpleRouter):
    def register(self, prefix, viewset, base_name=None):
        super(NestedComplexRouter, self).register(prefix, viewset, base_name=base_name)

        parent_registry = [registered for registered in self.parent_router.registry if
                           registered[0] == self.parent_prefix]
        try:
            parent_registry = parent_registry[0]
            parent_prefix, parent_viewset, parent_basename = parent_registry
        except:
            raise RuntimeError('parent registered resource not found')

        viewset.parent = parent_viewset
        viewset.parent_lookup_field = self.nest_prefix[:-1]
        viewset.parent_lookup_kwarg = '{}{}'.format(self.nest_prefix, getattr(viewset, 'lookup_field', 'pk'))
