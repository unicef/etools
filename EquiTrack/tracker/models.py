# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.
from __future__ import unicode_literals

from django.db import models


class Yiilog(models.Model):
    id = models.IntegerField(primary_key=True)
    level = models.CharField(max_length=128L, blank=True)
    category = models.CharField(max_length=128L, blank=True)
    logtime = models.IntegerField(null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        db_table = 'YiiLog'


class Action(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255L)
    comment = models.TextField(blank=True)
    subject = models.CharField(max_length=255L, blank=True)

    class Meta:
        db_table = 'action'


class CopyLocations(models.Model):
    latitude = models.DecimalField(decimal_places=6, null=True, max_digits=10, db_column='Latitude', blank=True) # Field name made lowercase.
    longitude = models.DecimalField(decimal_places=6, null=True, max_digits=10, db_column='Longitude', blank=True) # Field name made lowercase.
    governorate_un = models.CharField(max_length=13L, db_column='Governorate_UN', blank=True) # Field name made lowercase.
    caza = models.CharField(max_length=16L, db_column='Caza', blank=True) # Field name made lowercase.
    cadastral_local_name = models.CharField(max_length=42L, db_column='Cadastral_Local_NAME', blank=True) # Field name made lowercase.
    village_name = models.CharField(max_length=35L, db_column='Village_Name', blank=True) # Field name made lowercase.
    p_code = models.CharField(max_length=9L, db_column='P_code', blank=True) # Field name made lowercase.
    cas_code = models.IntegerField(null=True, db_column='CAS_CODE', blank=True) # Field name made lowercase.
    cas_code_un = models.CharField(max_length=8L, db_column='CAS_CODE_UN', blank=True) # Field name made lowercase.
    cad_code = models.CharField(max_length=9L, db_column='CAD_CODE', blank=True) # Field name made lowercase.
    cas_village_name = models.CharField(max_length=42L, db_column='CAS_Village_NAME', blank=True) # Field name made lowercase.
    mohafaza = models.CharField(max_length=13L, db_column='MOHAFAZA', blank=True) # Field name made lowercase.
    elevation = models.IntegerField(null=True, db_column='Elevation', blank=True) # Field name made lowercase.

    class Meta:
        db_table = 'copy_locations'


class Friendship(models.Model):
    inviter_id = models.IntegerField()
    friend_id = models.IntegerField()
    status = models.IntegerField()
    acknowledgetime = models.IntegerField(null=True, blank=True)
    requesttime = models.IntegerField(null=True, blank=True)
    updatetime = models.IntegerField(null=True, blank=True)
    message = models.CharField(max_length=255L)

    class Meta:
        db_table = 'friendship'


class Locdata(models.Model):
    location_id = models.IntegerField(primary_key=True)
    locality_id = models.IntegerField()
    name = models.CharField(max_length=45L, blank=True)
    latitude = models.DecimalField(null=True, max_digits=12, decimal_places=5, blank=True)
    longitude = models.DecimalField(null=True, max_digits=12, decimal_places=5, blank=True)
    p_code = models.CharField(max_length=32L, blank=True)

    class Meta:
        db_table = 'locdata'


class Membership(models.Model):
    id = models.IntegerField(primary_key=True)
    membership_id = models.IntegerField()
    user_id = models.IntegerField()
    payment_id = models.IntegerField()
    order_date = models.IntegerField()
    end_date = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=255L, blank=True)
    street = models.CharField(max_length=255L, blank=True)
    zipcode = models.CharField(max_length=255L, blank=True)
    city = models.CharField(max_length=255L, blank=True)
    payment_date = models.IntegerField(null=True, blank=True)
    subscribed = models.IntegerField()

    class Meta:
        db_table = 'membership'


class Message(models.Model):
    id = models.IntegerField(primary_key=True)
    timestamp = models.IntegerField()
    from_user_id = models.IntegerField()
    to_user_id = models.IntegerField()
    title = models.CharField(max_length=255L)
    message = models.TextField(blank=True)
    message_read = models.IntegerField()
    answered = models.IntegerField(null=True, blank=True)
    draft = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'message'


