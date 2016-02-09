from behave import *
from datetime import datetime
from selenium.webdriver.support.select import Select


@given('go to "Trips" from the trips section')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_xpath("//a[contains(@href, '/admin/trips/trip/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('click "Add trip"')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_xpath("//a[contains(@href, '/admin/trips/trip/add/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('you will find your name selected by default as a traveller')
def step_impl(context):
    try:
        driver = context.browser

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select your supervisor from the drop-down list')
def step_impl(context):
    try:
        driver = context.browser
        Select(driver.find_element_by_id("id_supervisor")).select_by_visible_text("Tarek Moubarak")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select your section and office location')
def step_impl(context):
    try:
        driver = context.browser
        Select(driver.find_element_by_id("id_section")).select_by_visible_text("SPPME")
        Select(driver.find_element_by_id("id_office")).select_by_visible_text("Beirut")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)\


@then('add a Purpose of travel')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_id("id_purpose_of_travel").clear()
        driver.find_element_by_id("id_purpose_of_travel").send_keys("Testing behave selenium")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the From date and To date of trip')
def step_impl(context):
    try:
        driver = context.browser
        date = datetime.now().strftime('%Y-%m-%d')
        driver.find_element_by_id("id_from_date").send_keys(date)
        driver.find_element_by_id("id_to_date").send_keys(date)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select the Travel type and Travel focal point')
def step_impl(context):
    try:
        driver = context.browser
        Select(driver.find_element_by_id("id_travel_type")).select_by_visible_text("TECHNICAL SUPPORT")
        Select(driver.find_element_by_id("id_travel_assistant")).select_by_visible_text("Tarek Moubarak")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the Travel Itinerary')
def step_impl(context):
    try:
        driver = context.browser
        date = datetime.now().strftime('%d/%m/%Y')

        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-origin']").send_keys("Beirut")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-destination']").send_keys("Saida")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-depart']").send_keys(date+" 08:10")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-0-arrive']").send_keys(date+" 08:40")

        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-origin']").send_keys("Beirut")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-destination']").send_keys("Saida")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-depart']").send_keys(date+" 14:10")
        driver.find_element_by_xpath("//input[@id='id_travelroutes_set-1-arrive']").send_keys(date+" 14:40")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('press "Save"')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_name("_save")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('press "Save and continue editing"')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_name("_continue")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the new trip')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.get(context.browser.current_url)
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('go to "Action points" from trips section')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_xpath("//a[contains(@href, '/admin/trips/trip/')]").click()
        driver.implicitly_wait(10)
        driver.find_element_by_xpath("//a[contains(@href, '/admin/trips/actionpoint/')]").click()
        driver.implicitly_wait(10)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('click "Add action point"')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_xpath("//a[contains(@href, '/admin/trips/actionpoint/add/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter action point information')
def step_impl(context):
    try:
        driver = context.browser
        date = datetime.now().strftime('%Y-%m-%d')

        driver.implicitly_wait(10)
        driver.find_element_by_id("id_actions_taken").clear()
        driver.find_element_by_id("id_actions_taken").send_keys("Taken")
        driver.find_element_by_id("id_actions_taken").clear()
        driver.find_element_by_id("id_actions_taken").send_keys("task action list")
        driver.find_element_by_id("id_completed_date").send_keys(date)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('press "Save" to save the new action point')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_name("_save").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the new action point')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.get(context.browser.current_url)
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)
