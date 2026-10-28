"""Record the desktop during a smoke test or a saved learned-policy trial."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from recording_checks import recording_geometry, validate_recording

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('name', nargs='?', default='recorded')
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--learned', action='store_true')
mode.add_argument('--waypoints', action='store_true')
args = parser.parse_args()
name = args.name
if not name or Path(name).name != name or name in ('.', '..'):
    raise SystemExit('Use a non-empty single result name')
video = OUT / (name + '.mp4')
if video.exists():
    raise SystemExit('Refusing to overwrite an existing recording: ' + str(video))
env = os.environ.copy()
env.update(DISPLAY=':0', XAUTHORITY='/home/ubuntu/.Xauthority')
display_info = subprocess.check_output(['xdpyinfo'], env=env, text=True, timeout=10)
dimensions = re.search(r'dimensions:\s+(\d+)x(\d+)\s+pixels', display_info)
if not dimensions:
    raise RuntimeError('Cannot determine the desktop dimensions for recording')
capture_width, capture_height = int(dimensions.group(1)), int(dimensions.group(2))
encoded_size = recording_geometry(capture_width, capture_height)
capture_size = f'{capture_width}x{capture_height}'
video_size = f'{encoded_size[0]}x{encoded_size[1]}'
recording_info = {
    'capture_size': capture_size, 'video_size': video_size,
    'padding_right_bottom_pixels': [encoded_size[0]-capture_width, encoded_size[1]-capture_height],
    'recording_success': False,
    'frame_rate': 15, 'render_scene': json.loads(
        (ROOT / ('waypoint_scene_metadata.json' if args.waypoints else 'scene_metadata.json')).read_text()),
    'learned': args.learned or args.waypoints,
    'waypoints': args.waypoints,
    'purpose': 'Continuous four-point learned-policy demonstration' if args.waypoints else
        'Repeat of development start for visible demonstration; not an independent test'
        if args.learned else 'Scripted smoke test without AI',
}
with (OUT / (name + '_ffmpeg.log')).open('w') as log:
    recording_info['capture_launch_unix'] = time.time()
    recorder = subprocess.Popen(['ffmpeg', '-nostdin', '-loglevel', 'warning', '-f', 'x11grab',
        '-framerate', '15', '-video_size', capture_size, '-i', ':0.0', '-an',
        '-vf', f'pad={encoded_size[0]}:{encoded_size[1]}:0:0',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-threads', '1',
        '-pix_fmt', 'yuv420p', str(video)], env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        time.sleep(1)
        if recorder.poll() is not None:
            raise RuntimeError('Recording failed; see ' + str(log.name))
        recording_info['controller_launch_unix'] = time.time()
        (OUT / (name + '_recording.json')).write_text(json.dumps(recording_info, indent=2))
        script = 'run_waypoints.py' if args.waypoints else 'evaluate_policy.py' if args.learned else 'benchmark.py'
        command = [sys.executable, str(ROOT / script), '--name', name]
        if args.learned:
            command.extend(['--trials', '1', '--observation', 'odometry_axle'])
        test = subprocess.run(command)
        if args.waypoints:
            time.sleep(3)
    finally:
        if recorder.poll() is None:
            recorder.send_signal(signal.SIGINT)
            try:
                recorder.wait(timeout=15)
            except subprocess.TimeoutExpired:
                recorder.kill()
                recorder.wait()
recording_info['recorder_exit_code'] = recorder.returncode
recording_info['controller_exit_code'] = test.returncode
try:
    recording_info['video_validation'] = validate_recording(video, recorder.returncode, encoded_size)
except RuntimeError as exc:
    recording_info['recording_error'] = str(exc)
    (OUT / (name + '_recording.json')).write_text(json.dumps(recording_info, indent=2))
    raise SystemExit('Recording failed: ' + str(exc) + '; see ' + name + '_ffmpeg.log')
recording_info['recording_success'] = True
(OUT / (name + '_recording.json')).write_text(json.dumps(recording_info, indent=2))
print('Saved', video, json.dumps(recording_info['video_validation']), flush=True)
raise SystemExit(test.returncode)
