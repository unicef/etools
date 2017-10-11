from django.apps import AppConfig


class PartnersAppConfig(AppConfig):
    name = 'partners'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Agreement'))
        registry.register(self.get_model('PartnerOrganization'))
        registry.register(self.get_model('PartnerStaffMember'))
        registry.register(self.get_model('Assessment'))
        registry.register(self.get_model('Intervention'))
        registry.register(self.get_model('AgreementAmendmentLog'))
        registry.register(self.get_model('FileType'))
        registry.register(self.get_model('IndicatorReport'))
        registry.register(self.get_model('FundingCommitment'))
        registry.register(self.get_model('DirectCashTransfer'))
