import unittest
from review_candidates_v2 import image_match


class Tests(unittest.TestCase):
    def setUp(self):
        self.witness = {'url': 'http://site/a.html', 'evidence_refs': [{'quote': 'http://site/media/cache/hash/A/x.jpg'}]}
        self.urls = [{'entity_type': 'product', 'entity_id': 1, 'request_path': 'a.html'}]
        self.values = [{'entity_id': 1, 'attribute_code': 'image', 'value': '/A/x.jpg'}]

    def test_same_record_resource_supported(self):
        self.assertIsNotNone(image_match(self.witness, self.urls, self.values))

    def test_wrong_product_not_supported(self):
        self.values[0]['entity_id'] = 2
        self.assertIsNone(image_match(self.witness, self.urls, self.values))

    def test_similar_filename_not_supported(self):
        self.values[0]['value'] = '/A/y.jpg'
        self.assertIsNone(image_match(self.witness, self.urls, self.values))

    def test_label_without_resource_not_supported(self):
        self.witness['evidence_refs'] = [{'quote': 'Image'}]
        self.assertIsNone(image_match(self.witness, self.urls, self.values))


if __name__ == '__main__':
    unittest.main()
