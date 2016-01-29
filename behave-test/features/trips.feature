@dev
@staging
@trips
Feature: testing trips features

  @trip
  Scenario: visit eTools and test add trip
     Given add a trip
      Then fill trip info
      Then delete the new trip

  @actpoint
  Scenario: visit eTools and test add action point
     Given add an action point
      Then delete the new action point
