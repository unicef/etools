from utils import *
from selenium import webdriver


def before_feature(context, scenario):
    context.execute_steps(u'''
       given login to eTools
   ''')
    # context.execute_steps(u'''
    #     given login to eTools "username" and "password!"
    # ''')


def after_feature(context, scenario):
    context.execute_steps(u'''
       given logout from eTools
   ''')


def before_all(context):
    # context.execute_steps(u'''
    #     Given login to eTools
    # ''')
    context.browser = webdriver.Firefox()
    context.browser.maximize_window()
    context.browser.set_window_size(1400, 1200)
    context.util = Utils(context.browser)
    context.browser.implicitly_wait(30)
    context.base_url = context.util.readConfig('baseurl')
    context.verificationErrors = []
    context.accept_next_alert = True


def after_all(context):
    # context.execute_steps(u'''
    #     given logout from eTools
    # ''')
    context.browser.quit()
