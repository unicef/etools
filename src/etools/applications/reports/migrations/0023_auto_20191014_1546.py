# Generated by Django 2.2.4 on 2019-10-14 15:46

from django.db import connection, migrations


# def convert_tenant_profile_data(apps, schema):
#     """For each UserProfile setup office relation in ProfileOffice
#     for each country that UserProfile has available
#     Use the connection to determine the current country
#     """
#     if connection.tenant.schema_name not in ["test", "public"]:
#         UserProfile = apps.get_model("users", "userprofile")
#         UserTenantProfile = apps.get_model("reports", "usertenantprofile")
#         Office = apps.get_model("reports", "office")
#         Country = apps.get_model("users", "country")
#         country = Country.objects.get(
#             schema_name=connection.tenant.schema_name,
#         )
#         for profile in UserProfile.objects.all():
#             if profile.office and country in profile.countries_available.all():
#                 try:
#                     office = Office.objects.get(pk=profile.office.pk)
#                 except Office.DoesNotExist:
#                     # assume that office is from another schema
#                     pass
#                 else:
#                     UserTenantProfile.objects.create(
#                         profile=profile,
#                         office=office,
#                     )


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0022_userprofileoffice'),
    ]

    operations = [
    ]
