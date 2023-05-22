import functools
import operator

from django.db.models import Q


class ExternalModuleFilterMixin:
    """
    Mixin which allow to filter based on current user:
    - UNICEF Users and Read Only API will get the whole queryset
    - External Users would use filter defined in module2filters

    module2filters is a dictionary where:
    - key: name of the module in order to get filters
    - value: list of filter used for matching (item would show if one or more filters match)
    """
    param_name = 'externals_module'
    module2filters = {}

    def get_queryset(self, module=None):
        qs = super().get_queryset()
        user = self.request.user
        if not (user.is_unicef_user() or user.groups.filter(name="Read-Only API").exists()):
            if module is None:
                query_params = self.request.query_params
                module = query_params.get(self.param_name, None)
            if module in self.module2filters:
                queries = []
                for user_filter in self.module2filters[module]:
                    if callable(user_filter):
                        queries.append(user_filter(user))
                    else:
                        queries.append(Q(**{user_filter: user}))
                if queries:
                    qs = qs.filter(functools.reduce(operator.or_, queries)).distinct()
            else:
                # if no module query param or module has an unexpected value return none
                return qs.model.objects.none()
        return qs
