from behave import *


@given('check all pages and take screenshots')
def step_impl(context):
    try:
        driver = context.browser
        util = context.util
        driver.implicitly_wait(20)

        util.screenshot('Dashboard Personal')
        driver.find_element_by_link_text("Previous").click()
        driver.find_element_by_link_text("Supervised").click()
        driver.find_element_by_link_text("Current").click()

        driver.find_element_by_link_text("Indicators").click()
        driver.implicitly_wait(20)
        driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
        driver.find_element_by_xpath("(//button[@type='button'])[2]").click()
        util.screenshot('Dashboard Indicators')

        driver.find_element_by_link_text("Trips").click()
        driver.implicitly_wait(20)
        util.screenshot('Dashboard Trips')

        driver.find_element_by_xpath("//a[contains(@href, '/map/')]").click()
        driver.implicitly_wait(20)
        driver.find_element_by_xpath("//section[@id='main-content']/div/div/div/button[2]").click()
        driver.find_element_by_xpath("//section[@id='main-content']/div/div[2]/div/button[2]").click()
        driver.find_element_by_xpath("(//button[@type='button'])[5]").click()
        driver.find_element_by_xpath("//button[@type='=button']").click()
        driver.find_element_by_css_selector("div.row.col-md-offset-1").click()
        driver.find_element_by_xpath("//section[@id='main-content']/div[2]/div[4]/div/button[2]").click()
        driver.find_element_by_xpath("//section[@id='main-content']/div[2]/div[3]/div/button[2]").click()
        driver.find_element_by_xpath("//section[@id='main-content']/div[2]/div[2]/div/button[2]").click()
        driver.find_element_by_xpath("(//button[@type='=button'])[2]").click()
        driver.find_element_by_id("main-content").click()
        driver.find_element_by_link_text("+").click()
        driver.find_element_by_link_text("+").click()
        driver.implicitly_wait(20)
        util.screenshot('Map')

        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/')]").click()
        driver.implicitly_wait(20)
        util.screenshot('Partnerships - Interventions')

        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/pca/add/')]").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add an Intervention')

        driver.find_element_by_link_text("Add another Budget").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add another Budget')

        driver.find_element_by_link_text("Add another Grant").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add another Grant')

        driver.find_element_by_link_text("Add another Sector").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add another Sector')

        driver.find_element_by_link_text("Results").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Results')

        driver.find_element_by_link_text("Locations").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Locations')

        driver.find_element_by_link_text("Trips").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Trips')

        driver.find_element_by_link_text("Supplies").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Supplies')

        driver.find_element_by_link_text("Add another Supply Plan").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add another Supply Plan')

        driver.find_element_by_link_text("Add another Distribution Plan").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add another Distribution PLan')

        driver.find_element_by_link_text("Attachments").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Attachments')

        driver.find_element_by_link_text("Add another File").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add another File')

        driver.find_element_by_link_text("Add another Generic Link").click()
        driver.implicitly_wait(20)
        util.screenshot('Interventions - Add another Generic Link')

        driver.find_element_by_link_text("Agreements").click()
        driver.implicitly_wait(20)
        util.screenshot('Agreements')

        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/agreement/add/')]").click()
        driver.implicitly_wait(20)
        util.screenshot('Add an Agreement')

        # driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/partnerorganization/')]").click()
        driver.find_element_by_xpath("//a[@href='/admin/partners/partnerorganization/']").click()
        driver.implicitly_wait(20)
        util.screenshot('Partners Organizations')

        driver.find_element_by_xpath("//a[contains(@href, '/admin/partners/partnerorganization/add/')]").click()
        driver.implicitly_wait(20)
        util.screenshot('Add a Partner')

        # driver.find_element_by_link_text("Add another Assessments And Audits Record").click()
        # driver.implicitly_wait(20)
        # util.screenshot('Partners - Add another Assessments And Audits Record')

        # driver.find_element_by_link_text("Add another Partner Staff Member").click()
        # driver.implicitly_wait(20)
        # util.screenshot('Partners - Add another Partner Staff Member')

        driver.find_element_by_link_text("Trips").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips')

        driver.find_element_by_link_text("Add trip").click()
        driver.implicitly_wait(20)
        util.screenshot('Add a Trip')

        driver.find_element_by_link_text("Reporting").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Reporting')

        driver.find_element_by_link_text("Attachments").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Attachments')

        driver.find_element_by_link_text("Checklists").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Checklists')

        driver.find_element_by_link_text("Attachments").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Attachments')

        driver.find_element_by_link_text("Add another File Attachment").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips  - Add another File Attachment')

        driver.find_element_by_link_text("Add another Generic Link").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Add another Generic Link')

        driver.find_element_by_link_text("Reporting").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Reporting')

        driver.find_element_by_link_text("Add another Action Point").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Add another Action Point')

        driver.find_element_by_link_text("Planning").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Planning')

        driver.find_element_by_id("fieldsetcollapser0").click()
        driver.find_element_by_link_text("Add another Travel Itinerary").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Add another Travel Itinerary')

        driver.find_element_by_link_text("Add another Sites To Visit").click()
        driver.implicitly_wait(20)
        util.screenshot('Trips - Add another Sites To Visit')

        driver.find_element_by_link_text("Action points").click()
        driver.implicitly_wait(20)
        util.screenshot('Action points')

        driver.find_element_by_link_text("Add action point").click()
        driver.implicitly_wait(20)
        util.screenshot('Add action point')

        driver.find_element_by_link_text("Funds").click()
        driver.implicitly_wait(20)
        util.screenshot('Funds')

        driver.find_element_by_link_text("Grants").click()
        driver.implicitly_wait(20)
        util.screenshot('Grants')

        driver.find_element_by_link_text("Result Structures").click()
        driver.implicitly_wait(20)
        util.screenshot('Result Structures')

        driver.find_element_by_link_text("Indicators").click()
        driver.implicitly_wait(20)
        util.screenshot('Indicators')

        driver.find_element_by_link_text("CCCs").click()
        driver.implicitly_wait(20)
        util.screenshot('CCCs')

        driver.find_element_by_link_text("Locations").click()
        driver.implicitly_wait(20)
        util.screenshot('Locations')

        driver.find_element_by_xpath("(//a[contains(text(),'Locations')])[3]").click()
        driver.implicitly_wait(20)

        driver.find_element_by_css_selector("#left-nav > ul > li > a").click()
        driver.implicitly_wait(20)

    except Exception as ex:
        util.screenshot_error()
        raise Exception(ex)
