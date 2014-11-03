from solvebio.errors import SolveError
from solvebio.query import BatchQuery
from solvebio.resource import Dataset

from .helper import unittest, SolveBioTestCase


class BatchQueryTest(SolveBioTestCase):
    def setUp(self):
        self.dataset = Dataset.retrieve(self.TEST_DATASET_NAME)
        super(BatchQueryTest, self).setUp()

    def test_invalid_batch_query(self):
        def test(self):
            BatchQuery([
                self.dataset.query(limit=1, fields=['bogus_field']),
                self.dataset.query(limit=10).filter(bogus_id__gt=100000)
            ]).execute()

        self.assertRaises(SolveError, test, self)

    def test_batch_query(self):
        queries = [
            self.dataset.query(limit=1),
            self.dataset.query(limit=10).filter(hgnc_id__gt=100)
        ]
        results = BatchQuery(queries).execute()
        self.assertEqual(len(results), 2)
        self.assertEqual(len(results[0]['results']), 1)
        self.assertEqual(len(results[1]['results']), 10)

if __name__ == "__main__":
    unittest.main()