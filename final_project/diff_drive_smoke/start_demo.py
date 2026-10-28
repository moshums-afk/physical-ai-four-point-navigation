"""Launch the server first, then its bridge and optional GUI; track PID groups."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)
STATE = OUT / 'processes.json'

def alive(item):
    try:
        stat = Path(f'/proc/{item["pid"]}/stat').read_text().rsplit(')', 1)[1].split()
        return stat[19] == item['start_ticks'] and stat[0] != 'Z'
    except (FileNotFoundError, ProcessLookupError):
        return False

if '--stop' in sys.argv:
    if STATE.exists():
        items = json.loads(STATE.read_text())
        for item in items:
            if alive(item):
                os.killpg(item['pid'], signal.SIGINT)
                print('Stopped', item['name'])
        deadline = time.monotonic()+10
        while any(alive(item) for item in items) and time.monotonic() < deadline:
            time.sleep(0.1)
        if any(alive(item) for item in items):
            raise SystemExit('Some demo processes have not exited. Inspect logs before restarting.')
    sys.exit(0)

if STATE.exists() and any(alive(x) for x in json.loads(STATE.read_text())):
    raise SystemExit('Demo is already running. Stop it with --stop before restarting.')

env = os.environ.copy()
env.update(DISPLAY=':0', XAUTHORITY='/home/ubuntu/.Xauthority', IGN_PARTITION='pai_delivery_smoke')
commands = [
    # An explicit server avoids the combined launcher's starting-world handshake,
    # which left the server and GUI waiting for one another in the desktop image.
    ('gazebo', ['ign', 'gazebo', '-s', '-r', '-v', '2',
        str(ROOT / ('world_waypoints.sdf' if '--waypoints' in sys.argv else 'world.sdf'))]),
    ('bridge', ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
        '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
        '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
        '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
        '/model/delivery_bot/pose@geometry_msgs/msg/PoseStamped[ignition.msgs.Pose',
        '--ros-args', '-r', '__node:=delivery_smoke_bridge']),
]
if '--headless' not in sys.argv:
    commands.append(('gui', ['ign', 'gazebo', '-g', '-v', '2', '--gui-config',
        str(ROOT / ('gui_waypoints.config' if '--waypoints' in sys.argv else 'gui.config'))]))
state = []
try:
    for name, command in commands:
        with (OUT / (name + '.log')).open('a') as log:
            proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
        ticks = Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
        state.append({'name': name, 'pid': proc.pid, 'start_ticks': ticks, 'headless': '--headless' in sys.argv,
                      'waypoints': '--waypoints' in sys.argv})
        STATE.write_text(json.dumps(state, indent=2))
except BaseException:
    for item in state:
        if alive(item):
            os.killpg(item['pid'], signal.SIGINT)
    raise
print(json.dumps(state))
