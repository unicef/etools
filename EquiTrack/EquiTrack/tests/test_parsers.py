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
            "sample[1]": "List Int",
            "sample[str]": "List Str",
            "sample[1][str]": "Var Int Str"
        }
        self.assertEqual(
            parsers._create_lists_from_dict_keys(data),
            [
                [1],
                ["sample", 1],
                ["sample", 1, "str"],
                ["sample", "str"],
                ["str"],
            ]
        )

    def test_sorted_keys(self):
        data = {
            "a[10]": "Int10",
            "a[2]": "Int2",
            "a[30]": "Int30",
            "a[3]": "Int3",
            "a[4]": "Int4",
            "a[b]": "Str",
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
        self.assertEqual(parsers._create_key(["sample", 1]), "sample[1]")

    def test_multi_element(self):
        """If multiple elements in list then return dict str of path"""
        res = parsers._create_key(["sample", "d", "k", "2"])
        self.assertEqual(res, "sample[d][k][2]")

    def test_unicode(self):
        """If multiple elements in list then return dict str of path"""
        res = parsers._create_key(["sample", u"m\xe9lange", "k", "2"])
        self.assertEqual(res, "sample[m\xe9lange][k][2]")


class TestInitData(TestCase):
    def test_int_new(self):
        """Test int key, that does NOT exist"""
        self.assertEqual(parsers._init_data([], 0, []), [[]])

    def test_int_exists(self):
        """Test int key, that does exist"""
        self.assertEqual(parsers._init_data([[1, 2, 3]], 0, []), [[1, 2, 3]])

    def test_str_new(self):
        """Test str key, that does NOT exist"""
        self.assertEqual(parsers._init_data({}, "new", {}), {"new": {}})

    def test_str_exists(self):
        """Test str key, that does exist"""
        self.assertEqual(
            parsers._init_data({"old": "exists"}, "old", {}),
            {"old": "exists"}
        )


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
            "sample[d][_obj][key-2]": "val-2",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "sample": {
                "d": {"key-2": "val-2"},
            }
        })

    def test_multi_str_list_key(self):
        """Check that string keys results in valid dictionary"""
        data = {
            "sample[d][_obj][key-2]": "val-2",
            "sample[d][_obj][key-5]": "val-5",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "sample": {
                "d": {
                    "key-2": "val-2",
                    "key-5": "val-5",
                },
            }
        })

    def test_int_list_key(self):
        """Check that int key results in valid dictionary with list"""
        data = {
            "sample[d][0]": "val-2",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "sample": {
                "d": ["val-2"],
            }
        })

    def test_multi_int_list_key(self):
        """Check that int key results in valid dictionary with list"""
        data = {
            "sample[d][0]": "val-0",
            "sample[d][1]": "val-1",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "sample": {
                "d": ["val-0", "val-1"],
            }
        })

    def test_mix(self):
        """Check that int key results in valid dictionary with list"""
        data = {
            "one": "two",
            "sample[d][0]": "val-0",
            "sample[d][1]": "val-1",
            "sample[extra][_obj][key-2]": "val-2",
            "sample[extra][_obj][key-5]": "val-5",
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            "one": "two",
            "sample": {
                "d": ["val-0", "val-1"],
                "extra": {"key-2": "val-2", "key-5": "val-5"}
            }
        })

    def test_use_case(self):
        """Check live use case sample"""
        data = {
            u'attachments[8][_obj][type]': [u'133'],
            u'attachments[7][_obj][id]': [u'1681'],
            u'attachments[0][_obj][intervention]': [u'71'],
            u'sector_locations[0][_obj][locations][4]': [u'7705'],
            u'sector_locations[0][_obj][locations][0]': [u'7699'],
            u'attachments[8][_obj][id]': [u'1693'],
            u'sector_locations[0][_obj][locations][2]': [u'7702'],
            u'attachments[1][_obj][id]': [u'1691'],
            u'attachments[2][_obj][id]': [u'1692'],
            u'attachments[5][_obj][type]': [u'135'],
            u'attachments[2][_obj][type]': [u'135'],
            u'attachments[6][_obj][id]': [u'1680'],
            u'offices[0]': [u'1'],
            u'unicef_focal_points[0]': [u'1086'],
            u'attachments[0][_obj][attachment]': ["sample.pdf"],
            u'partner_focal_points[0]': [u'99'],
            u'attachments[1][_obj][type]': [u'135'],
            u'sector_locations[0][_obj][id]': [u'230'],
            u'sector_locations[0][_obj][sector]': [u'4'],
            u'attachments[6][_obj][type]': [u'135'],
            u'attachments[5][_obj][id]': [u'1679'],
            u'sector_locations[0][_obj][locations][3]': [u'7704'],
            u'attachments[0][_obj][type]': [u'135'],
            u'sector_locations[0][_obj][locations][5]': [u'7701'],
            u'attachments[4][_obj][type]': [u'135'],
            u'sector_locations[0][_obj][locations][1]': [u'7706'],
            u'attachments[0][_obj][id]': [None],
            u'attachments[3][_obj][id]': [u'1677'],
            u'attachments[4][_obj][id]': [u'1678'],
            u'attachments[3][_obj][type]': [u'135'],
            u'attachments[9][_obj][type]': [u'135'],
            u'attachments[9][_obj][id]': [u'1694'],
            u'attachments[7][_obj][type]': [u'135']
        }
        res = parsers.parse_multipart_data(data)
        self.assertEqual(res, {
            'unicef_focal_points': [[u'1086']],
            'sector_locations': [
                {
                    'sector': [u'4'],
                    'id': [u'230'],
                    'locations': [
                        [u'7699'],
                        [u'7706'],
                        [u'7702'],
                        [u'7704'],
                        [u'7705'],
                        [u'7701']
                    ]
                }
            ],
            'offices': [[u'1']],
            'attachments': [
                {'intervention': [u'71'], 'type': [u'135'], 'attachment': ['sample.pdf'], 'id': [None]},
                {'type': [u'135'], 'id': [u'1691']},
                {'type': [u'135'], 'id': [u'1692']},
                {'type': [u'135'], 'id': [u'1677']},
                {'type': [u'135'], 'id': [u'1678']},
                {'type': [u'135'], 'id': [u'1679']},
                {'type': [u'135'], 'id': [u'1680']},
                {'type': [u'135'], 'id': [u'1681']},
                {'type': [u'133'], 'id': [u'1693']},
                {'type': [u'135'], 'id': [u'1694']}
            ],
            'partner_focal_points': [[u'99']]
        })
