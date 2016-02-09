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
      Then select your supervisor from the drop-down list
       And select your section and office location
       And enter the From date and To date of trip
       And add a Purpose of travel
      Then select the Travel type and Travel focal point
      Then enter the Travel Itinerary
      Then press "Save"


  @actpoint
  Scenario: visit eTools and test add action point
     Given go to "Action points" from trips section
      Then click "Add action point"
      Then enter action point information
      Then press "Save" to save the new action point

