from datetime import datetime
from behave import *
from selenium.webdriver.support.select import Select


@given('go to "Partners" from the partnership section')
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


@then('enter partner\'s "Full name" and "Short name"')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_id("id_name").clear()
        driver.find_element_by_id("id_name").send_keys("Test Vision")
        driver.find_element_by_id("id_short_name").clear()
        driver.find_element_by_id("id_short_name").send_keys("TTV")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select an exiting "Partner type" from the drop-down list')
def step_impl(context):
    try:
        driver = context.browser
        Select(driver.find_element_by_id("id_partner_type")).select_by_visible_text("Civil Society Organisation")
        Select(driver.find_element_by_id("id_type")).select_by_visible_text("National NGO")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the partner\'s Alternate name')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_id("fieldsetcollapser0").click()
        driver.find_element_by_id("id_alternate_name").clear()
        driver.find_element_by_id("id_alternate_name").send_keys("testvision")
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


@then('delete a partner organization')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_link_text("TestVision").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('go to "Agreements" from the partnership section')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/')]").click()
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


@then('select a partner from the drop-down list')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("TestVision")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select an "Agreement type"')
def step_impl(context):
    try:
        driver = context.browser
        Select(driver.find_element_by_id("id_agreement_type")).select_by_visible_text("Work Plan")
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter the "Reference Number"')
def step_impl(context):
    try:
        driver = context.browser
        driver.find_element_by_id("id_agreement_number").clear()
        driver.find_element_by_id("id_agreement_number").send_keys("TTV00012345")
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


@then('delete the new agreement')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_link_text("TTV00012345").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete an intervention')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_link_text("TTV12345").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('go to "Interventions" from the partnership section')
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


@then('select an existing partner from the drop-down partner')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_id("id_partner"))
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("AAA Demo Partner")

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select an existing agreement for that partner and enter a reference number for this agreement')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_id("id_agreement"))
        Select(driver.find_element_by_id("id_agreement")).select_by_visible_text("PCA for AAA Demo Partner (16-12-2015 - 16-12-2015)")

        context.util.highlight(driver.find_element_by_id("id_number"))
        driver.find_element_by_id("id_number").clear()
        driver.find_element_by_id("id_number").send_keys("AAA 00002")

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select the appropriate Document Type for this intervention')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_id("id_partnership_type"))
        Select(driver.find_element_by_id("id_partnership_type")).select_by_visible_text("Programme Document")

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('add a Title for this intervention')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        date = datetime.now().strftime('%Y-%m-%d')

        context.util.highlight(driver.find_element_by_id("id_title"))
        driver.find_element_by_id("id_title").send_keys("Distribution of hygiene kits in Kabul")

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


@then('continue adding supplies and quantities. Click "Save and continue editing" to save the supply plan')
def set_impl(context):
    try:

        driver = context.browser
        driver.implicitly_wait(10)

        Select(driver.find_element_by_id("id_supply_plans-0-item")).select_by_visible_text("Family hygiene kit")
        driver.find_element_by_id("id_supply_plans-0-quantity").clear()
        driver.find_element_by_id("id_supply_plans-0-quantity").send_keys("6000")
        driver.find_element_by_link_text("Add another Supply Plan").click()
        Select(driver.find_element_by_id("id_supply_plans-1-item")).select_by_visible_text("Family hygiene kit")
        Select(driver.find_element_by_id("id_supply_plans-1-item")).select_by_visible_text("Water purification tablet")
        driver.find_element_by_id("id_supply_plans-1-quantity").clear()
        driver.find_element_by_id("id_supply_plans-1-quantity").send_keys("3000")
        driver.find_element_by_link_text("Add another Supply Plan").click()
        Select(driver.find_element_by_id("id_supply_plans-2-item")).select_by_visible_text("Tarpaulin")
        driver.find_element_by_id("id_supply_plans-2-quantity").clear()
        driver.find_element_by_id("id_supply_plans-2-quantity").send_keys("10000")

        driver.find_element_by_name("_continue").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('add an item from the supply plan to the distribution plan')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_link_text("Supplies").click()
        Select(driver.find_element_by_id("id_distribution_plans-0-item")).select_by_visible_text("Water purification tablet")

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('select a location where the item will be distributed from the pre-defined list of districts for your country')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        Select(driver.find_element_by_id("id_distribution_plans-0-location")).select_by_visible_text("ACHHAM")

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('enter in the quantities for this distribution location. Select "Send to partner" to send the distribution to the UniSuppy app')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        driver.find_element_by_id("id_distribution_plans-0-quantity").clear()
        driver.find_element_by_id("id_distribution_plans-0-quantity").send_keys("2000")
        driver.find_element_by_id("id_distribution_plans-0-send").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('continue adding items, locations, and quantities from your supply plan to the distribution plan')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        Select(driver.find_element_by_id("id_distribution_plans-1-item")).select_by_visible_text("Water purification tablet")
        Select(driver.find_element_by_id("id_distribution_plans-1-location")).select_by_visible_text("SAPTARI")
        driver.find_element_by_id("id_distribution_plans-1-quantity").clear()
        driver.find_element_by_id("id_distribution_plans-1-quantity").send_keys("1000")
        driver.find_element_by_id("id_distribution_plans-1-send").click()

        driver.find_element_by_name("_continue").click()

        Select(driver.find_element_by_id("id_distribution_plans-2-item")).select_by_visible_text("Water purification tablet")
        Select(driver.find_element_by_id("id_distribution_plans-2-location")).select_by_visible_text("BHAKTAPUR")
        driver.find_element_by_id("id_distribution_plans-2-quantity").clear()
        driver.find_element_by_id("id_distribution_plans-2-quantity").send_keys("500")
        driver.find_element_by_id("id_distribution_plans-2-send").click()

        driver.find_element_by_name("_continue").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('you cannot exceed the quantity outlined in the supply plan')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)

        context.util.highlight(driver.find_element_by_id("id_distribution_plans-2-quantity"))

        Select(driver.find_element_by_id("id_distribution_plans-2-item")).select_by_visible_text("Family hygiene kit")
        Select(driver.find_element_by_id("id_distribution_plans-2-location")).select_by_visible_text("BHOJPUR")
        driver.find_element_by_id("id_distribution_plans-2-quantity").clear()
        driver.find_element_by_id("id_distribution_plans-2-quantity").send_keys("3000")
        driver.find_element_by_id("id_distribution_plans-2-send").click()

        Select(driver.find_element_by_id("id_distribution_plans-3-item")).select_by_visible_text("Family hygiene kit")
        Select(driver.find_element_by_id("id_distribution_plans-3-location")).select_by_visible_text("SALYAN")
        driver.find_element_by_id("id_distribution_plans-3-quantity").clear()
        driver.find_element_by_id("id_distribution_plans-3-quantity").send_keys("1000")
        driver.find_element_by_id("id_distribution_plans-3-send").click()

        Select(driver.find_element_by_id("id_distribution_plans-4-item")).select_by_visible_text("Tarpaulin")
        Select(driver.find_element_by_id("id_distribution_plans-4-location")).select_by_visible_text("KATHMANDU")
        driver.find_element_by_id("id_distribution_plans-4-quantity").clear()
        driver.find_element_by_id("id_distribution_plans-4-quantity").send_keys("8000")
        driver.find_element_by_id("id_distribution_plans-4-send").click()

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
