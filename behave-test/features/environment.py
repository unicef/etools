from utils import *
from selenium import webdriver


BEHAVE_DEBUG_ON_ERROR = False


def setup_debug_on_error(userdata):
    global BEHAVE_DEBUG_ON_ERROR
    BEHAVE_DEBUG_ON_ERROR = userdata.getbool("BEHAVE_DEBUG_ON_ERROR")


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
    setup_debug_on_error(context.config.userdata)
    # context.execute_steps(u'''
    #     Given login to eTools
    # ''')
    context.browser = webdriver.Firefox()
    context.browser.maximize_window()
    # context.browser.set_window_size(1400, 1200)
    context.util = Utils(context.browser)
    context.browser.implicitly_wait(30)
    context.base_url = context.util.read_config('baseurl')
    context.verificationErrors = []
    context.accept_next_alert = True


def after_all(context):
    # context.execute_steps(u'''
    #     given logout from eTools
    # ''')
    context.browser.quit()


def after_step(context, step):
    if BEHAVE_DEBUG_ON_ERROR and step.status == "failed":
        context.browser.screenshot_error()
        # -- ENTER DEBUGGER: Zoom in on failure location.
        # NOTE: Use IPython debugger, same for pdb (basic python debugger).
        import ipdb
        ipdb.post_mortem(step.exc_traceback)
