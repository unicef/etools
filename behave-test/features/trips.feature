@web
@dev
@staging
@trips
Feature: testing trips features

  @trip
  Scenario: visit eTools and test add trip
     Given go to "Trips" from the trips section
      Then click "Add trip"
      Then you will find your name selected by default as a traveller
      Then select the supervisor "Tarek Moubarak" from the drop-down list
       And select the section "SPPME" and office location "Beirut"
       And enter the From date and To date of trip
       And add a Purpose of travel "Testing behave selenium"
      Then select the Travel type "TECHNICAL SUPPORT" and Travel focal point "Tarek Moubarak"
      Then enter the Travel Itinerary "Beirut" to/from "Saida"
      Then press "Save"
      Then delete the trip number "00000"


  @actpoint
  Scenario: visit eTools and test add action point
     Given go to "Action points" from trips section
      Then click "Add action point"
      Then enter action point information "task action list"
      Then press "Save" to save the new action point

