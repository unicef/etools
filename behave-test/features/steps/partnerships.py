from datetime import datetime
from behave import *
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0


@given('we test partnerships features')
def step_impl(context):
    try :
        pass
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('go to "Partners" from the partnership section')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/')]").click()
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/partnerorganization/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('click "Add partner organization"')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/partnerorganization/add/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter partner\'s Full name "{fullname}" and Short name "{shortname}"')
def step_impl(context, fullname, shortname):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_id("id_name").clear()
        driver.find_element_by_id("id_name").send_keys(fullname)
        driver.find_element_by_id("id_short_name").clear()
        driver.find_element_by_id("id_short_name").send_keys(shortname)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select an exiting Partner type "{partnertype}" and CSO type "{csotype}" from the drop-down list')
def step_impl(context, partnertype, csotype):
    try:
        driver = context.browser
        Select(driver.find_element_by_id("id_partner_type")).select_by_visible_text(partnertype)
        Select(driver.find_element_by_id("id_type")).select_by_visible_text(csotype)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the partners main address "{address}", main phone number "{phone}" and main email "{email}"')
def step_impl(context, address, phone, email):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_id("id_address").clear()
        driver.find_element_by_id("id_address").send_keys(address)
        driver.find_element_by_id("id_phone_number").clear()
        driver.find_element_by_id("id_phone_number").send_keys(phone)
        driver.find_element_by_id("id_email").clear()
        driver.find_element_by_id("id_email").send_keys(email)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the partner\'s Alternate name "{alternatename}"')
def step_impl(context, alternatename):
    try:
        driver = context.browser
        driver.find_element_by_id("fieldsetcollapser0").click()
        driver.find_element_by_id("id_alternate_name").clear()
        driver.find_element_by_id("id_alternate_name").send_keys(alternatename)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('press "Save" to add this new partner')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_name("_save").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('go to "Agreements" from the partnership section')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/agreement/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('click "Add agreement"')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/agreement/add/')]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select a partner "{partner}" from the drop-down list')
def step_impl(context, partner):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text(partner)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select an Agreement type "{type}"')
def step_impl(context, type):
    try:
        driver = context.browser
        Select(driver.find_element_by_id("id_agreement_type")).select_by_visible_text(type)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the Reference Number "{reference}"')
def step_impl(context, reference):
    try:
        driver = context.browser
        driver.find_element_by_id("id_agreement_number").clear()
        driver.find_element_by_id("id_agreement_number").send_keys(reference)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the Start and End date of this agreement')
def step_impl(context):
    try:
        driver = context.browser
        date = datetime.now().strftime('%Y-%m-%d')
        driver.find_element_by_id("id_start").send_keys(date)
        driver.find_element_by_id("id_end").send_keys(date)
        # driver.find_element_by_id("id_signed_by_partner_date").send_keys(date)
        # driver.find_element_by_id("id_signed_by_unicef_date").send_keys(date)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('add un-existing partner manager')
def step_impl(context):
    try:
        driver = context.browser
        currentPage = driver.current_window_handle
        driver.find_element_by_id("add_id_partner_manager").click()

        windows = driver.window_handles
        for window in windows:
            if currentPage != window:
                driver.switch_to_window(window)

        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("TestVision")
        driver.find_element_by_id("id_title").clear()
        driver.find_element_by_id("id_title").send_keys("Officer")
        driver.find_element_by_id("id_first_name").clear()
        driver.find_element_by_id("id_first_name").send_keys("First")
        driver.find_element_by_id("id_last_name").clear()
        driver.find_element_by_id("id_last_name").send_keys("Name")
        driver.find_element_by_id("id_email").clear()
        driver.find_element_by_id("id_email").send_keys("ttvmember3@test.test")
        driver.find_element_by_name("_save").click()

        driver.switch_to_window(currentPage)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('press "Save" to save the new agreement')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_name("_save").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('go to "Interventions" from the partnership section')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        element = driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/')]")
        context.util.highlight(element)
        element.click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('click "add intervention"')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        element = driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/add/')]")
        context.util.highlight(element)
        element.click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select an existing partner "{partner}" from the drop-down partner')
def set_impl(context, partner):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_id("id_partner"))
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text(partner)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select an existing agreement "{agreement}" for that partner and enter a reference number for this agreement "{reference}"')
def set_impl(context, agreement, reference):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_id("id_agreement"))
        # Select(driver.find_element_by_id("id_agreement")).select_by_visible_text(agreement)

        context.util.highlight(driver.find_element_by_id("id_number"))
        driver.find_element_by_id("id_number").clear()
        driver.find_element_by_id("id_number").send_keys(reference)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select the appropriate Document Type "{type}" for this intervention')
def set_impl(context, type):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_id("id_partnership_type"))
        Select(driver.find_element_by_id("id_partnership_type")).select_by_visible_text(type)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('add a Title for this intervention "{title}"')
