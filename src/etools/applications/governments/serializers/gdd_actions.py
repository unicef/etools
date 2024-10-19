from etools.applications.governments.models import GDDReview
from rest_framework import serializers


class AmendedGDDReviewActionSerializer(serializers.ModelSerializer):
    review_type = serializers.ChoiceField(required=True, choices=GDDReview.ALL_REVIEW_TYPES)

    class Meta:
        model = GDDReview
        fields = ('id', 'review_type')


class GDDReviewActionSerializer(serializers.ModelSerializer):
    review_type = serializers.ChoiceField(required=True, choices=GDDReview.INTERVENTION_REVIEW_TYPES)

    class Meta:
        model = GDDReview
        fields = ('id', 'review_type')


class GDDReviewSendBackSerializer(serializers.ModelSerializer):
    class Meta:
        model = GDDReview
        fields = ('id', 'sent_back_comment')
        extra_kwargs = {
            'sent_back_comment': {'required': True},
        }
