from django.apps import AppConfig


class PartnersAppConfig(AppConfig):
    name = 'partners'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Agreement'))
        registry.register(self.get_model('PartnerOrganization'))
        registry.register(self.get_model('PartnerStaffMember'))
        registry.register(self.get_model('Assessment'))
        registry.register(self.get_model('BankDetails'))
        registry.register(self.get_model('AuthorizedOfficer'))
        registry.register(self.get_model('PCA'))
        registry.register(self.get_model('Intervention'))
        registry.register(self.get_model('AmendmentLog'))
        registry.register(self.get_model('AgreementAmendmentLog'))
        registry.register(self.get_model('PartnershipBudget'))
        registry.register(self.get_model('PCAGrant'))
        registry.register(self.get_model('GwPCALocation'))
        registry.register(self.get_model('PCASector'))
        registry.register(self.get_model('PCASectorGoal'))
        registry.register(self.get_model('FileType'))
        registry.register(self.get_model('PCAFile'))
        registry.register(self.get_model('RAMIndicator'))
        registry.register(self.get_model('IndicatorDueDates'))
        registry.register(self.get_model('IndicatorReport'))
        registry.register(self.get_model('SupplyPlan'))
        registry.register(self.get_model('FundingCommitment'))
        registry.register(self.get_model('DirectCashTransfer'))
