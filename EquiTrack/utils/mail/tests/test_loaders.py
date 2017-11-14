from django.core import mail
from django.test import TestCase

from post_office import mail as post_office_mail
from post_office.models import EmailTemplate


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
        post_office_mail.send(
            'test@test.com',
            'no-reply@test.com',
            template='template1',
            context={},
        )

        self.assertEqual(len(mail.outbox), 1)
        content = mail.outbox[0].alternatives[0]
        self.assertEqual(content[1], 'text/html')
        self.assertIn('Base template', content[0])
        self.assertIn('Template1', content[0])
