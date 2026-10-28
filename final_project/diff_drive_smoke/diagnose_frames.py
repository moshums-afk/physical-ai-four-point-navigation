"""Check the known wheel-axis/model-frame offset against saved baseline logs.

The offset is derived from SDF geometry, not fitted to ground-truth results.
Reports final stationary-frame errors; not an online localization algorithm.
"""
import csv
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
directory = Path(sys.argv[1])
robot = ET.parse(root / 'world.sdf').getroot().find("world/model[@name='delivery_bot']")
wheel_xy = [list(map(float, robot.find(f"link[@name='{side}_wheel']/pose").text.split()[:2]))
            for side in ('left', 'right')]
ax, ay = (sum(w[i] for w in wheel_xy)/2 for i in (0, 1))
summary = json.loads((directory / 'summary.json').read_text())
output = {'axle_center_in_model_xy_m': [ax, ay], 'note': 'Final stationary rows only; geometry-derived correction', 'trials': []}
for result in summary['results']:
    with (directory / (result['name']+'.csv')).open() as f:
        row = list(csv.DictReader(f))[-1]
    x, y, theta = (float(row[k]) for k in ('x_est', 'y_est', 'yaw_est'))
    gx, gy = (float(row[k]) for k in ('x_true', 'y_true'))
    initial = result['origin_truth'][2]
    corrected_x = x+math.cos(initial)*ax-math.sin(initial)*ay-math.cos(theta)*ax+math.sin(theta)*ay
    corrected_y = y+math.sin(initial)*ax+math.cos(initial)*ay-math.sin(theta)*ax-math.cos(theta)*ay
    output['trials'].append({'name': result['name'], 'position_error_before_m': math.hypot(x-gx, y-gy),
        'position_error_after_m': math.hypot(corrected_x-gx, corrected_y-gy)})
(directory / 'frame_diagnosis.json').write_text(json.dumps(output, indent=2))
print(json.dumps(output, indent=2))
