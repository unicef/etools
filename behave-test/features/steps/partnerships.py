from behave import *
from selenium.webdriver.support.select import Select


@given('add a partner organization')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_xpath("//div[@id='leftside-navigation']/ul/li[4]/a/span").click()
        driver.find_element_by_css_selector("li.active > ul > li > a").click()
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/partnerorganization/add/')]").click()
        driver.find_element_by_id("id_name").clear()
        driver.find_element_by_id("id_name").send_keys("TestVision")
        driver.find_element_by_id("id_short_name").clear()
        driver.find_element_by_id("id_short_name").send_keys("TTV")
        Select(driver.find_element_by_id("id_partner_type")).select_by_visible_text("Civil Society Organisation")
        Select(driver.find_element_by_id("id_type")).select_by_visible_text("National NGO")
        driver.find_element_by_id("id_address").clear()
        driver.find_element_by_id("id_address").send_keys("Hamra - Concorde")
        driver.find_element_by_id("id_phone_number").clear()
        driver.find_element_by_id("id_phone_number").send_keys("76 123 234")
        driver.find_element_by_id("id_partnerstaffmember_set-0-title").clear()
        driver.find_element_by_id("id_partnerstaffmember_set-0-title").send_keys("member")
        driver.find_element_by_id("id_partnerstaffmember_set-0-first_name").clear()
        driver.find_element_by_id("id_partnerstaffmember_set-0-first_name").send_keys("name")
        driver.find_element_by_id("id_partnerstaffmember_set-0-last_name").clear()
        driver.find_element_by_id("id_partnerstaffmember_set-0-last_name").send_keys("name2")
        driver.find_element_by_id("id_partnerstaffmember_set-0-email").clear()
        driver.find_element_by_id("id_partnerstaffmember_set-0-email").send_keys("ttvmember@test.test")
        driver.find_element_by_name("_save").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the new partner organization')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_link_text("TestVision").click()
        # driver.find_element_by_link_text("Delete").click()
        # driver.find_element_by_css_selector("input.btn.btn-danger").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('add an agreement')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/')]").click()
        driver.find_element_by_link_text("Agreements").click()
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/agreement/add/')]").click()
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("TestVision")
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("Test Partner One")
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("Albir Society")
        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("TestVision")
        Select(driver.find_element_by_id("id_agreement_type")).select_by_visible_text("Work Plan")
        driver.find_element_by_id("id_agreement_number").clear()
        driver.find_element_by_id("id_agreement_number").send_keys("TTV00012345")
        driver.find_element_by_link_text("Today").click()
        driver.find_element_by_id("calendarlink1").click()
        driver.find_element_by_css_selector("#calendarbox1 > div > a.calendarnav-next").click()
        driver.find_element_by_css_selector("#calendarbox1 > div > a.calendarnav-next").click()
        driver.find_element_by_css_selector("#calendarbox1 > div > a.calendarnav-next").click()
        driver.find_element_by_css_selector("#calendarbox1 > div > a.calendarnav-next").click()
        driver.find_element_by_css_selector("#calendarbox1 > div > a.calendarnav-next").click()
        driver.find_element_by_css_selector("#calendarbox1 > div > a.calendarnav-next").click()
        driver.find_element_by_xpath("(//a[contains(text(),'29')])[2]").click()
        driver.find_element_by_css_selector("div.controls > span.datetimeshortcuts > a").click()
        Select(driver.find_element_by_id("id_partner_manager")).select_by_visible_text("name name2 (TestVision)")

        currentPage = driver.current_window_handle
        driver.find_element_by_id("add_id_authorized_officers-0-officer").click()

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
        # driver.find_element_by_link_text("Delete").click()
        # driver.find_element_by_css_selector("input.btn.btn-danger").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@given('add an intervention')
def step_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/')]").click()
        driver.find_element_by_link_text("Interventions").click()
        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/add/')]").click()

        Select(driver.find_element_by_id("id_partner")).select_by_visible_text("TestVision")
        Select(driver.find_element_by_id("id_agreement")).select_by_visible_text("---------")
        Select(driver.find_element_by_id("id_agreement")).select_by_visible_text("AWP for TestVision (20-01-2016 - 29-07-2016)")
        Select(driver.find_element_by_id("id_partnership_type")).select_by_visible_text("Cash Transfers to Government")
        driver.find_element_by_id("id_number").clear()
        driver.find_element_by_id("id_number").send_keys("TTV12345")
        driver.find_element_by_id("id_title").clear()
        driver.find_element_by_id("id_title").send_keys("Test")
        driver.find_element_by_link_text("Today").click()
        driver.find_element_by_name("_save").click()

    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)


@then('delete the new intervention')
def set_impl(context):
    try:
        driver = context.browser
        driver.implicitly_wait(10)
        driver.find_element_by_link_text("TTV12345").click()
        # driver.find_element_by_link_text("Delete").click()
        # driver.find_element_by_css_selector("input.btn.btn-danger").click()
        driver.find_element_by_xpath("//a[contains(@href, 'delete/')]").click()
        driver.find_element_by_xpath("//input[@value=\"Yes, I'm sure\"]").click()
    except Exception as ex:
        context.util.screenshot_error()
        raise Exception(ex)