from config import *

import time


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

    def highlight(self, element, name=''):
        """Highlights (blinks) a Selenium Webdriver element"""
        original_style = element.get_attribute('style')
        self.browser.execute_script("arguments[0].setAttribute('style', arguments[1]);",
                                    element, "border: 2px solid red !important;")
        time.sleep(.3)
        self.screenshot(name)
        time.sleep(.3)
        self.browser.execute_script("arguments[0].setAttribute('style', arguments[1]);",
                                  element, original_style)
