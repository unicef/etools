import json
import logging
from datetime import datetime

from django.db.models import F, FloatField, Func
from django.http import StreamingHttpResponse
from django.utils.html import strip_tags

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.last_mile import models
from etools.applications.last_mile.permissions import LMSMAPIPermission
from etools.applications.last_mile.serializers_ext import MaterialIngestResultSerializer, MaterialIngestSerializer
from etools.applications.last_mile.services_ext import MaterialIngestService
from etools.applications.organizations.models import Organization
from etools.libraries.pythonlib.encoders import CustomJSONEncoder


class VisionIngestMaterialsApiView(APIView):
    permission_classes = (LMSMAPIPermission,)

    def post(self, request):
        input_serializer = MaterialIngestSerializer(data=request.data, many=True)
        input_serializer.is_valid(raise_exception=True)

        ingest_result = MaterialIngestService().ingest_materials(
            validated_data=input_serializer.validated_data
        )

        output_serializer = MaterialIngestResultSerializer(ingest_result)

        return Response(output_serializer.data, status=status.HTTP_200_OK)


class GeometryPointFunc(Func):
    template = "%(function)s(%(expressions)s::geometry)"

    def __init__(self, expression):
        super().__init__(expression, output_field=FloatField())


class Latitude(GeometryPointFunc):
    function = 'ST_Y'


class Longitude(GeometryPointFunc):
    function = 'ST_X'


def get_annotated_qs(qs):
    if qs.model == models.Transfer:
        return qs.annotate(vendor_number=F('partner_organization__organization__vendor_number'),
                           checked_out_by_email=F('checked_out_by__email'),
                           checked_out_by_first_name=F('checked_out_by__first_name'),
                           checked_out_by_last_name=F('checked_out_by__last_name'),
                           checked_in_by_email=F('checked_in_by__email'),
                           checked_in_by_last_name=F('checked_in_by__last_name'),
                           checked_in_by_first_name=F('checked_in_by__first_name'),
                           origin_name=F('origin_point__name'),
                           destination_name=F('destination_point__name'),
                           ).values()

    if qs.model == models.PointOfInterest:
        return qs.prefetch_related('parent', 'poi_type').annotate(
            latitude=Latitude('point'),
            longitude=Longitude('point'),
            parent_pcode=F('parent__p_code'),
            vendor_number=F('partner_organizations__organization__vendor_number'),
        ).values('id', 'created', 'modified', 'parent_id', 'name', 'description', 'poi_type_id',
                 'other', 'private', 'is_active', 'latitude', 'longitude', 'parent_pcode', 'p_code', 'vendor_number')

    if qs.model == models.Item:
        return qs.annotate(material_number=F('material__number'),
                           material_description=F('material__short_description'),
                           ).values()
    return qs.values()


class VisionLMSMExport(APIView):
    permission_classes = (LMSMAPIPermission,)

    def get(self, request, *args, **kwargs):
        model_param = request.query_params.get('type')
        model_manager_map = {
            "transfer": models.Transfer.objects,
            "poi": models.PointOfInterest.all_objects,
            "item": models.Item.objects,
            "item_history": models.ItemTransferHistory.objects,
            "poi_type": models.PointOfInterestType.objects,
        }
        queryset = model_manager_map.get(model_param)
        if not queryset:
            return Response({"type": "invalid data model"}, status=status.HTTP_400_BAD_REQUEST)

        last_modified_param = request.query_params.get('last_modified', None)

        if last_modified_param:
            try:
                gte_dt = datetime.fromisoformat(last_modified_param)
            except ValueError:
                return Response({"last_modified": "invalid format"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                queryset = queryset.filter(modified__gte=gte_dt)

        queryset = get_annotated_qs(queryset)

        def data_stream(qs):
            yield '['  # Start of JSON array
            first = True
            for obj in qs.iterator():
                if not first:
                    yield ','
                else:
                    first = False
                yield json.dumps(obj, cls=CustomJSONEncoder)
            yield ']'  # End of JSON array

        response = StreamingHttpResponse(data_stream(queryset), content_type='application/json')
        return response


class VisionIngestTransfersApiView(APIView):
    permission_classes = (LMSMAPIPermission,)
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
        try:
            organization = Organization.objects.get(vendor_number=transfer_dict['vendor_number'])
        except Organization.DoesNotExist:
            logging.error(f"No organization found in etools for {transfer_dict['vendor_number']}")
            return None

        if not hasattr(organization, 'partner'):
            logging.error(f'No partner available for vendor_number {transfer_dict["vendor_number"]}')
            return None

        origin_point = models.PointOfInterest.objects.get(pk=1)  # Unicef Warehouse
        transfer_dict.pop('vendor_number')
        transfer_dict.update({
            'transfer_type': models.Transfer.DELIVERY,
            'partner_organization': organization.partner,
            'origin_point': origin_point
        })

        try:
            transfer_obj = models.Transfer.objects.get(unicef_release_order=transfer_dict['unicef_release_order'])
            return transfer_obj
        except models.Transfer.DoesNotExist:
            return models.Transfer(**transfer_dict)

    @staticmethod
    def import_items(transfer_items):
        items_to_create = []
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
                    item_dict.pop('description')
                    if item_dict['uom'] == material.original_uom:
                        item_dict.pop('uom')
                except models.Material.DoesNotExist:
                    logging.error(f"No Material found in etools with # {item_dict['material']}")
                    continue

                try:
                    models.Item.objects.get(other__itemid=f"{unicef_ro}-{item_dict['unicef_ro_item']}")
                except models.Item.DoesNotExist:
                    try:
                        models.Item.objects.get(
                            transfer__unicef_release_order=unicef_ro, unicef_ro_item=item_dict['unicef_ro_item'])
                    except models.Item.DoesNotExist:
                        item_dict['transfer'] = transfer
                        item_dict['base_quantity'] = item_dict['quantity']
                        if not item_dict.get('batch_id'):
                            item_dict['conversion_factor'] = 1.0
                            item_dict['uom'] = "EA"
                        items_to_create.append(models.Item(**item_dict))

        models.Item.objects.bulk_create(items_to_create)

    def post(self, request):
        transfers_to_create = []
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
            item_dict['other']['itemid'] = f"{transfer_dict['unicef_release_order']}-{item_dict['unicef_ro_item']}"

            transfer_obj = self.get_transfer(transfer_dict)
            if not transfer_obj:
                continue

            if not transfer_obj.pk and transfer_obj.unicef_release_order not in [o.unicef_release_order for o in transfers_to_create]:
                transfers_to_create.append(transfer_obj)

            if transfer_dict['unicef_release_order'] in transfer_items:
                transfer_items[transfer_dict['unicef_release_order']].append(item_dict)
            else:
                transfer_items[transfer_dict['unicef_release_order']] = [item_dict]

        models.Transfer.objects.bulk_create(transfers_to_create)
        self.import_items(transfer_items)

        return Response(status=status.HTTP_200_OK)
