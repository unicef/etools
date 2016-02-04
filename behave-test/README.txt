# Run a Behave test for EquiTrack
# This test will generate a final report and screenshot for test errors

# Install required libraries
$ pip install requirements.txt

# Check the configuration file 'behave.ini'

# Base command with default configuration in 'behave.ini'
$ python run.py

# Options
  -h, --help                                show this help message and exit
  -rt REPORT, --report REPORT               define the report dir
  -sh SCREENSHOT, --screenshot SCREENSHOT   define the screenshot dir
  -ft FEATURE, --feature FEATURE            define a specific feature to test
  -t TAGS, --tags TAGS                      define a specific tags to test (@tag1,@tag2)
  -d DRIVER, --driver DRIVER                define a specific feature to test (firefox chrome android)
  -sr SENDREPORT, --sendreport SENDREPORT   send test result by email
  -v, --version                             show program's version number and exit


# Tags list:
# @dev @staging
# @partnerships @partner @agreement @intervention
# @trips @trip @actpoint
# @screenshot
# @web
# @ios
# @android


# How to run a test only for UniSupply
$ python run.py --tags=@unisupply


# How to run a test for UniSupply and screenshot
$ python run.py --tags=@unisupply,@screenshot


# How to run a test for all feature without UniSupply
$ python run.py --tags=@web,~@unisupply


# run an android test for UniSupply feature
$ java -jar selendroid-standalone-0.17.0-with-dependencies.jar -app unisupply-nepal.apk
$ python run.py --tags=@appunisupply --driver=android


# How to create a scenario:
1. Download Selenium IDE on your Firefox (http://docs.seleniumhq.org/projects/ide/)
2. Go to your web page (using Firefox)
3. Click on the Selenium IDE button in the toolbar (top right)
4. Keep the IDE's popup open and switch to your browser
5. Browse some pages
6. Switch to your IDE, go to File -> Export test as ... -> Python 2 / unittest / WebDriver