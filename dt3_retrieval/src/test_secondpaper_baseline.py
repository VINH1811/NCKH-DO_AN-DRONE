"""Small, known-answer checks for track ranking and correlated-query bootstrap."""
import unittest
import numpy as np
from secondpaper_baseline import rank_tracks, query_metrics, clustered_ci


class RetrievalTests(unittest.TestCase):
    def test_multiple_frames_count_as_one_track(self):
        ranked, scores = rank_tracks(np.array([.9, .8, .7, .6]), np.array([1, 1, 2, 3]))
        self.assertEqual(ranked.tolist(), [1, 2, 3])
        rank, metrics = query_metrics(ranked, 2)
        self.assertEqual(rank, 2)
        self.assertEqual(metrics, {"Recall@1": 0., "Recall@5": 1., "Recall@10": 1., "mAP": .5})

    def test_ties_use_track_id(self):
        ranked, _ = rank_tracks(np.array([.5, .5]), np.array([8, 4]))
        self.assertEqual(ranked.tolist(), [4, 8])

    def test_missing_relevant_track_is_error(self):
        with self.assertRaises(ValueError): query_metrics(np.array([1, 2]), 3)

    def test_cluster_bootstrap_is_repeatable_and_preserves_group(self):
        a = clustered_ci([1, 1, 0], [10, 10, 20], 42, 1000)
        self.assertEqual(a, clustered_ci([1, 1, 0], [10, 10, 20], 42, 1000))
        self.assertEqual(a, [0., 1.])
        self.assertEqual(clustered_ci([1, 1], [10, 10], 42, 100), [1., 1.])


if __name__ == "__main__": unittest.main()
