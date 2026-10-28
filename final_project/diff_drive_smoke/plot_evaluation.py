"""Plot saved Gazebo ground-truth paths; matplotlib is an optional report tool."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
args = parser.parse_args()
summary = json.loads((args.directory / 'summary.json').read_text())
fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)
for result in summary['results']:
    with (args.directory / (result['name']+'.csv')).open() as f:
        rows = list(csv.DictReader(f))
    x = [float(r['x_true']) for r in rows]
    y = [float(r['y_true']) for r in rows]
    line, = ax.plot(x, y, label=f"{result['name']}: {result['final_true_distance_m']:.3f} m")
    ax.plot(x[0], y[0], 'o', color=line.get_color(), markersize=7)
    ax.plot(x[-1], y[-1], 'x', color=line.get_color(), markersize=8)
gx, gy = summary['results'][0]['goal']
ax.scatter([gx], [gy], s=140, marker='*', color='darkorange', label='Goal (3, 2)')
ax.add_patch(Circle((gx, gy), summary['protocol']['criteria']['true_goal_radius_m'],
                    color='orange', alpha=0.15, label='Success radius: 0.25 m'))
ax.set(xlabel='World x (m)', ylabel='World y (m)', aspect='equal',
       title=f"Learned controller in 3D Gazebo: {summary['successes']}/{summary['completed_trials']} successes\nGround-truth paths; circles = starts, crosses = stops")
ax.grid(alpha=0.25)
ax.legend(fontsize=9, loc='lower left')
fig.savefig(args.directory / 'trajectories.png', dpi=160)
print(args.directory / 'trajectories.png')
