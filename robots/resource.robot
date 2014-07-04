*** Settings ***
Documentation     A resource file with reusable keywords and variables.
...
...               The system specific keywords created here form our own
...               domain specific language. They utilize keywords provided
...               by the imported Selenium2Library.
Library           Selenium2Library

*** Variables ***
${SERVER}         localhost:8000
${BROWSER}        Firefox
${DELAY}          0.5
${VALID USER}     admin
${VALID PASS}     admin
${BASE URL}       http://${SERVER}/

*** Keywords ***
Open Browser To Login Page
    Open Browser    ${BASE URL}    ${BROWSER}
    Maximize Browser Window
    Set Selenium Speed    ${DELAY}
    Login Page Should Be Open

Login Page Should Be Open
    Title Should Be    EquiTrack

Go To Login Page
    Go To    ${LOGIN URL}
    Login Page Should Be Open

Input Username
    [Arguments]    ${username}
    Input Text    username    ${username}

Input Password
    [Arguments]    ${password}
    Input Text    password    ${password}

Submit Credentials
    Click Button    Sign In

Welcome Page Should Be Open
    Title Should Be    EquiTrack


