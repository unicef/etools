from behave import *


#@given('login to eTools "{username}" and "{password}"')
#def step_impl(context, username, password):
@given('login to eTools')
def step_impl(context):
    try:
        driver = context.browser
        util = context.util
        username = util.read_config('username')
        password = util.read_config('password')
        driver.get(context.base_url + "login/")
        driver.implicitly_wait(15)
        driver.find_element_by_xpath("//a[contains(@href, 'saml2/login/')]").click()
        driver.implicitly_wait(10)
        driver.find_element_by_id("userNameInput").send_keys(username)
        driver.find_element_by_id("passwordInput").send_keys(password)
        driver.find_element_by_id("submitButton").click()

    except Exception as ex:
        #context.util.screenshot_error()
        driver.get(context.base_url)
        #raise Exception(ex)
