from import_export import fields, resources, widgets

from etools.applications.last_mile.models import PointOfInterest, PointOfInterestType
from etools.applications.partners.models import PartnerOrganization
# from etools.applications.users.models import User


class PoiUserResource(resources.ModelResource):
    class Meta:
        model = PointOfInterest

        skip_unchanged = True

        fields = (
            'name', 'poi_type', 'is_private', 'latitude', 'longitude', 'partner_organizations',
            'username', 'first_name', 'last_name', 'email')

    name = fields.Field('name', column_name='LOCATION NAME')
    poi_type = fields.Field(
        'poi_type', column_name='PRIMARY TYPE *',
        widget=widgets.ForeignKeyWidget(PointOfInterestType, 'id'), saves_null_values=True)
    is_private = fields.Field(
        'is_private', column_name='IS PRIVATE***', widget=widgets.BooleanWidget(),
        default=False)
    partner_organization = fields.Field(
        'partner_organization', column_name='IP Number',
        widget=widgets.ManyToManyWidget(PartnerOrganization, 'vendor_number'))
    # User fields
    first_name = fields.Field('first_name', column_name='First Name')
    last_name = fields.Field('last_name', column_name='Last Name')
    email = fields.Field('email', column_name='Email address', saves_null_values=False)

    def before_import_row(self, row, **kwargs):
        row['username'] = row['Email address']

        if row['PRIMARY TYPE *']:
            poi_type, _ = PointOfInterestType.objects.get_or_create(
                name=row['PRIMARY TYPE *'].strip(), category=row['PRIMARY TYPE *'].strip().lower().replace(' ', '_'))
            row['poi_type'] = poi_type.id

        try:
            partner_obj = PartnerOrganization.objects.get(vendor_number=str(row['IP Number']))
            row['partner_organization'] = partner_obj
            #
        except PartnerOrganization.DoesNotExist:
            raise AttributeError(f"The Partner with vendor number '{row['IP Number']}' does not exist.")

    def get_instance(self, instance_loader, row):
        try:
            return PointOfInterest.objects.get(name=row.get('LOCATION NAME').strip())
        except PointOfInterest.DoesNotExist:
            return False

    def save_m2m(self, obj, data, using_transactions, dry_run):
        obj.partner_organizations.add(data['partner_organization'])
