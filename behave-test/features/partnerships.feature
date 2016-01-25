@dev
@staging
Feature: testing partnerships features

  @partner
  Scenario: visit eTools and test adding partner organization
     Given add a partner organization
      Then delete the new partner organization

  @argeement
  Scenario: visit eTools and test adding agreement
     Given add an agreement
      Then delete the new agreement

  @intervention
  Scenario: visit eTools and test adding intervention
     Given add an intervention
      Then delete the new intervention