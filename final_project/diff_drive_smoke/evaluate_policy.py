"""Execute the saved neural policy in Gazebo from predeclared start poses.

    Control uses either aligned odometry or explicitly selected simulator pose.
Gazebo world poses are used independently to score arrival. All goal checking,
speed clipping, timeouts and stopping supervision are explicit non-AI logic.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from policy import Policy, GOAL_RADIUS, relative_goal

ROOT = Path(__file__).resolve().parent
TRIALS = [
    {'name': 'diagonal', 'start': [1.0, 1.0, 0.0], 'goal': [3.0, 2.0]},
    {'name': 'longer', 'start': [1.0, 0.0, 0.7], 'goal': [3.0, 2.0]},
    {'name': 'turn_left', 'start': [2.0, 0.0, -0.8], 'goal': [3.0, 2.0]},
    {'name': 'behind', 'start': [1.0, 2.0, 2.4], 'goal': [3.0, 2.0]},
    {'name': 'turn_right', 'start': [2.0, 1.0, -2.4], 'goal': [3.0, 2.0]},
]
CHECK_TRIALS = [
    {'name': 'check_a', 'start': [0.5, 1.5, -1.2], 'goal': [3.0, 2.0]},
    {'name': 'check_b', 'start': [2.8, -0.5, 2.8], 'goal': [3.0, 2.0]},
    {'name': 'check_c', 'start': [0.7, 0.2, -2.1], 'goal': [3.0, 2.0]},
]
CRITERIA = {'true_goal_radius_m': 0.25, 'controller_stop_radius_m': GOAL_RADIUS,
            'max_final_linear_mps': 0.03, 'max_final_angular_radps': 0.03,
            'max_sim_seconds': 45.0, 'max_wall_seconds': 180.0,
            'stop_hold_sim_seconds': 1.0, 'control_period_sim_seconds': 0.1}

def yaw(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))

def service(endpoint, request_type, request):
    env = dict(os.environ, IGN_PARTITION='pai_delivery_smoke')
    result = subprocess.run(['ign', 'service', '-s', '/world/delivery_smoke/'+endpoint,
        '--reqtype', request_type, '--reptype', 'ignition.msgs.Boolean',
        '--timeout', '3000', '--req', request], capture_output=True, text=True, timeout=10, env=env)
    if result.returncode or 'data: true' not in result.stdout:
        raise RuntimeError(f'{endpoint}: {result.stdout} {result.stderr}')

class Driver(Node):
    def __init__(self):
        super().__init__('learned_delivery_evaluator')
        self.sim = self.odom = self.truth = None
        self.clock_wall = self.odom_wall = self.truth_wall = 0.0
        self.frames = set()
        robot = ET.parse(ROOT / 'world.sdf').getroot().find("world/model[@name='delivery_bot']")
        wheel_xy = [list(map(float, robot.find(f"link[@name='{side}_wheel']/pose").text.split()[:2]))
                    for side in ('left', 'right')]
        self.axle_xy = tuple(sum(w[i] for w in wheel_xy)/2 for i in (0, 1))
        self.create_subscription(Clock, '/clock', self.clock_cb, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self.odom_cb, qos_profile_sensor_data)
        self.create_subscription(PoseStamped, '/model/delivery_bot/pose', self.truth_cb, qos_profile_sensor_data)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def clock_cb(self, msg):
        self.sim = msg.clock.sec+msg.clock.nanosec*1e-9
        self.clock_wall = time.monotonic()

    def odom_cb(self, msg):
        p, q, t = msg.pose.pose.position, msg.pose.pose.orientation, msg.twist.twist
        self.odom = (p.x, p.y, yaw(q), t.linear.x, t.angular.z)
        self.odom_wall = time.monotonic()

    def truth_cb(self, msg):
        self.frames.add(msg.header.frame_id)
        p, q = msg.pose.position, msg.pose.orientation
        self.truth = (p.x, p.y, yaw(q))
        self.truth_wall = time.monotonic()

    def command(self, v=0.0, w=0.0):
        if not math.isfinite(v+w) or abs(v) > 0.35001 or abs(w) > 0.80001:
            raise ValueError('Invalid policy velocity')
        msg = Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.pub.publish(msg)

    def stop(self):
        for _ in range(10):
            self.command()
            rclpy.spin_once(self, timeout_sec=0.02)

    def fresh(self):
        now = time.monotonic()
        return all(now-t < 3.0 for t in (self.clock_wall, self.odom_wall, self.truth_wall))

    def settle_at(self, start):
        self.stop()
        service('control', 'ignition.msgs.WorldControl', 'pause:true')
        x, y, theta = start
        request = f'name:"delivery_bot" position:{{x:{x} y:{y} z:0.325}} orientation:{{z:{math.sin(theta/2)} w:{math.cos(theta/2)}}}'
        service('set_pose', 'ignition.msgs.Pose', request)
        self.truth = None
        self.truth_wall = 0
        service('control', 'ignition.msgs.WorldControl', 'pause:false')
        wall, stable_start, next_zero = time.monotonic(), None, 0
        while time.monotonic()-wall < 30:
            rclpy.spin_once(self, timeout_sec=0.02)
            if time.monotonic() >= next_zero:
                self.command()
                next_zero = time.monotonic()+0.05
            if self.truth is None or self.odom is None or self.sim is None or not self.fresh():
                continue
            angle_error = math.atan2(math.sin(self.truth[2]-theta), math.cos(self.truth[2]-theta))
            near = math.hypot(self.truth[0]-x, self.truth[1]-y) < 0.08 and abs(angle_error) < 0.08
            stopped = abs(self.odom[3]) < 0.03 and abs(self.odom[4]) < 0.03
            if near and stopped:
                if stable_start is None:
                    stable_start = self.sim
                if self.sim-stable_start >= 0.5:
                    return self.odom[:3], self.truth
            else:
                stable_start = None
        raise RuntimeError('Start pose/odometry/world pose not settled; frames=' + repr(sorted(self.frames)))

def evaluate(node, policy, trial, observation):
    origin, truth_origin = node.settle_at(trial['start'])
    angle = truth_origin[2]-origin[2]
    co, si = math.cos(angle), math.sin(angle)
    sim0, wall0 = node.sim, time.monotonic()
    next_tick, stop_since = sim0, None
    rows, infer_ms = [], []
    error = None
    reached = False
    while time.monotonic()-wall0 < CRITERIA['max_wall_seconds']:
        rclpy.spin_once(node, timeout_sec=0.02)
        if not node.fresh():
            error = 'Stale clock, odometry, or evaluation world pose'
            break
        if node.sim < next_tick:
            continue
        next_tick = node.sim+CRITERIA['control_period_sim_seconds']
        dx, dy = node.odom[0]-origin[0], node.odom[1]-origin[1]
        px, py, theta = truth_origin[0]+co*dx-si*dy, truth_origin[1]+si*dx+co*dy, node.odom[2]+angle
        if observation == 'odometry_axle':
            # DiffDrive integrates the wheel-axle centre. The model origin is
            # behind that point; rotating changes their world-space offset.
            ax, ay = node.axle_xy
            initial_yaw = truth_origin[2]
            px += math.cos(initial_yaw)*ax-math.sin(initial_yaw)*ay-math.cos(theta)*ax+math.sin(theta)*ay
            py += math.sin(initial_yaw)*ax+math.cos(initial_yaw)*ay-math.sin(theta)*ax-math.cos(theta)*ay
        if observation == 'sim_pose':
            px, py, theta = node.truth
        d, h = relative_goal(px, py, theta, *trial['goal'])
        if stop_since is None and d <= GOAL_RADIUS:
            stop_since = node.sim
        if stop_since is not None:
            v = w = 0.0
        else:
            tick = time.perf_counter_ns()
            v, w = policy.command(d, h)
            infer_ms.append((time.perf_counter_ns()-tick)/1e6)
        node.command(v, w)
        rows.append({'wall': time.monotonic()-wall0, 'sim': node.sim-sim0, 'x_est': px, 'y_est': py,
            'yaw_est': theta, 'distance_est': d, 'bearing_error': h, 'cmd_v': v, 'cmd_w': w,
            'x_true': node.truth[0], 'y_true': node.truth[1], 'yaw_true': node.truth[2],
            'odom_v': node.odom[3], 'odom_w': node.odom[4]})
        if stop_since is not None and node.sim-stop_since >= CRITERIA['stop_hold_sim_seconds']:
            reached = True
            break
        if node.sim-sim0 >= CRITERIA['max_sim_seconds']:
            error = 'Simulation time limit'
            break
    else:
        error = 'Wall time limit'
    node.stop()
    final_distance = math.hypot(node.truth[0]-trial['goal'][0], node.truth[1]-trial['goal'][1])
    success = reached and error is None and final_distance <= CRITERIA['true_goal_radius_m'] and \
        abs(node.odom[3]) <= CRITERIA['max_final_linear_mps'] and abs(node.odom[4]) <= CRITERIA['max_final_angular_radps']
    result = dict(trial, observation=observation, success=success, error=error, final_true_distance_m=final_distance,
        final_odom_linear_mps=node.odom[3], final_odom_angular_radps=node.odom[4],
        sim_seconds=node.sim-sim0, wall_seconds=time.monotonic()-wall0,
        inference_calls=len(infer_ms), inference_ms_mean=sum(infer_ms)/max(len(infer_ms), 1),
        inference_ms_max=max(infer_ms, default=0), origin_odom=origin, origin_truth=truth_origin)
    return result, rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='learned_evaluation_v1')
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--trials', type=int, default=5)
    parser.add_argument('--observation', choices=['odometry', 'odometry_axle', 'sim_pose'], default='odometry_axle')
    parser.add_argument('--suite', choices=['development', 'check'], default='development')
    args = parser.parse_args()
    out = ROOT / 'results' / args.name
    if not args.probe and out.exists():
        raise SystemExit('Existing evaluation preserved: ' + str(out))
    rclpy.init()
    node = Driver()
    results = []
    try:
        if args.probe:
            service('control', 'ignition.msgs.WorldControl', 'pause:false')
            until = time.monotonic()+15
            while time.monotonic() < until and (node.truth is None or node.odom is None):
                rclpy.spin_once(node, timeout_sec=0.05)
            print(json.dumps({'frames': sorted(node.frames), 'truth': node.truth, 'odom': node.odom, 'sim': node.sim}), flush=True)
            return 0 if node.truth and node.odom else 1
        out.mkdir(parents=True)
        policy = Policy()
        trials = (TRIALS if args.suite == 'development' else CHECK_TRIALS)[:args.trials]
        configuration = {'criteria': CRITERIA, 'trials': trials, 'suite': args.suite,
            'observation': args.observation,
            'axle_center_in_model_xy_m': node.axle_xy,
            'simulator_processes': json.loads((ROOT / 'results/processes.json').read_text()),
            'model_sha256': hashlib.sha256((ROOT / 'learned/policy.npz').read_bytes()).hexdigest(),
            'control': 'Learned velocity policy using '+args.observation,
            'evaluation': 'Gazebo model pose distance. In sim_pose mode this is also the control observation; perfect simulated localization is assumed.',
            'non_ai': ['pose setup', 'odometry alignment', 'speed bounds', 'goal threshold', 'stop hold', 'watchdogs'],
            'limits': f'{len(trials)} designed starts, one goal, no obstacles. Not evidence of broad navigation generalization.'}
        (out / 'protocol.json').write_text(json.dumps(configuration, indent=2))
        for trial in trials:
            print('START', trial['name'], flush=True)
            result, rows = evaluate(node, policy, trial, args.observation)
            results.append(result)
            with (out / (trial['name']+'.csv')).open('w', newline='') as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
            (out / 'summary.json').write_text(json.dumps({'protocol': configuration, 'results': results,
                'successes': sum(r['success'] for r in results), 'completed_trials': len(results)}, indent=2))
            print('RESULT', json.dumps(result), flush=True)
    except Exception as exc:
        if out.exists():
            (out / 'failure.txt').write_text(repr(exc))
        raise
    finally:
        node.stop()
        try:
            service('control', 'ignition.msgs.WorldControl', 'pause:true')
        finally:
            node.destroy_node()
            rclpy.shutdown()
    return 0 if results and all(r['success'] for r in results) else 1

if __name__ == '__main__':
    raise SystemExit(main())
