import ConfigParser

from datetime import datetime


class Utils:

    def __init__(self, browser):
        self.ctr = 1
        self.ctrE = 1
        self.browser = browser
        self.basedir = 'screenshots/'
        self.current = datetime.now().strftime('%Y-%m-%d')
        self.dir = self.basedir + self.current
        self.dirErrors = 'reports/' + self.current + '/errors'


    def screenshot(self, name):
        name = str(self.ctr) + ' - ' + name + '.png'
        self.browser.get_screenshot_as_file(self.dir + '/' + name)
        self.ctr += 1


    def screenshoterror(self):
        name = str(self.ctrE) + ' - ' + 'error.png'
        self.browser.get_screenshot_as_file(self.dirErrors + '/' + name)
        self.ctrE += 1


    def readBaseConfig(self):
        config = ConfigParser.ConfigParser()
        config.read('behave.ini')
        return config


    def readConfig(self, name):
        config = self.readBaseConfig()
        return config.get('etools', name)
