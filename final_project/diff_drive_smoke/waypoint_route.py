"""Declared four-point route and non-learned goal sequencing.

The neural policy chooses linear/angular velocity. This supervisor only chooses
the current goal and requests the final stop; it does not learn a route.
"""
from dataclasses import dataclass, field
import math

ROUTE = {
    'name': 'four_points_axle_v2',
    'start': [0.0, 0.0, 0.0],
    'goals': [[1.5, 0.0], [1.5, 1.5], [0.0, 1.5], [0.0, 3.0]],
    'goal_reference': 'wheel_axle_center',
}
CRITERIA = {
    'switch_radius_m': 0.20,
    'true_goal_radius_m': 0.25,
    'stop_hold_sim_seconds': 1.0,
    'max_final_linear_mps': 0.03,
    'max_final_angular_radps': 0.03,
    'max_sim_seconds': 120.0,
    'max_wall_seconds': 360.0,
    'control_period_sim_seconds': 0.1,
}
COLORS = ['0.1 0.65 0.9 1', '0.95 0.65 0.05 1',
          '0.65 0.3 0.85 1', '0.1 0.75 0.4 1']


@dataclass
class Sequencer:
    goals: list
    radius: float = CRITERIA['switch_radius_m']
    index: int = 0
    final_since: float | None = None
    visits: list = field(default_factory=list)

    def __post_init__(self):
        if len(self.goals) != 4 or not math.isfinite(self.radius) or self.radius <= 0:
            raise ValueError('Exactly four goals and a positive finite radius are required')
        if any(len(g) != 2 or not all(math.isfinite(v) for v in g) for g in self.goals):
            raise ValueError('Goals must be finite x/y pairs')
        if any(math.dist(a, b) <= 2*self.radius for a, b in zip(self.goals, self.goals[1:])):
            raise ValueError('Consecutive waypoint acceptance areas must not overlap')

    @property
    def goal(self):
        return self.goals[self.index]

    def update(self, xy, sim_seconds):
        """Accept at most the current point per tick; return its 1-based number."""
        if self.final_since is not None or math.dist(xy, self.goal) > self.radius:
            return None
        number = self.index + 1
        self.visits.append(number)
        if number == len(self.goals):
            self.final_since = sim_seconds
        else:
            self.index += 1
        return number


def aligned_model_pose(odom, origin, truth_origin, axle_xy):
    """Apply the existing axle-to-model correction with ONE initial alignment."""
    angle = truth_origin[2] - origin[2]
    co, si = math.cos(angle), math.sin(angle)
    dx, dy = odom[0] - origin[0], odom[1] - origin[1]
    theta = odom[2] + angle
    px = truth_origin[0] + co*dx - si*dy
    py = truth_origin[1] + si*dx + co*dy
    ax, ay = axle_xy
    initial_yaw = truth_origin[2]
    px += math.cos(initial_yaw)*ax - math.sin(initial_yaw)*ay - math.cos(theta)*ax + math.sin(theta)*ay
    py += math.sin(initial_yaw)*ax + math.cos(initial_yaw)*ay - math.sin(theta)*ax - math.cos(theta)*ay
    return px, py, theta


def model_to_axle(pose, axle_xy):
    x, y, theta = pose
    ax, ay = axle_xy
    return (x + math.cos(theta)*ax - math.sin(theta)*ay,
            y + math.sin(theta)*ax + math.cos(theta)*ay, theta)


def aligned_axle_pose(odom, origin, truth_origin, axle_xy):
    """Wheel velocities describe this point's unicycle motion, including turns."""
    initial_axle = model_to_axle(truth_origin, axle_xy)
    angle = truth_origin[2] - origin[2]
    dx, dy = odom[0]-origin[0], odom[1]-origin[1]
    return (initial_axle[0] + math.cos(angle)*dx - math.sin(angle)*dy,
            initial_axle[1] + math.sin(angle)*dx + math.cos(angle)*dy,
            odom[2] + angle)


def score_route(visits, final_xy, final_goal, final_speed, hold_complete, error):
    final_error = math.dist(final_xy, final_goal)
    success = (error is None and hold_complete and
               [v['point'] for v in visits] == [1, 2, 3, 4] and
               all(v['true_distance_m'] <= CRITERIA['true_goal_radius_m'] for v in visits) and
               final_error <= CRITERIA['true_goal_radius_m'] and
               abs(final_speed[0]) <= CRITERIA['max_final_linear_mps'] and
               abs(final_speed[1]) <= CRITERIA['max_final_angular_radps'])
    return bool(success), final_error
