from __future__ import unicode_literals

from decimal import Decimal, getcontext, InvalidOperation

from rest_framework import serializers

from t2f.models import Invoice, InvoiceItem


def round_to_currency_precision(currency, amount):
    if currency.decimal_places:
        q = Decimal('1.' + '0' * currency.decimal_places)
    else:
        q = Decimal('1')

    try:
        return amount.quantize(q)
    except InvalidOperation:
        # Fall back to a slower option but make sure to get the best precision possible
        max_precision = getcontext().prec
        amount_tuple = amount.as_tuple()
        max_decimal_places = max_precision - len(amount_tuple[1]) - amount_tuple[2]
        return amount.quantize(Decimal('1.' + '0' * max_decimal_places))


class InvoiceItemSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceItem
        fields = ('wbs', 'grant', 'fund', 'amount')

    def get_amount(self, obj):
        return str(round_to_currency_precision(obj.invoice.currency, obj.amount))


class InvoiceSerializer(serializers.ModelSerializer):
    ta_number = serializers.CharField(source='travel.reference_number', read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    message = serializers.CharField(read_only=True)

    class Meta:
        model = Invoice
        fields = ('id', 'travel', 'reference_number', 'business_area', 'vendor_number', 'currency', 'amount', 'status',
                  'messages', 'message', 'vision_fi_id', 'ta_number', 'items')

    def to_representation(self, instance):
        data = super(InvoiceSerializer, self).to_representation(instance)
        data['amount'] = str(round_to_currency_precision(instance.currency, instance.amount))
        return data
