from rest_framework import serializers

from etools.applications.snapshot.models import Activity
from etools.applications.snapshot.utils import create_dict_with_relations, create_snapshot


class ActivitySerializer(serializers.ModelSerializer):
    by_user_display = serializers.ReadOnlyField()

    class Meta:
        model = Activity
        fields = "__all__"


class SnapshotModelSerializer(serializers.ModelSerializer):
    def save(self, **kwargs):
        pre_save = create_dict_with_relations(self.instance)
        super(SnapshotModelSerializer, self).save(**kwargs)
        create_snapshot(self.instance, pre_save, self.context["request"].user)
        return self.instance
