from __future__ import unicode_literals


class ModelExporter(object):
    def __init__(self):
        self._registry = {}  # Model class -> Exporter class

    @classmethod
    def export_queryset(cls, queryset):
        pass

    @classmethod
    def export_instance(cls, instance):
        pass
