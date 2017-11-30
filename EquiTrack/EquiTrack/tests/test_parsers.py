from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from unittest import TestCase

from EquiTrack import parsers


class TestIntOrString(TestCase):
    def test_int(self):
        self.assertEqual(parsers._int_or_str(1), 1)

    def test_str_to_int(self):
        self.assertEqual(parsers._int_or_str("1"), 1)

    def test_str(self):
        self.assertEqual(parsers._int_or_str("one"), "one")


class TestNaturalKeys(TestCase):
    def test_int(self):
        self.assertEqual(parsers._natural_keys('123'), ["", 123, ""])

    def test_str(self):
        self.assertEqual(parsers._natural_keys('abc'), ['abc'])

    def test_mix(self):
        self.assertEqual(parsers._natural_keys('a1b2'), ['a', 1, 'b', 2, ""])
        self.assertEqual(
            parsers._natural_keys('a12bc3d'),
            ['a', 12, 'bc', 3, 'd']
        )


class TestCreateListsFromDictKeys(TestCase):
    def test_empty_dict(self):
        self.assertEqual(parsers._create_lists_from_dict_keys({}), [])

    def test_keys(self):
        data = {
            "1": "Int",
            "str": "Str",
            "[1]": "List Int",
            "[str]": "List Str",
            "[1 str]": "List Int Str"
        }
        self.assertEqual(
            parsers._create_lists_from_dict_keys(data),
            [[1], ["", 1, "str"], ["", 1], ["", "str"], ["str"]]
        )

    def test_sorted_keys(self):
        data = {
            "a 10": "Int10",
            "a 2": "Int2",
            "a 30": "Int30",
            "a 3": "Int3",
            "a 4": "Int4",
            "a b": "Str",
        }
        self.assertEqual(
            parsers._create_lists_from_dict_keys(data),
            [['a', 2], ['a', 3], ['a', 4], ['a', 10], ['a', 30], ['a', 'b']]
        )


class TestCreateKey(TestCase):
    def test_empty(self):
        """If empty path list provided, then return an empty string"""
        self.assertEqual(parsers._create_key([]), "")

    def test_single_element(self):
        """If only one element in list then return str of that element"""
        self.assertEqual(parsers._create_key(["", 1]), "[1]")

    def test_multi_element(self):
        """If multiple elements in list then return dict str of path"""
        res = parsers._create_key(["", "d", "k", "2"])
        self.assertEqual(res, "[d][k][2]")

    def test_unicode(self):
        """If multiple elements in list then return dict str of path"""
        res = parsers._create_key(["", u"m\xe9lange", "k", "2"])
        self.assertEqual(res, "[m\xe9lange][k][2]")


class TestBuildParsedData(TestCase):
    def test_dict(self):
        """Check handling of last element as a string, should result in
        dictionary"""
        keys = ["one", "two"]
        res = parsers.build_parsed_data({}, keys, "end")
        self.assertEqual(res, {"one": {"two": "end"}})

    def test_dict_recursion(self):
        """Check a few recursion levels with result being a dictionary"""
        keys = ["one", "two", "three", "four"]
        res = parsers.build_parsed_data({}, keys, "end")
        self.assertEqual(res, {"one": {"two": {"three": {"four": "end"}}}})

    def test_list(self):
        """Check handling of last element as an integer, should result in
        list at 'end' of dictionary
        """
        keys = ["one", 1]
        res = parsers.build_parsed_data({}, keys, "end")
        self.assertEqual(res, {"one": ["end"]})

    def test_list_recursion(self):
        """Check a few recursion levels with integer as last element in list"""
        keys = ["one", "two", "three", 1]
        res = parsers.build_parsed_data({}, keys, "end")
        self.assertEqual(res, {"one": {"two": {"three": ["end"]}}})


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
        self.assertEqual(res, {
            "": {
                "d": {"key-2": "val-2"},
            }
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
        self.assertEqual(res, {
            "": {
                "d": {
                    "key-2": "val-2",
                    "key-5": "val-5",
                },
            }
        })

    def test_int_list_key(self):
        """Check that int key results in valid dictionary with list"""
        data = {
            "[d 0]": "val-2",
            "[d][0]": "val-2",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "": {
                "d": ["val-2"],
            }
        })

    def test_multi_int_list_key(self):
        """Check that int key results in valid dictionary with list"""
        data = {
            "[d 0]": "val-0",
            "[d][0]": "val-0",
            "[d 1]": "val-1",
            "[d][1]": "val-1",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "": {
                "d": ["val-0", "val-1"],
            }
        })

    def test_mix(self):
        """Check that int key results in valid dictionary with list"""
        data = {
            "one": "two",
            "[d 0]": "val-0",
            "[d][0]": "val-0",
            "[d 1]": "val-1",
            "[d][1]": "val-1",
            "[extra _obj key-2]": "val-2",
            "[extra][_obj][key-2]": "val-2",
            "[extra _obj key-5]": "val-5",
            "[extra][_obj][key-5]": "val-5",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "one": "two",
            "": {
                "d": ["val-0", "val-1"],
                "extra": {"key-2": "val-2", "key-5": "val-5"}
            }
        })
