from behave import *
from selenium.webdriver.support.select import Select


@given('add a trip')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_xpath("//div[@id='leftside-navigation']/ul/li[5]/a/span").click()
        driver.find_element_by_xpath("//a[contains(@href, '/admin/trips/trip/add/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('fill trip info')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        Select(driver.find_element_by_id("id_supervisor")).select_by_visible_text("Tarek Moubarak")
        Select(driver.find_element_by_id("id_section")).select_by_visible_text("SPPME")
        Select(driver.find_element_by_id("id_office")).select_by_visible_text("Beirut")
        driver.find_element_by_id("id_purpose_of_travel").clear()
        driver.find_element_by_id("id_purpose_of_travel").send_keys("Testing behave selenium")
        driver.find_element_by_css_selector("img[alt=\"Calendar\"]").click()
        driver.find_element_by_link_text("20").click()
        driver.find_element_by_css_selector("#calendarlink1 > img[alt=\"Calendar\"]").click()
        driver.find_element_by_xpath("(//a[contains(text(),'20')])[2]").click()
        Select(driver.find_element_by_id("id_travel_type")).select_by_visible_text("TECHNICAL SUPPORT")
        Select(driver.find_element_by_id("id_travel_assistant")).select_by_visible_text("Tarek Moubarak")

        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-origin']").send_keys("Beirut")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-destination']").send_keys("Saida")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-depart']").send_keys("20/01/2016 08:10")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-arrive']").send_keys("20/01/2016 08:40")

        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-origin']").send_keys("Beirut")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-destination']").send_keys("Saida")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-depart']").send_keys("20/01/2016 14:10")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-arrive']").send_keys("20/01/2016 14:40")
        driver.find_element_by_name("_continue").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the new trip')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.get(context.browser.current_url)
        # driver.find_element_by_link_text("Delete").click()
        # driver.find_element_by_css_selector("input.btn.btn-danger").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('add an action point')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.get(context.base_url + "/admin/trips/trip/add/#checklists")
        driver.find_element_by_link_text("Action points").click()
        driver.find_element_by_link_text("Add action point").click()
        driver.find_element_by_id("id_actions_taken").clear()
        driver.find_element_by_id("id_actions_taken").send_keys("Taken")
        driver.find_element_by_id("id_actions_taken").clear()
        driver.find_element_by_id("id_actions_taken").send_keys("task action list")
        driver.find_element_by_link_text("Today").click()
        driver.find_element_by_name("_continue").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the new action point')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.get(context.browser.current_url)
        # driver.find_element_by_link_text("Delete").click()
        # driver.find_element_by_css_selector("input.btn.btn-danger").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)