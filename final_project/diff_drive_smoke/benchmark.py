"""Measure actual /clock and /odom while testing forward, turn, and stop.

This is an environment smoke test, NOT an AI policy or a final submission demo.
Uses simulation time for motion phases and wall time for the watchdog.
"""
import argparse
import csv
import json
import math
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock

ROOT = Path(__file__).resolve().parent

class Probe(Node):
    def __init__(self):
        super().__init__('delivery_smoke_probe')
        self.sim = None
        self.pose = None
        self.odom_wall = None
        self.clock_wall = None
        self.counts = {'clock': 0, 'odom': 0}
        self.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self.on_odom, qos_profile_sensor_data)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def on_clock(self, msg):
        self.sim = msg.clock.sec + msg.clock.nanosec * 1e-9
        self.clock_wall = time.monotonic()
        self.counts['clock'] += 1

    def on_odom(self, msg):
        p, q, t = msg.pose.pose.position, msg.pose.pose.orientation, msg.twist.twist
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        self.pose = {'x': p.x, 'y': p.y, 'yaw': yaw, 'v': t.linear.x, 'w': t.angular.z}
        self.odom_wall = time.monotonic()
        self.counts['odom'] += 1

    def command(self, v=0.0, w=0.0):
        msg = Twist()
        msg.linear.x, msg.angular.z = v, w
        self.pub.publish(msg)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='baseline')
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    rclpy.init()
    node = Probe()
    start_wall = time.monotonic()
    start_sim = None
    previous = None
    points, rows = {}, []
    complete = False
    error = None
    next_tick = start_wall
    try:
        while time.monotonic() - start_wall < args.timeout:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            if now < next_tick:
                continue
            next_tick = now + 0.05
            if node.sim is None or node.pose is None:
                if now-start_wall > 20:
                    error = 'No /clock or /odom within 20 wall seconds'
                    break
                continue
            if start_sim is None:
                start_sim, start_wall = node.sim, now
            elapsed = node.sim-start_sim
            phase = 'settle' if elapsed < 2 else 'forward' if elapsed < 5 else 'turn' if elapsed < 7 else 'stop'
            if phase != previous:
                points[phase] = dict(node.pose, sim=node.sim, wall=now-start_wall)
                print(phase, json.dumps(points[phase]), flush=True)
                previous = phase
            if now-node.odom_wall > 3 or now-node.clock_wall > 3:
                error = 'Stale odometry or simulation clock'
                break
            if phase == 'forward':
                node.command(0.35, 0.0)
            elif phase == 'turn':
                node.command(0.0, 0.6)
            else:
                node.command()
            rows.append(dict(wall=now-start_wall, sim=elapsed, phase=phase, **node.pose))
            if elapsed >= 9:
                points['end'] = dict(node.pose, sim=node.sim, wall=now-start_wall)
                complete = True
                break
        if not complete and error is None:
            error = 'Wall-time watchdog expired'
    finally:
        for _ in range(5):
            node.command()
            rclpy.spin_once(node, timeout_sec=0.05)
        out = ROOT / 'results'
        out.mkdir(exist_ok=True)
        result = {'complete': complete, 'error': error, 'counts': node.counts, 'phases': points,
                  'note': 'Scripted motion only; no AI. RTF is the ratio over this measurement window.'}
        if (ROOT / 'scene_metadata.json').exists():
            result['scene'] = json.loads((ROOT / 'scene_metadata.json').read_text())
        if rows:
            result.update(wall_seconds=rows[-1]['wall'], sim_seconds=rows[-1]['sim'],
                          rtf=rows[-1]['sim']/max(rows[-1]['wall'], 1e-9))
            with (out / (args.name + '.csv')).open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        if complete:
            a, b, c, d = [points[k] for k in ('forward', 'turn', 'stop', 'end')]
            distance = math.hypot(b['x']-a['x'], b['y']-a['y'])
            rotation = abs(math.atan2(math.sin(c['yaw']-b['yaw']), math.cos(c['yaw']-b['yaw'])))
            drift = math.hypot(d['x']-c['x'], d['y']-c['y'])
            result.update(forward_distance_m=distance, turn_angle_rad=rotation, stop_drift_m=drift,
                          final_linear_speed=d['v'], final_angular_speed=d['w'])
            result['checks'] = {'forward': distance > 0.2, 'turn': rotation > 0.3,
                                'stop': abs(d['v']) < 0.05 and abs(d['w']) < 0.05}
        (out / (args.name + '.json')).write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2), flush=True)
        node.destroy_node()
        rclpy.shutdown()
    return 0 if complete and all(result.get('checks', {}).values()) else 1

if __name__ == '__main__':
    raise SystemExit(main())
