"""Regression checks for ordered visits, final scoring, and frame continuity."""
import math
import unittest
from waypoint_route import ROUTE, Sequencer, aligned_model_pose, aligned_axle_pose, model_to_axle, score_route


class WaypointTests(unittest.TestCase):
    def test_cannot_skip_a_point(self):
        s = Sequencer(ROUTE['goals'])
        self.assertIsNone(s.update(ROUTE['goals'][2], 1))
        self.assertEqual(s.index, 0)
        self.assertEqual(s.visits, [])

    def test_only_final_point_requests_stop(self):
        s = Sequencer(ROUTE['goals'])
        for n, goal in enumerate(ROUTE['goals'], 1):
            self.assertEqual(s.update(goal, n*10), n)
            if n < 4:
                self.assertIsNone(s.final_since)
        self.assertEqual(s.final_since, 40)
        self.assertEqual(s.visits, [1, 2, 3, 4])
        self.assertIsNone(s.update(ROUTE['goals'][-1], 41))
        self.assertEqual(s.visits, [1, 2, 3, 4])

    def test_truth_and_stop_are_both_required(self):
        visits = [{'point': n, 'true_distance_m': 0.18} for n in range(1, 5)]
        args = [visits, ROUTE['goals'][-1], ROUTE['goals'][-1], (0, 0), True, None]
        self.assertTrue(score_route(*args)[0])
        visits[1]['true_distance_m'] = 0.30
        self.assertFalse(score_route(*args)[0])
        visits[1]['true_distance_m'] = 0.18
        args[3] = (0, 0.1)
        self.assertFalse(score_route(*args)[0])
        args[3], args[4] = (0, 0), False
        self.assertFalse(score_route(*args)[0])

    def test_no_success_from_wrong_order_or_stale_data(self):
        visits = [{'point': n, 'true_distance_m': 0.18} for n in [1, 3, 2, 4]]
        self.assertFalse(score_route(visits, (0, 3), (0, 3), (0, 0), True, None)[0])
        visits.sort(key=lambda x: x['point'])
        self.assertFalse(score_route(visits, (0, 3), (0, 3), (0, 0), True, 'Stale clock')[0])

    def test_axle_pivot_uses_same_origin_after_turn(self):
        a = 0.5542825
        # Fixed axle centre, 90-degree turn: model origin swings around the axle.
        pose = aligned_model_pose((0, 0, math.pi/2), (0, 0, 0), (2, 3, 0), (a, 0))
        self.assertAlmostEqual(pose[0], 2+a)
        self.assertAlmostEqual(pose[1], 3-a)
        pose2 = aligned_model_pose((1, 0, 0), (0, 0, 0), (2, 3, math.pi/2), (a, 0))
        self.assertAlmostEqual(pose2[0], 2)
        self.assertAlmostEqual(pose2[1], 4)

    def test_invalid_route_rejected(self):
        with self.assertRaises(ValueError):
            Sequencer([[0, 0]]*4)
        with self.assertRaises(ValueError):
            Sequencer([[math.nan, 0], [1, 0], [2, 0], [3, 0]])

    def test_axle_centre_does_not_move_during_pure_rotation(self):
        a = 0.5542825
        for theta in (0, math.pi/2, math.pi, -math.pi/2):
            axle = aligned_axle_pose((0, 0, theta), (0, 0, 0), (0, 0, 0), (a, 0))
            self.assertAlmostEqual(axle[0], a)
            self.assertAlmostEqual(axle[1], 0)
            model = aligned_model_pose((0, 0, theta), (0, 0, 0), (0, 0, 0), (a, 0))
            truth_axle = model_to_axle(model, (a, 0))
            self.assertAlmostEqual(truth_axle[0], axle[0])
            self.assertAlmostEqual(truth_axle[1], axle[1])


if __name__ == '__main__':
    unittest.main()