class Payment(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255L)
    text = models.TextField(blank=True)

    class Meta:
        db_table = 'payment'


class Permission(models.Model):
    principal_id = models.IntegerField()
    subordinate_id = models.IntegerField()
    type = models.CharField(max_length=4L)
    action = models.IntegerField()
    template = models.IntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        db_table = 'permission'


class Privacysetting(models.Model):
    user_id = models.IntegerField(primary_key=True)
    message_new_friendship = models.IntegerField()
    message_new_message = models.IntegerField()
    message_new_profilecomment = models.IntegerField()
    appear_in_search = models.IntegerField()
    show_online_status = models.IntegerField()
    log_profile_visits = models.IntegerField()
    ignore_users = models.CharField(max_length=255L, blank=True)
    public_profile_fields = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'privacysetting'


class Profile(models.Model):
    id = models.IntegerField(primary_key=True)
    user_id = models.IntegerField()
    lastname = models.CharField(max_length=50L)
    firstname = models.CharField(max_length=50L)
    email = models.CharField(max_length=255L)
    street = models.CharField(max_length=255L, blank=True)
    city = models.CharField(max_length=255L, blank=True)
    about = models.TextField(blank=True)

    class Meta:
        db_table = 'profile'


class ProfileComment(models.Model):
    id = models.IntegerField(primary_key=True)
    user_id = models.IntegerField()
    profile_id = models.IntegerField()
    comment = models.TextField()
    createtime = models.IntegerField()

    class Meta:
        db_table = 'profile_comment'


class ProfileVisit(models.Model):
    visitor_id = models.IntegerField()
    visited_id = models.IntegerField()
    timestamp_first_visit = models.IntegerField()
    timestamp_last_visit = models.IntegerField()
    num_of_visits = models.IntegerField()

    class Meta:
        db_table = 'profile_visit'


class Role(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255L)
    description = models.CharField(max_length=255L, blank=True)
    membership_priority = models.IntegerField(null=True, blank=True)
    price = models.FloatField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'role'


class Activity(models.Model):
    activity_id = models.IntegerField(primary_key=True)
    sector = models.ForeignKey('Sector', null=True, blank=True)
    name = models.CharField(max_length=128L)
    type = models.CharField(max_length=30L, blank=True)

    class Meta:
        db_table = 'tbl_activity'


class Donor(models.Model):
    donor_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=45L, blank=True)

    class Meta:
        db_table = 'tbl_donor'


class Gateway(models.Model):
    gateway_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=64L)

    class Meta:
        db_table = 'tbl_gateway'


class Goal(models.Model):
    goal_id = models.IntegerField(primary_key=True)
    sector = models.ForeignKey('Sector')
    name = models.CharField(max_length=512L)
    description = models.CharField(max_length=512L, blank=True)

    class Meta:
        db_table = 'tbl_goal'

    def __unicode__(self):
        return self.name


class Governorate(models.Model):
    governorate_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=45L)

    class Meta:
        db_table = 'tbl_governorate'


class Grant(models.Model):
    grant_id = models.IntegerField(primary_key=True)
    donor = models.ForeignKey(Donor)
    name = models.CharField(max_length=128L)

    class Meta:
        db_table = 'tbl_grant'

    def __unicode__(self):
        return u"{}: {}".format(
            self.donor.name,
            self.name
        )


class GwPcaLoc(models.Model):
    id = models.IntegerField(primary_key=True)
    gateway = models.ForeignKey(Gateway, null=True, blank=True)
    pca = models.ForeignKey('PCA')
    location = models.ForeignKey('Location')
    name = models.CharField(max_length=128L)

    class Meta:
        db_table = 'tbl_gw_pca_loc'


class IntermediateResult(models.Model):
    ir_id = models.IntegerField(primary_key=True)
    sector = models.ForeignKey('Sector')
    ir_wbs_reference = models.CharField(max_length=50L)
    name = models.CharField(max_length=128L)

    class Meta:
        db_table = 'tbl_intermediate_result'


