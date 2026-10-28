"""Continuous four-point Gazebo run using the saved neural policy.

Reset and align coordinates once at the beginning, never between waypoints.
Ground truth scores the visits but does not select goals or control velocities.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import time
import rclpy
from evaluate_policy import Driver, service
from policy import Policy, relative_goal
from waypoint_route import ROUTE, CRITERIA, Sequencer, aligned_axle_pose, model_to_axle, score_route

ROOT = Path(__file__).resolve().parent


def run(node, policy, out):
    origin, truth_origin = node.settle_at(ROUTE['start'])
    sequencer = Sequencer(ROUTE['goals'])
    sim0, wall0, epoch0 = node.sim, time.monotonic(), time.time()
    next_tick = node.sim
    visits, rows, infer_ms = [], [], []
    error, complete = None, False
    (out / 'timing.json').write_text(json.dumps({'motion_start_unix': epoch0}, indent=2))
    print('MOTION_START', epoch0, flush=True)
    with (out / 'trajectory.csv').open('w', newline='') as f:
        writer = None
        try:
            while time.monotonic()-wall0 < CRITERIA['max_wall_seconds']:
                rclpy.spin_once(node, timeout_sec=0.02)
                if not node.fresh():
                    error = 'Stale clock, odometry, or evaluation pose'
                    break
                if node.sim < next_tick:
                    continue
                next_tick = node.sim + CRITERIA['control_period_sim_seconds']
                elapsed = node.sim-sim0
                px, py, theta = aligned_axle_pose(node.odom, origin, truth_origin, node.axle_xy)
                true_axle = model_to_axle(node.truth, node.axle_xy)
                accepted = sequencer.update((px, py), elapsed)
                if accepted is not None:
                    goal = ROUTE['goals'][accepted-1]
                    visit = {'point': accepted, 'goal': goal, 'sim_seconds': elapsed,
                             'wall_seconds': time.monotonic()-wall0,
                             'estimated_distance_m': math.dist((px, py), goal),
                             'true_distance_m': math.dist(true_axle[:2], goal),
                             'true_xy': list(true_axle[:2])}
                    visits.append(visit)
                    (out / 'visits.json').write_text(json.dumps(visits, indent=2))
                    print('VISIT', json.dumps(visit), flush=True)
                d, h = relative_goal(px, py, theta, *sequencer.goal)
                if sequencer.final_since is None:
                    tick = time.perf_counter_ns()
                    v, w = policy.command(d, h)
                    infer_ms.append((time.perf_counter_ns()-tick)/1e6)
                else:
                    v = w = 0.0
                node.command(v, w)
                row = {'wall': time.monotonic()-wall0, 'sim': elapsed,
                       'target': sequencer.index+1, 'accepted_point': accepted or 0,
                       'phase': 'stop' if sequencer.final_since is not None else 'travel',
                       'x_est': px, 'y_est': py, 'yaw_est': theta,
                       'distance_est': d, 'bearing_error': h, 'cmd_v': v, 'cmd_w': w,
                       'x_true': true_axle[0], 'y_true': true_axle[1], 'yaw_true': true_axle[2],
                       'model_x_true': node.truth[0], 'model_y_true': node.truth[1],
                       'odom_v': node.odom[3], 'odom_w': node.odom[4]}
                rows.append(row)
                if writer is None:
                    writer = csv.DictWriter(f, fieldnames=list(row))
                    writer.writeheader()
                writer.writerow(row)
                if accepted is not None:
                    f.flush()
                if sequencer.final_since is not None and elapsed-sequencer.final_since >= CRITERIA['stop_hold_sim_seconds']:
                    complete = True
                    break
                if elapsed >= CRITERIA['max_sim_seconds']:
                    error = 'Simulation time limit'
                    break
            else:
                error = 'Wall time limit'
        except (Exception, KeyboardInterrupt) as exc:
            error = repr(exc)
        finally:
            node.stop()
    success, final_distance = score_route(visits, model_to_axle(node.truth, node.axle_xy)[:2], ROUTE['goals'][-1],
                                          node.odom[3:5], complete, error)
    result = {'success': success, 'error': error, 'route': ROUTE, 'visits': visits,
              'hold_complete': complete, 'final_true_distance_m': final_distance,
              'final_odom_linear_mps': node.odom[3], 'final_odom_angular_radps': node.odom[4],
              'sim_seconds': node.sim-sim0, 'wall_seconds': time.monotonic()-wall0,
              'motion_start_unix': epoch0, 'inference_calls': len(infer_ms),
              'inference_ms_mean': sum(infer_ms)/max(1, len(infer_ms)),
              'inference_ms_max': max(infer_ms, default=0)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if Path(args.name).name != args.name or args.name in ('.', '..'):
        raise SystemExit('Use a single result directory name')
    processes = json.loads((ROOT / 'results/processes.json').read_text())
    if not processes or not all(p.get('waypoints') for p in processes):
        raise SystemExit('Launch start_demo.py --waypoints first')
    out = ROOT / 'results' / args.name
    out.mkdir(parents=True, exist_ok=False)
    configuration = {
        'route': ROUTE, 'criteria': CRITERIA, 'observation': 'aligned_wheel_axle_odometry',
        'model_sha256': hashlib.sha256((ROOT / 'learned/policy.npz').read_bytes()).hexdigest(),
        'world_sha256': hashlib.sha256((ROOT / 'world_waypoints.sdf').read_bytes()).hexdigest(),
        'simulator_processes': processes,
        'ai': 'Saved PyTorch-trained neural policy, NumPy inference; linear m/s and angular rad/s velocity',
        'non_ai': ['one initial pose reset/alignment', 'ordered waypoint switching', 'final stop',
                   'speed limits', 'watchdogs'],
        'evaluation': 'Gazebo model pose transformed to wheel axle centre at each transition and after final stop',
        'limits': 'One declared route, no obstacles. Separate task from single-goal trials.'}
    (out / 'protocol.json').write_text(json.dumps(configuration, indent=2))
    rclpy.init()
    node = Driver()
    try:
        result = run(node, Policy(), out)
        (out / 'summary.json').write_text(json.dumps({'protocol': configuration, 'result': result}, indent=2))
        print('RESULT', json.dumps(result), flush=True)
        return 0 if result['success'] else 1
    except Exception as exc:
        (out / 'failure.txt').write_text(repr(exc))
        raise
    finally:
        try:
            node.stop()
            service('control', 'ignition.msgs.WorldControl', 'pause:true')
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
