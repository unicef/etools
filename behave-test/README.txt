# Run a Behave test for EquiTrack
# This test will generate a final report and screenshot for test errors

# Base command with default configuration in 'behave.ini'
python run.py

# Options
  -h, --help                                show this help message and exit
  -rt REPORT, --report REPORT               define the report dir
  -sh SCREENSHOT, --screenshot SCREENSHOT   define the screenshot dir
  -ft FEATURE, --feature FEATURE            define a specific feature to test
  -t TAGS, --tags TAGS                      define a specific tags to test
  -sr SENDREPORT, --sendreport SENDREPORT   send test result by email
  -v, --version                             show program's version number and exit
  -d, --driver                              run test with which driver (firefox, chrome)


# Work in progress

merge report result and errors screenshots
