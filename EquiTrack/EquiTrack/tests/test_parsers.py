from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from unittest import TestCase

from EquiTrack import parsers


class TestIntOrString(TestCase):
    def test_int(self):
        self.assertEqual(parsers.int_or_str(1), 1)

    def test_str_to_int(self):
        self.assertEqual(parsers.int_or_str("1"), 1)

    def test_str(self):
        self.assertEqual(parsers.int_or_str("one"), "one")


class TestListOrDict(TestCase):
    def test_list(self):
        self.assertEqual(parsers.list_or_dict(1), '[]')

    def test_dict(self):
        self.assertEqual(parsers.list_or_dict("1"), '{}')


class TestCreateListsFromKeys(TestCase):
    def test_empty_dict(self):
        self.assertEqual(parsers.create_lists_from_keys({}), [])

    def test_keys(self):
        data = {
            "1": "Int",
            "str": "Str",
            "[1]": "List Int",
            "[str]": "List Str",
            "[1 str]": "List Int Str"
        }
        self.assertEqual(
            parsers.create_lists_from_keys(data),
            [[1], ["", 1, "str"], ["", 1], ["", "str"], ["str"]]
        )


class TestFormPathFromList(TestCase):
    def test_empty(self):
        res = parsers.form_path_from_list([])
        self.assertEqual(res, '')

    def test_not_list(self):
        """If list parameter is False then don't append
        if integer last value in list"""
        data = ["str", 1]
        res = parsers.form_path_from_list(data)
        self.assertEqual(res, '["str"][1]')

    def test_list_no_append(self):
        """If list item is an integer but not the last value in the list
        then NO append
        """
        data = [1, "str"]
        res = parsers.form_path_from_list(data, list=True)
        self.assertEqual(res, '[1]["str"]')

    def test_list_append(self):
        """If list item is an integer and the last value in the list
        then append
        """
        data = ["str", 1]
        res = parsers.form_path_from_list(data, list=True)
        self.assertEqual(res, '["str"].append({})')


class TestSetCurrentPathInDict(TestCase):
    def test_str(self):
        """If last value is NOT an integer, and set that key to the
        next_value parameter provided
        """
        data = {
            "one": {"two": 2}
        }
        path = ["one", "two"]
        res = parsers.set_current_path_in_dict(data, path, '"change"')
        self.assertEqual(res, {"one": {"two": "change"}})

    def test_int(self):
        """If last value in path list is an integer, then append an empty dict
        to the value in the data dict
        """
        data = {
            "one": [1]
        }
        path = ["one", 1]
        res = parsers.set_current_path_in_dict(data, path, '"change"')
        self.assertEqual(res, {"one": [1, {}]})


class TestPathInDictExists(TestCase):
    def test_false(self):
        res = parsers.path_in_dict_exists({1: "one"}, '[2]')
        self.assertFalse(res)

    def test_true(self):
        res = parsers.path_in_dict_exists({1: "one"}, '[1]')
        self.assertTrue(res)


class TestFormDataPath(TestCase):
    def test_empty(self):
        """If empty path list provided, then return an empty string"""
        self.assertEqual(parsers.form_data_path([]), "")

    def test_single_element(self):
        """If only one element in list then return str of that element"""
        self.assertEqual(parsers.form_data_path([1]), "1")

    def test_multi_element(self):
        """If multiple elements in list then return dict str of path"""
        res = parsers.form_data_path(["d", "k", "2"])
        self.assertEqual(res, "d[k][2]")


class TestSetInPath(TestCase):
    def test_not_in_path(self):
        data = {"one": "old"}
        res = parsers.set_in_path(data, ["two"], "change")
        self.assertEqual(res, data)

    def test_in_path(self):
        data = {"one": "old"}
        res = parsers.set_in_path(data, ["one", "_obj"], "change")
        self.assertEqual(res, {"one": "old"})


class TestParseMultipartData(TestCase):
    def test_empty(self):
        self.assertEqual(parsers.parse_multipart_data({}), {})

    def test_single_dict(self):
        data = {"one": "two"}
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {"one": "two"})

    def test_multi_str_list_key(self):
        data = {
            "[d _obj key-2]": "val-2",
            "[d][_obj][key-2]": "val-2",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res[""], {
            "d": {"key-2": "val-2"},
        })

    def test_multi_int_list_key(self):
        data = {
            "[d 0]": "val-2",
            "[d][0]": "val-2",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res[""], {
            "d": ["val-2", "val-2"],
        })