class Locality(models.Model):
    locality_id = models.IntegerField(primary_key=True)
    region = models.ForeignKey('Region')
    cad_code = models.CharField(max_length=11L)
    cas_code = models.CharField(max_length=11L)
    cas_code_un = models.CharField(max_length=11L)
    name = models.CharField(max_length=128L)
    cas_village_name = models.CharField(max_length=128L)

    class Meta:
        db_table = 'tbl_locality'


class Location(models.Model):
    location_id = models.IntegerField(primary_key=True)
    locality = models.ForeignKey(Locality)
    name = models.CharField(max_length=45L, blank=True)
    latitude = models.DecimalField(null=True, max_digits=12, decimal_places=5, blank=True)
    longitude = models.DecimalField(null=True, max_digits=12, decimal_places=5, blank=True)
    p_code = models.CharField(max_length=32L, blank=True)

    class Meta:
        db_table = 'tbl_location'


class LocationGateway(models.Model):
    location = models.ForeignKey(Location)
    gateway = models.ForeignKey(Gateway)

    class Meta:
        db_table = 'tbl_location_gateway'


class PartnerLocation(models.Model):
    partner = models.ForeignKey('PartnerOrganization')
    location = models.ForeignKey(Location)

    class Meta:
        db_table = 'tbl_partner_location'


class PartnerOrganization(models.Model):
    partner_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=45L)
    description = models.CharField(max_length=256L, blank=True)
    email = models.CharField(max_length=128L, blank=True)
    contact_person = models.CharField(max_length=64L, blank=True)
    phone_number = models.CharField(max_length=32L, blank=True)

    class Meta:
        db_table = 'tbl_partner_organization'

    def __unicode__(self):
        return self.name


class PartnerOrganizationActivity(models.Model):

    partner = models.ForeignKey(PartnerOrganization)
    activity = models.ForeignKey(Activity)

    class Meta:
        db_table = 'tbl_partner_organization_activity'


class Sector(models.Model):
    sector_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=45L)
    description = models.CharField(max_length=256L, blank=True)

    # proxy attributes, non schema altering
    pcas = models.ManyToManyField('PCA', through='PcaSector')

    class Meta:
        db_table = 'tbl_sector'

    def __unicode__(self):
        return self.name


class PCA(models.Model):
    pca_id = models.IntegerField(primary_key=True)
    number = models.CharField(max_length=45L, blank=True)
    title = models.CharField(max_length=256L, blank=True)
    status = models.CharField(max_length=32L, blank=True)
    partner = models.ForeignKey(PartnerOrganization, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    initiation_date = models.DateField(null=True, blank=True)
    signed_by_unicef_date = models.DateField(null=True, blank=True)
    signed_by_partner_date = models.DateField(null=True, blank=True)
    unicef_mng_first_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_last_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_email = models.CharField(max_length=128L, blank=True)
    partner_mng_first_name = models.CharField(max_length=64L, blank=True)
    partner_mng_last_name = models.CharField(max_length=64L, blank=True)
    partner_mng_email = models.CharField(max_length=128L, blank=True)
    partner_contribution_budget = models.IntegerField(null=True, blank=True)
    unicef_cash_budget = models.IntegerField(null=True, blank=True)
    in_kind_amount_budget = models.IntegerField(null=True, blank=True)
    cash_for_supply_budget = models.IntegerField(null=True, blank=True)
    total_cash = models.IntegerField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)
    is_approved = models.NullBooleanField(null=True, blank=True)

    # proxy attributes, non schema altering
    sectors = models.ManyToManyField(Sector, through='PcaSector')

    class Meta:
        db_table = 'tbl_pca'

    def __unicode__(self):
        return self.number


class PcaActivity(models.Model):
    pca = models.ForeignKey(PCA)
    activity = models.ForeignKey(Activity)

    class Meta:
        db_table = 'tbl_pca_activity'


class PcaFile(models.Model):
    pca_file_id = models.IntegerField(primary_key=True)
    pca = models.ForeignKey(PCA)
    file_name = models.CharField(max_length=256L)
    file_category = models.CharField(max_length=32L)

    class Meta:
        db_table = 'tbl_pca_file'


