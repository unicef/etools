from behave import *


#@given('login to eTools "{username}" and "{password}"')
#def step_impl(context, username, password):
@given('login to eTools')
def step_impl(context):
    try:
        driver = context.browser
        util = context.util
        username = util.readConfig('username')
        password = util.readConfig('password')
        driver.get(context.base_url + "login/")
        driver.implicitly_wait(15)
        driver.get(context.base_url + "saml2/login/")
        ##driver.find_element_by_xpath("//section[@id='container']/div/paper-card[2]/div[2]/a/paper-button").click()
        driver.implicitly_wait(10)
        driver.find_element_by_id("userNameInput").send_keys(username)
        driver.find_element_by_id("passwordInput").send_keys(password)
        driver.find_element_by_id("submitButton").click()

    except Exception as ex:
        #context.util.screenshoterror()
        driver.get(context.base_url)
        #raise Exception(ex)
