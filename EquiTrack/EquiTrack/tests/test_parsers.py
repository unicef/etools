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


class TestCreateKey(TestCase):
    def test_empty(self):
        """If empty path list provided, then return an empty string"""
        self.assertEqual(parsers.create_key([]), "")

    def test_single_element(self):
        """If only one element in list then return str of that element"""
        self.assertEqual(parsers.create_key([1]), "1")

    def test_multi_element(self):
        """If multiple elements in list then return dict str of path"""
        res = parsers.create_key(["d", "k", "2"])
        self.assertEqual(res, "d[k][2]")


class TestBuildDict(TestCase):
    def test_dict(self):
        keys = ["one", "two"]
        res = parsers.build_dict({}, keys, "end")
        self.assertEqual(res, {"one": {"two": "end"}})

    def test_list(self):
        keys = ["one", 1]
        res = parsers.build_dict({}, keys, "end")
        self.assertEqual(res, {"one": ["end"]})


class TestParseMultipartData(TestCase):
    def test_empty(self):
        self.assertEqual(parsers.parse_multipart_data({}), {})

    def test_simple(self):
        data = {"one": "two"}
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {"one": "two"})

    def test_str_list_key(self):
        """Check that string keys results in valid dictionary"""
        data = {
            "[d _obj key-2]": "val-2",
            "[d][_obj][key-2]": "val-2",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res[""], {
            "d": {"key-2": "val-2"},
        })

    def test_multi_str_list_key(self):
        """Check that string keys results in valid dictionary"""
        data = {
            "[d _obj key-2]": "val-2",
            "[d][_obj][key-2]": "val-2",
            "[d _obj key-5]": "val-5",
            "[d][_obj][key-5]": "val-5",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res[""], {
            "d": {
                "key-2": "val-2",
                "key-5": "val-5",
            },
        })

    def test_int_list_key(self):
        """Check that int key results in valid dictionaory with list"""
        data = {
            "[d 0]": "val-2",
            "[d][0]": "val-2",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res[""], {
            "d": ["val-2"],
        })

    def test_multi_int_list_key(self):
        """Check that int key results in valid dictionaory with list"""
        data = {
            "[d 0]": "val-0",
            "[d][0]": "val-0",
            "[d 1]": "val-1",
            "[d][1]": "val-1",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res[""], {
            "d": ["val-0", "val-1"],
        })
