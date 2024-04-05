import logging

from django.utils.html import strip_tags

from rest_framework import status
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
        set_country('somalia')
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
        "MaterialNumber": "material",  # material.number
        "ItemDescription": "description",
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
        for_create = True
        try:
            organization = Organization.objects.get(vendor_number=transfer_dict['vendor_number'])
        except Organization.DoesNotExist:
            logging.error(f"No organization found in etools for {transfer_dict['vendor_number']}")
            return for_create, None

        if not hasattr(organization, 'partner'):
            logging.error(f'No partner in rwanda available for vendor_number {transfer_dict["vendor_number"]}')
            return for_create, None

        origin_point = models.PointOfInterest.objects.get(pk=1)  # Unicef Warehouse
        transfer_dict.pop('vendor_number')
        transfer_dict.update({
            'transfer_type': models.Transfer.DELIVERY,
            'partner_organization': organization.partner,
            'origin_point': origin_point
        })

        try:
            transfer_obj = models.Transfer.objects.get(unicef_release_order=transfer_dict['unicef_release_order'])
            for_create = False
            for field, value in transfer_dict.items():
                setattr(transfer_obj, field, value)
            return for_create, transfer_obj
        except models.Transfer.DoesNotExist:
            return for_create, models.Transfer(**transfer_dict)

    @staticmethod
    def import_items(transfer_items):
        items_to_create, items_to_update = [], []
        for unicef_ro, items in transfer_items.items():
            try:
                transfer = models.Transfer.objects.get(unicef_release_order=unicef_ro)
            except models.Transfer.DoesNotExist:
                logging.error(f"No transfer found in etools for UNICEF Release Order {unicef_ro}")
                continue

            for item_dict in items:
                try:
                    material = models.Material.objects.get(number=item_dict['material'])
                    item_dict['material'] = material
                    if item_dict['description'] != material.short_description:
                        models.PartnerMaterial.objects.update_or_create(
                            partner_organization=transfer.partner_organization,
                            material=material,
                            defaults={'description': item_dict['description']}
                        )
                    item_dict.pop('description')
                    if item_dict['uom'] == material.original_uom:
                        item_dict.pop('uom')
                except models.Material.DoesNotExist:
                    logging.error(f"No Material found in etools with # {item_dict['material']}")
                    continue
                try:
                    item_obj = models.Item.objects.get(
                        transfer__unicef_release_order=unicef_ro, unicef_ro_item=item_dict['unicef_ro_item'])
                    for field, value in item_dict.items():
                        setattr(item_obj, field, value)
                    items_to_update.append(item_obj)
                except models.Item.DoesNotExist:
                    item_dict['transfer'] = transfer
                    items_to_create.append(models.Item(**item_dict))

        models.Item.objects.bulk_create(items_to_create)
        models.Item.objects.bulk_update(
            items_to_update,
            fields=['unicef_ro_item', 'material', 'quantity', 'uom', 'batch_id', 'expiry_date',
                    'purchase_order_item', 'amount_usd', 'other']
        )

    def post(self, request):
        set_country('somalia')
        transfers_to_create, transfers_to_update = [], []
        transfer_items = {}
        for row in request.data:
            # only consider LD events
            if row['Event'] != 'LD':
                continue

            transfer_dict, item_dict = {}, {'other': {}}
            for k, v in row.items():
                if k in self.transfer_mapping:
                    transfer_dict[self.transfer_mapping[k]] = strip_tags(v)  # strip text that has html tags
                elif k in self.item_mapping:
                    if self.item_mapping[k] == 'other':
                        item_dict['other'].update({k: v})
                    elif self.item_mapping[k] == 'expiry_date':
                        item_dict[self.item_mapping[k]] = v if v else None
                    else:
                        item_dict[self.item_mapping[k]] = strip_tags(v)

            created, transfer_obj = self.get_transfer(transfer_dict)
            if not transfer_obj:
                continue

            if created and transfer_obj.unicef_release_order not in \
                    [o.unicef_release_order for o in transfers_to_create]:
                transfers_to_create.append(transfer_obj)
            elif not created and transfer_obj.unicef_release_order not in \
                    [o.unicef_release_order for o in transfers_to_update]:
                transfers_to_update.append(transfer_obj)

            if transfer_dict['unicef_release_order'] in transfer_items:
                transfer_items[transfer_dict['unicef_release_order']].append(item_dict)
            else:
                transfer_items[transfer_dict['unicef_release_order']] = [item_dict]

        models.Transfer.objects.bulk_create(transfers_to_create)
        models.Transfer.objects.bulk_update(
            transfers_to_update,
            fields=['purchase_order_id', 'pd_number', 'waybill_id', 'origin_check_out_at']
        )
        self.import_items(transfer_items)

        return Response(status=status.HTTP_200_OK)
