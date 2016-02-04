from utils import *
from selenium import webdriver

import config

BEHAVE_DEBUG_ON_ERROR = False


def setup_debug_on_error(userdata):
    global BEHAVE_DEBUG_ON_ERROR
    BEHAVE_DEBUG_ON_ERROR = userdata.getbool("BEHAVE_DEBUG_ON_ERROR")


def before_feature(context, scenario):
    driver = config.read_config('driver')
    if driver == 'android':
        pass
    else:
        context.execute_steps(u'''
            given login to eTools
        ''')


def after_feature(context, scenario):
    driver = config.read_config('driver')
    if driver == 'android':
        pass
    else:
        context.execute_steps(u'''
            given logout from eTools
        ''')


def before_all(context):
    setup_debug_on_error(context.config.userdata)

    context.browser = get_driver()
    # context.browser.maximize_window()
    # context.browser.set_window_size(1400, 1200)
    # context.browser.implicitly_wait(30)
    context.util = Utils(context.browser)
    context.base_url = config.read_config('baseurl')
    context.verificationErrors = []
    context.accept_next_alert = True


def after_all(context):
    context.browser.quit()


def after_step(context, step):
    if BEHAVE_DEBUG_ON_ERROR and step.status == "failed":
        context.browser.screenshot_error()
        # -- ENTER DEBUGGER: Zoom in on failure location.
        # NOTE: Use IPython debugger, same for pdb (basic python debugger).
        import ipdb
        ipdb.post_mortem(step.exc_traceback)


def get_driver():
    driver = config.read_config('driver')
    if driver == 'chrome':
        browser = webdriver.Chrome(config.read_config('chromedriver_path'))
        browser.maximize_window()
        browser.implicitly_wait(30)
    elif driver == 'android':
        desired_capabilities = {'aut': config.read_config('android_app_id')}
        return webdriver.Remote(
            desired_capabilities=desired_capabilities
        )
    else:
        browser = webdriver.Firefox()
        browser.maximize_window()
        browser.implicitly_wait(30)
    return browser
