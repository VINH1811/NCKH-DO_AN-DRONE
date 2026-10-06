"""Ensure query comparisons cannot accidentally change pairing or labels."""
import unittest
import pandas as pd
from secondpaper_comparison import paired_difference, dev_data, reviewed_queries


class ComparisonTests(unittest.TestCase):
    def test_pairing_is_by_id_not_position(self):
        left = pd.DataFrame({"track_id": [11, 12], "Recall@1": [0., 1.]}, index=[101, 102])
        right = pd.DataFrame({"track_id": [12, 11], "Recall@1": [1., 1.]}, index=[102, 101])
        value, low, high = paired_difference(left, right, "Recall@1", 42, 100)
        self.assertEqual(value, 50.)
        self.assertGreaterEqual(low, 0.)
        self.assertLessEqual(high, 100.)

    def test_missing_query_rejected(self):
        a = pd.DataFrame({"track_id": [11, 12], "Recall@1": [0., 1.]}, index=[101, 102])
        with self.assertRaises(ValueError): paired_difference(a, a.iloc[:1], "Recall@1", 42, 100)

    def test_changed_target_rejected(self):
        a = pd.DataFrame({"track_id": [11], "Recall@1": [0.]}, index=[101])
        b = pd.DataFrame({"track_id": [12], "Recall@1": [1.]}, index=[101])
        with self.assertRaises(ValueError): paired_difference(a, b, "Recall@1", 42, 100)

    def test_review_only_contains_frozen_dev(self):
        _, dev, _, _, _ = dev_data()
        review = reviewed_queries(dev)
        self.assertEqual(len(review), 76)
        self.assertEqual(set(review.annot_id), set(dev.annot_id))


if __name__ == "__main__": unittest.main()
