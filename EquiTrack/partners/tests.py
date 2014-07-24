__author__ = 'jcranwellward'


from django.test import TestCase


class FACETestCase(TestCase):

    def test_api(self):

        data = {
            "relayer": "76",
            "phone": "+96170996620",
            "flow": "1317",
            "step": "805a9ad0-1467-4daf-ac9f-26060fcdd29d",
            "time": "2014-07-23T18:41:14.601Z",
            "values": [{
                "category": "Valid",
                "text": "Parkitlogaunc",
                "rule_value": "valid",
                "value": "valid",
                "label": "PCA Number",
                "time": "2014-07-23T18:35:34.884308Z"
            }, {
                "category": None,
                "text": "20",
                "rule_value": "20",
                "value": "20.00000000",
                "label": "amount",
                "time": "2014-07-23T18:35:34.906070Z"
            }]
        }

        response = self.client.post('partners/pca/validate', data)

        self.assertEqual(response.status_code, 200)