class PcaGrant(models.Model):
    pca = models.ForeignKey(PCA, primary_key=True)
    grant = models.ForeignKey(Grant)
    funds = models.IntegerField()

    class Meta:
        db_table = 'tbl_pca_grant'

    def __unicode__(self):
        return self.grant


class PcaReport(models.Model):
    pca_report_id = models.IntegerField(primary_key=True)
    pca = models.ForeignKey(PCA)
    title = models.CharField(max_length=128L)
    description = models.CharField(max_length=512L)
    start_period = models.DateField(null=True, blank=True)
    end_period = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_pca_report'


class PcaReportFile(models.Model):
    pca_report_file_id = models.IntegerField(primary_key=True)
    pca_report = models.ForeignKey(PcaReport)
    file_name = models.CharField(max_length=256L)

    class Meta:
        db_table = 'tbl_pca_report_file'


class PcaRrp5Output(models.Model):
    pca = models.ForeignKey(PCA, primary_key=True)
    rrp5_output = models.ForeignKey('Rrp5Output')

    class Meta:
        db_table = 'tbl_pca_rrp5output'

    def __unicode__(self):
        return self.rrp5_output


class Rrp5Output(models.Model):
    rrp5_output_id = models.IntegerField(primary_key=True)
    sector = models.ForeignKey('Sector')
    code = models.CharField(max_length=16L)
    name = models.CharField(max_length=256L)

    class Meta:
        db_table = 'tbl_rrp5_output'
        verbose_name = 'RRP5 Output'

    def __unicode__(self):
        return self.name


class PcaSector(models.Model):
    pca = models.ForeignKey(PCA, primary_key=True)
    sector = models.ForeignKey('Sector')

    # new M2Ms added by JCW
    Rrp5Outputs = models.ManyToManyField(Rrp5Output)
    target_progress = models.ManyToManyField('TargetProgress')

    class Meta:
        db_table = 'tbl_pca_sector'

    def __unicode__(self):
        return self.sector.name


class PcaTarget(models.Model):
    pca = models.ForeignKey(PCA, primary_key=True)
    target = models.ForeignKey('Target')

    class Meta:
        db_table = 'tbl_pca_target'


class PcaTargetProgress(models.Model):
    target_id = models.IntegerField()
    unit_id = models.IntegerField()
    pca = models.ForeignKey(PCA, primary_key=True)
    total = models.IntegerField()
    current = models.IntegerField()
    shortfall = models.IntegerField()
    start_date = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField()
    active = models.IntegerField()

    class Meta:
        db_table = 'tbl_pca_target_progress'


class TargetProgress(models.Model):
    target = models.ForeignKey('Target', primary_key=True)
    unit = models.ForeignKey('Unit')
    total = models.IntegerField()
    current = models.IntegerField()
    shortfall = models.IntegerField()
    received_date = models.DateTimeField()
    start_date = models.DateField(null=True, blank=True)
    active = models.IntegerField()

    class Meta:
        db_table = 'tbl_target_progress'


class PcaTargetProgressCopy1(models.Model):
    target_id = models.IntegerField()
    unit_id = models.IntegerField()
    pca_id = models.IntegerField()
    total = models.IntegerField()
    current = models.IntegerField()
    shortfall = models.IntegerField()
    start_date = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField()
    active = models.IntegerField()

    class Meta:
        db_table = 'tbl_pca_target_progress_copy1'


class PcaUfile(models.Model):
    pca = models.ForeignKey(PCA)
    file = models.ForeignKey('UploadedFile')

    class Meta:
        db_table = 'tbl_pca_ufile'


class PcaUserAction(models.Model):
    user_action_id = models.IntegerField(primary_key=True)
    pca_id = models.IntegerField()
    pca_number = models.CharField(max_length=512L)
    pca_title = models.CharField(max_length=512L)
    user_id = models.IntegerField()
    action = models.CharField(max_length=32L)
    datetime = models.DateTimeField()

    class Meta:
        db_table = 'tbl_pca_user_action'


class PcaWbs(models.Model):
    pca = models.ForeignKey(PCA)
    wbs = models.ForeignKey('WBS')

    class Meta:
        db_table = 'tbl_pca_wbs'


