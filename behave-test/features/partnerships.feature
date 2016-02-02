@web
@dev
@staging
@partnerships
Feature: testing partnerships features

  @partner
  Scenario: visit eTools and test adding partner organization
     Given add a partner organization
      Then delete the new partner organization

  @agreement
  Scenario: visit eTools and test adding agreement
     Given add an agreement
      Then delete the new agreement

  @intervention
  Scenario: visit eTools and test adding intervention
     Given add an intervention
      Then delete the new intervention

  @unisupply
  Scenario: creating a supply plan in eTools
     Given go to "Interventions" from the partnership section
      Then click "add intervention"
      Then select an existing partner from the drop-down partner
      Then select an existing agreement for that partner and enter a reference number for this agreement
      Then select the appropriate Document Type for this intervention
      Then add a Title for this intervention
      Then go to the "Supplies" tab in the intervention to insert supplies
      Then select a supply from the drop-down list
      Then continue adding supplies and quantities. Click "Save and continue editing" to save the supply plan

  @unisupply
  Scenario: creating a distribution plan in eTools
    Given add an item from the supply plan to the distribution plan
     Then select a location where the item will be distributed from the pre-defined list of districts for your country
     Then enter in the quantities for this distribution location. Select "Send to partner" to send the distribution to the UniSuppy app
     Then continue adding items, locations, and quantities from your supply plan to the distribution plan
      But you cannot exceed the quantity outlined in the supply plan
     Then press "Save and continue editing" to save the plans and sync with the app
     When the partners begin to distribute supplies via UniSupply
     Then you will be able to the status of the deliveries in this section
