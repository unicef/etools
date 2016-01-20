from behave import *


@given('logout from eTools')
def step_impl(context):
    try:
        #context.browser.get(context.base_url)
        context.browser.find_element_by_link_text("Log out").click()

    except Exception as ex:
        context.util.screenshoterror()
        raise Exception(ex)
