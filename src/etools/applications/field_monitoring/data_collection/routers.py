import copy

from unicef_restlib.routers import NestedComplexRouter


class NestedBulkRouter(NestedComplexRouter):
    """
    Map http methods to actions defined on the bulk mixins.
    """
    routes = copy.deepcopy(NestedComplexRouter.routes)
    routes[0].mapping.update({
        'put': 'bulk_update',
        'patch': 'partial_bulk_update',
        'delete': 'bulk_destroy',
    })
