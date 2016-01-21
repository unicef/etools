from config import *


class Utils:

    def __init__(self, browser):
        self.ctr = 1
        self.ctrE = 1
        self.browser = browser


    def screenshot(self, name):
        name = str("%02d" % self.ctr) + ' - ' + name + '.png'
        self.browser.get_screenshot_as_file(read_config('screenshot_dir') + '/' + name)
        self.ctr += 1


    def screenshot_error(self):
        name = str("%02d" % self.ctrE) + ' - ' + 'error.png'
        self.browser.get_screenshot_as_file(read_config('report_dir_errors') + '/' + name)
        self.ctrE += 1


    def read_config(self, name):
        return read_config(name)
