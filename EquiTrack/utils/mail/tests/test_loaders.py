from __future__ import absolute_import, division, print_function, unicode_literals

from django.core import mail
from django.test import TestCase

from post_office.models import EmailTemplate

from notification.utils import send_notification_using_email_template


class EmailTemplateLoaderTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        EmailTemplate.objects.create(name='test_base', html_content='''
            <html>
                <head></head>
                <body>
                    <h1>Base template</h1>
                    {% block content %}{% endblock %}
                </body>
            </html>
        ''')
        EmailTemplate.objects.create(name='template1', html_content='''
            {% extends "email-templates/test_base" %}

            {% block content %}
                <p>Template1</p>
            {% endblock %}
        ''')

    def setUp(self):
        mail.outbox = []

    def test_extends(self):
        send_notification_using_email_template(
            recipients=['test@test.com'],
            from_address='no-reply@test.com',
            email_template_name='template1',
            context={},
        )

        self.assertEqual(len(mail.outbox), 1)
        content = mail.outbox[0].alternatives[0]
        self.assertEqual(content[1], 'text/html')
        self.assertIn('Base template', content[0])
        self.assertIn('Template1', content[0])