def set_impl(context, title):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        date = datetime.now().strftime('%Y-%m-%d')

        context.util.highlight(driver.find_element_by_id("id_title"))
        driver.find_element_by_id("id_title").send_keys(title)

        context.util.highlight(driver.find_element_by_id("id_initiation_date"))
        driver.find_element_by_id("id_initiation_date").send_keys(date)
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('go to the "Supplies" tab in the intervention to insert supplies')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_link_text("Supplies").click()
        context.util.highlight(driver.find_element_by_link_text("Supplies"))

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select a supply from the drop-down list')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        # context.util.highlight(driver.find_element_by_id("add_id_supply_plans-0-item"))
        context.util.highlight(driver.find_element_by_id("id_supply_plans-0-item"))

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('continue adding supplies and quantities')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        for i, row in enumerate(context.table):
            Select(driver.find_element_by_id("id_supply_plans-"+str(i)+"-item")).select_by_visible_text(row['item'])
            driver.find_element_by_id("id_supply_plans-"+str(i)+"-quantity").clear()
            driver.find_element_by_id("id_supply_plans-"+str(i)+"-quantity").send_keys(row['quantity'])
            driver.find_element_by_link_text("Add another Supply Plan").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('press "Save and continue editing" to save the supply plan')
def set_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_name("_continue").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('add an item from the supply plan to the distribution plan "{item}"')
def set_impl(context, item):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_link_text("Supplies").click()
        Select(driver.find_element_by_id("id_distribution_plans-0-item")).select_by_visible_text(item)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select a location where the item will be distributed from the pre-defined list of districts for your country "{location}"')
def set_impl(context, location):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        Select(driver.find_element_by_id("id_distribution_plans-0-location")).select_by_visible_text(location)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter in the quantities "{quantity}" for this distribution location')
def set_impl(context, quantity):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_id("id_distribution_plans-0-quantity").clear()
        driver.find_element_by_id("id_distribution_plans-0-quantity").send_keys(quantity)
        context.util.highlight(driver.find_element_by_id("id_distribution_plans-0-quantity"))

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select "Send to partner" to send the distribution to the UniSuppy app')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_id("id_distribution_plans-0-send").click()
        context.util.highlight(driver.find_element_by_id("id_distribution_plans-0-send"))
        driver.find_element_by_id("id_distribution_plans-0-send").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('continue adding items, locations, and quantities from your supply plan to the distribution plan')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        for i, row in enumerate(context.table):
            Select(driver.find_element_by_id("id_distribution_plans-"+str(i)+"-item")).select_by_visible_text(row['item'])
            Select(driver.find_element_by_id("id_distribution_plans-"+str(i)+"-location")).select_by_visible_text(row['location'])
            driver.find_element_by_id("id_distribution_plans-"+str(i)+"-quantity").clear()
            driver.find_element_by_id("id_distribution_plans-"+str(i)+"-quantity").send_keys(row['quantity'])
            driver.find_element_by_id("id_distribution_plans-"+str(i)+"-send").click()
            driver.find_element_by_link_text("Add another Distribution Plan").click()

        driver.find_element_by_name("_continue").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('you cannot exceed the quantity outlined in the supply plan')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        for i, row in enumerate(context.table):
            Select(driver.find_element_by_id("id_distribution_plans-"+str(i+3)+"-item")).select_by_visible_text(row['item'])
            Select(driver.find_element_by_id("id_distribution_plans-"+str(i+3)+"-location")).select_by_visible_text(row['location'])
            driver.find_element_by_id("id_distribution_plans-"+str(i+3)+"-quantity").clear()
            driver.find_element_by_id("id_distribution_plans-"+str(i+3)+"-quantity").send_keys(row['quantity'])
            driver.find_element_by_id("id_distribution_plans-"+str(i+3)+"-send").click()

        driver.find_element_by_name("_continue").click()

        # WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "(//a[contains(text(),'Remove')])[5]")))
        # context.util.highlight(driver.find_element_by_id("id_distribution_plans-5-quantity"))
        # driver.find_element_by_xpath("(//a[contains(text(),'Remove')])[5]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('press "Save and continue editing" to save the plans and sync with the app')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_name("_continue").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@when('the partners begin to distribute supplies via UniSupply')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('you will be able to the status of the deliveries in this section')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_xpath('//*[@id="distribution_plans-2"]/td[5]/p'))

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the partner organization number "{number}"')
def set_impl(context, number):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_xpath("//a[contains(@href, '?all=')]").click()
        driver.find_element_by_link_text(number).click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the agreement number "{number}"')
def set_impl(context, number):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_xpath("//a[contains(@href, '?all=')]").click()
        driver.find_element_by_link_text(number).click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the intervention number "{number}"')
def set_impl(context, number):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_id("searchbar").clear()
        driver.find_element_by_id("searchbar").send_keys(number)
        driver.find_element_by_xpath("//input[@value='Search']").click()
        driver.find_element_by_link_text(number).click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)