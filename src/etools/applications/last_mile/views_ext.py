import logging

from django.utils.html import strip_tags

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.core.util_scripts import set_country
from etools.applications.last_mile import models
from etools.applications.organizations.models import Organization


class VisionIngestMaterialsApiView(APIView):
    mapping = {
        'MaterialNumber': 'number',
        'ShortDescription': 'short_description',
        'UnitOfMeasurement': 'original_uom',
        'MaterialType': 'material_type',
        'MaterialTypeDescription': 'material_type_description',
        'MaterialGroup': 'group',
        'MaterialGroupDescription': 'group_description',
        'PurchasingGroup': 'purchase_group',
        'PurchasingGroupDescription': 'purchase_group_description',
        'HazardousGoods': 'hazardous_goods',
        'HazardousGoodsDescription': 'hazardous_goods_description',
        'TempConditions': 'temperature_conditions',
        'TempDescription': 'temperature_group',
        'PurchasingText': 'purchasing_text'
    }

    def post(self, request):
        set_country('rwanda')
        materials_to_create = []
        materials_to_update = []
        for material in request.data:
            model_dict = {}
            for k, v in material.items():
                if k in self.mapping:
                    model_dict[self.mapping[k]] = strip_tags(v)  # strip text that has html tags
            try:
                obj = models.Material.objects.get(number=model_dict['number'])
                for field, value in model_dict.items():
                    setattr(obj, field, value)
                materials_to_update.append(obj)
            except models.Material.DoesNotExist:
                materials_to_create.append(models.Material(**model_dict))

        models.Material.objects.bulk_create(materials_to_create)
        models.Material.objects.bulk_update(materials_to_update, fields=list(self.mapping.values()))

        return Response(status=status.HTTP_200_OK)


class VisionIngestTransfersApiView(APIView):
    transfer_mapping = {
        "ReleaseOrder": "unicef_release_order",
        "PONumber": "purchase_order_id",
        "EtoolsReference": "pd_number",
        "WaybillNumber": "waybill_id",
        "DocumentCreationDate": "origin_check_out_at",
        "ImplementingPartner": "vendor_number",
    }
    item_mapping = {
        "ReleaseOrderItem": "unicef_ro_item",
        "MaterialNumber": "number",  # material.number
        "ItemDescription": "name",
        "Quantity": "quantity",
        "UOM": "uom",
        "BatchNumber": "batch_id",
        "ExpiryDate": "expiry_date",
        "POItem": "purchase_order_item",
        "AmountUSD": "amount_usd",
        "HandoverNumber": "other",
        "HandoverItem": "other",
        "HandoverYear": "other",
        "Plant": "other",
        "PurchaseOrderType": "other",
    }

    @staticmethod
    def get_transfer(transfer_dict):
        created = True
        try:
            organization = Organization.objects.get(vendor_number=transfer_dict['vendor_number'])
        except Organization.DoesNotExist:
            logging.error(f"No organization found in etools for {transfer_dict['vendor_number']}")
            return created, None

        if not hasattr(organization, 'partner'):
            logging.error(f'No partner in rwanda available for vendor_number {transfer_dict["vendor_number"]}')
            return created, None

        origin_point = models.PointOfInterest.objects.get(pk=1)  # Unicef Warehouse
        transfer_dict.pop('vendor_number')
        transfer_dict.update({
            'partner_organization': organization.partner,
            'origin_point': origin_point
        })

        try:
            transfer_obj = models.Transfer.objects.get(unicef_release_order=transfer_dict['unicef_release_order'])
            created = False
            for field, value in transfer_dict.items():
                setattr(transfer_obj, field, value)
            return created, transfer_obj
        except models.Transfer.DoesNotExist:
            return created, models.Transfer(**transfer_dict)

    def post(self, request):
        set_country('rwanda')
        transfers_to_create, transfers_to_update = [], []
        items_to_create, items_to_update = [], []
        for transfer in request.data:
            # only consider LD events
            if transfer['Event'] != 'LD':
                continue

            transfer_dict, item_dict = {}, {'other': {}}
            for k, v in transfer.items():
                if k in self.transfer_mapping:
                    transfer_dict[self.transfer_mapping[k]] = strip_tags(v)  # strip text that has html tags
                elif k in self.item_mapping:
                    if self.item_mapping[k] == 'other':
                        item_dict['other'].update({k: v})
                    else:
                        item_dict[self.item_mapping[k]] = strip_tags(v)

            created, transfer_obj = self.get_transfer(transfer_dict)
            if not transfer_obj:
                continue
            if created:
                transfers_to_create.append(transfer_obj)
            else:
                transfers_to_update.append(transfer_obj)

        models.Transfer.objects.bulk_create(transfers_to_create)
        models.Transfer.objects.bulk_update(
            transfers_to_update,
            fields=['purchase_order_id', 'pd_number', 'waybill_id', 'origin_check_out_at'])

        return Response(status=status.HTTP_200_OK)
