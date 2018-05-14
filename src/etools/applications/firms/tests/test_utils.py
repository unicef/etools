
from django.test import SimpleTestCase
from django.utils import six

from etools.applications.firms.utils import generate_username


class UsernameGeneratorTestCase(SimpleTestCase):
    iterations = 10 ** 5

    def test_length(self):
        for _ in six.moves.range(self.iterations):
            username = generate_username()
            self.assertLessEqual(len(username), 30, "`%s` longer then %s" % (username, 30))

    def test_collision(self):
        usernames = set()
        for _ in six.moves.range(self.iterations):
            username = generate_username()

            self.assertNotIn(username, usernames)

            usernames.add(username)
