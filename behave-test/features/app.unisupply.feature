@android
Feature: Supply and distribution monitoring in eTools using the UniSupply mobile application

  @appunisupply
  Scenario: installing and launching UniSupply for the first time
     Given launch UniSupply app
      Then tap on the link for First Time users
      Then press the plus button
       And you will be asked to name your preference setting to proceed. Type any name
      Then enter in the following details in the fields provided
      When tap "Switch Environment"
      Then you should now see your preference name in the list
      Then tap "UniSupply" to return to login screen

    @appunisupply
    Scenario: recording distributions in UniSupply (for partners)
      Given login into UniSupply with the credentials provided by your UNICEF focal point "aaademo" and "aaademo"
       Then you will see a list of all distributions by district and supply type
       Then tap on any district name to see the distribution details
       When you tap on the item name to record the quantities distributed in this location
       Then you can scroll up through the numbers
        And you type a number into the number field
        And you can click on "Complete All" to record all quantities distributed
        And press "done" to return to the district details screen
        And you will see that the district details have updated
       Then press "done" to return to the main screen
        And the overview and reports screens will also reflect delivery status
        And continue updating deliveries as necessary
       When all items for one district have been completed
       Then the item will be moved from the "started" tab into the "finished" tab
        And to move a distribution to the "finished" tab manually
       Then tap the "Force Completion" button on a distribution
        And to ensure that distributions are synced with the eTools system.Go to the "Sync" tab
        And tap "Force Sync"
