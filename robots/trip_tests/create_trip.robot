*** Settings ***
Documentation    Creates a trip in EquiTrack
Resource         ../resource.robot


*** Test Cases ***
Create Trip
    [Tags]    DEBUG
    Go To   ${BASE URL}/admin/trips/trip
    Login Page Should Be Open
    Input Username    ${VALID USER}
    Input Password    ${VALID PASS}
    Submit Credentials



*** Keywords ***
Provided precondition
    Setup system under test