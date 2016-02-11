@web
@dev
@staging
@partnerships
Feature: testing partnerships features

  @partner
  Scenario: visit eTools and test adding partner organization
     Given we test partnerships features
      Then go to "Partners" from the partnership section
      Then click "Add partner organization"
      Then enter partner's Full name "Test Vesion" and Short name "testv"
       And select an exiting Partner type "Civil Society Organisation" and CSO type "National NGO" from the drop-down list
       And enter the partner's Alternate name "testvision"
       And enter the partners main address "31 Test Way", main phone number "123456789" and main email "someone@ngo.org"
       And press "Save" to add this new partner

  @agreement
  Scenario: visit eTools and test adding agreement
     Given we test partnerships features
      Then go to "Agreements" from the partnership section
      Then click "Add agreement"
      Then select a partner "TestVision" from the drop-down list
       And select an Agreement type "Work Plan"
       And enter the Reference Number "TTV00012345"
       And enter the Start and End date of this agreement
      Then press "Save" to save the new agreement

  @intervention
  @supplyplan
  @unisupply
  Scenario: creating a supply plan in eTools
     Given we test partnerships features
      Then go to "Interventions" from the partnership section
      Then click "add intervention"
      Then select an existing partner "AAA Demo Partner" from the drop-down partner
      Then select an existing agreement "PCA for AAA Demo Partner (16-12-2015 - 16-12-2015)" for that partner and enter a reference number for this agreement "AAA00003"
      Then select the appropriate Document Type "Programme Document" for this intervention
      Then add a Title for this intervention "Distribution of hygiene kits in Kabul"
      Then go to the "Supplies" tab in the intervention to insert supplies
      Then select a supply from the drop-down list
      Then continue adding supplies and quantities
          | item                        | quantity  |
          | Family hygiene kit          | 6000      |
          | Water purification tablet   | 3000      |
          | Tarpaulin                   | 10000     |
      Then press "Save and continue editing" to save the supply plan

  @intervention
  @distribplan
  @unisupply
  Scenario: creating a distribution plan in eTools
    Given add an item from the supply plan to the distribution plan "Water purification tablet"
     Then select a location where the item will be distributed from the pre-defined list of districts for your country "ACHHAM"
     Then enter in the quantities "2000" for this distribution location
     Then select "Send to partner" to send the distribution to the UniSuppy app
     Then continue adding items, locations, and quantities from your supply plan to the distribution plan
          | item                        | location  | quantity  |
          | Water purification tablet   | ACHHAM    | 2000      |
          | Water purification tablet   | SAPTARI   | 1000      |
          | Family hygiene kit          | BHOJPUR   | 3000      |
      But you cannot exceed the quantity outlined in the supply plan
          | item                        | location  | quantity  |
          | Family hygiene kit          | SALYAN    | 1000      |
          | Tarpaulin                   | KATHMANDU | 8000      |
#          | Water purification tablet   | SAPTARI   | 500       |
     Then press "Save and continue editing" to save the plans and sync with the app
     When the partners begin to distribute supplies via UniSupply
     Then you will be able to the status of the deliveries in this section

    @unisupply
    Scenario: rollback added partnership informations
      Given we test partnerships features
       Then go to "Interventions" from the partnership section
        And delete the intervention number "AAA00003"
       Then go to "Agreements" from the partnership section
        And delete the agreement number "TTV00012345"
       Then go to "Partners" from the partnership section
        And delete the partner organization number "TestVision"
       