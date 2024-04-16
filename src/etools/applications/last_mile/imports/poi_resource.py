from django.contrib.gis.geos import Point

from import_export import fields, resources, widgets

from etools.applications.last_mile.models import PointOfInterest, PointOfInterestType
from etools.applications.partners.models import PartnerOrganization


class PoiUserResource(resources.ModelResource):

    class Meta:
        model = PointOfInterest

        use_transactions = True
        use_bulk = False

        skip_unchanged = True

        fields = ('name', 'private', 'point', 'poi_type', 'partner_organizations')

    name = fields.Field('name', column_name='LOCATION NAME')
    partner_organizations = fields.Field(
        attribute='partner_organizations', column_name='IP Number',
        widget=widgets.ManyToManyWidget(PartnerOrganization, field='id'))
    poi_type = fields.Field(
        attribute='poi_type', column_name='PRIMARY TYPE *',
        widget=widgets.ForeignKeyWidget(PointOfInterestType, field='name'), saves_null_values=True)
    private = fields.Field(
        'private', column_name='IS PRIVATE***', widget=widgets.BooleanWidget(),
        default=False)
    latitude = fields.Field(column_name='LATITUDE', widget=widgets.DecimalWidget())
    longitude = fields.Field(column_name='LONGITUDE', widget=widgets.DecimalWidget())

    def skip_row(self, instance, original):
        if not instance.point:
            return True
        return super().skip_row(instance, original)

    def before_import_row(self, row, **kwargs):
        row['IS PRIVATE***'] = True if row['IS PRIVATE***'] and row['IS PRIVATE***'].lower().strip() == 'yes' else False

        if row['PRIMARY TYPE *']:
            row['PRIMARY TYPE *'] = row['PRIMARY TYPE *'].strip()
            poi_type, _ = PointOfInterestType.objects.get_or_create(
                name=row['PRIMARY TYPE *'], category=row['PRIMARY TYPE *'].lower().replace(' ', '_'))

        try:
            row['IP Number'] = PartnerOrganization.objects.get(vendor_number=str(row['IP Number']).strip()).id
        except PartnerOrganization.DoesNotExist:
            raise AttributeError(f"The Partner with vendor number '{row['IP Number']}' does not exist.")

        long = row.pop('LONGITUDE')
        lat = row.pop('LATITUDE')
        try:
            row['point'] = Point(float(long), float(lat))
        except (TypeError, ValueError):
            print(f'Row # {kwargs["row_number"]}  Long/Lat Format error: {long}, {lat}')
            pass

    def get_instance(self, instance_loader, row):
        return PointOfInterest.objects.filter(point=row.get('point'), name=row.get('LOCATION NAME').strip()).first()
