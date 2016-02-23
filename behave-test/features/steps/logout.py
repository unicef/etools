from behave import *


@given('logout from eTools')
def step_impl(context):
    try:
        #context.browser.get(context.base_url)
        context.browser.get(context.base_url + "saml2/logout/")

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)