class Region(models.Model):
    region_id = models.IntegerField(primary_key=True)
    governorate = models.ForeignKey(Governorate)
    name = models.CharField(max_length=45L)

    class Meta:
        db_table = 'tbl_region'


class SectorRole(models.Model):
    role = models.ForeignKey(Role)
    sector = models.ForeignKey(Sector)

    class Meta:
        db_table = 'tbl_sector_role'


class SectorUser(models.Model):
    user = models.ForeignKey('User')
    sector = models.ForeignKey(Sector)

    class Meta:
        db_table = 'tbl_sector_user'


class Target(models.Model):
    target_id = models.IntegerField(primary_key=True)
    goal = models.ForeignKey(Goal)
    name = models.CharField(max_length=128L)

    class Meta:
        db_table = 'tbl_target'


class TargetActivity(models.Model):
    activity = models.ForeignKey(Activity)
    target = models.ForeignKey(Target)

    class Meta:
        db_table = 'tbl_target_activity'


class TargetProgressBackup(models.Model):
    target_id = models.IntegerField()
    unit_id = models.IntegerField()
    total = models.IntegerField()
    current = models.IntegerField()
    shortfall = models.IntegerField()
    received_date = models.DateTimeField()
    active = models.IntegerField()

    class Meta:
        db_table = 'tbl_target_progress_backup'


class TargetProgressPcaReport(models.Model):
    target = models.ForeignKey(TargetProgress, related_name='pca_reports')
    unit = models.ForeignKey(TargetProgress)
    pca_report = models.ForeignKey(PcaReport)
    total = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_target_progress_pca_report'


class Unit(models.Model):
    unit_id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=45L)

    class Meta:
        db_table = 'tbl_unit'


class UploadedFile(models.Model):
    file_id = models.IntegerField(primary_key=True)
    file_name = models.CharField(max_length=256L, blank=True)
    file_type = models.CharField(max_length=32L, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    file_content = models.TextField(blank=True)
    file_category = models.CharField(max_length=64L)

    class Meta:
        db_table = 'tbl_uploaded_file'


class WBS(models.Model):
    wbs_id = models.IntegerField(primary_key=True)
    ir = models.ForeignKey(IntermediateResult)
    name = models.CharField(max_length=128L)
    code = models.CharField(max_length=10L)

    class Meta:
        db_table = 'tbl_wbs'


class Translation(models.Model):
    message = models.CharField(max_length=255L)
    translation = models.CharField(max_length=255L)
    language = models.CharField(max_length=5L)
    category = models.CharField(max_length=255L)

    class Meta:
        db_table = 'translation'


# ----- Yii auth models -----

class User(models.Model):
    id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=20L, unique=True)
    password = models.CharField(max_length=128L)
    salt = models.CharField(max_length=128L)
    activationkey = models.CharField(max_length=128L, db_column='activationKey') # Field name made lowercase.
    createtime = models.IntegerField()
    lastvisit = models.IntegerField()
    lastaction = models.IntegerField()
    lastpasswordchange = models.IntegerField()
    failedloginattempts = models.IntegerField()
    superuser = models.IntegerField()
    status = models.IntegerField()
    avatar = models.CharField(max_length=255L, blank=True)
    notifytype = models.CharField(max_length=9L, db_column='notifyType', blank=True) # Field name made lowercase.

    class Meta:
        db_table = 'user'


class UserGroupMessage(models.Model):
    id = models.IntegerField(primary_key=True)
    author_id = models.IntegerField()
    group_id = models.IntegerField()
    createtime = models.IntegerField()
    title = models.CharField(max_length=255L)
    message = models.TextField()

    class Meta:
        db_table = 'user_group_message'


class UserRole(models.Model):
    user_id = models.IntegerField()
    role_id = models.IntegerField()

    class Meta:
        db_table = 'user_role'


class Usergroup(models.Model):
    id = models.IntegerField(primary_key=True)
    owner_id = models.IntegerField()
    participants = models.TextField(blank=True)
    title = models.CharField(max_length=255L)
    description = models.TextField()

    class Meta:
        db_table = 'usergroup'

