#!/usr/bin/env bash
# Run in the supplied container. Stop only this launcher's simulator at exit.
set -eo pipefail
source /opt/ros/humble/setup.bash
set -u
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-52}"
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
export IGN_PARTITION=pai_delivery_smoke
cd "$repo_dir"
python3 tools/check_environment.py
python3 tools/verify_evidence.py
python3 -m unittest discover -s final_project/diff_drive_smoke -p test_waypoints.py -v
cd final_project/diff_drive_smoke
run_name="${1:-four_points_$(date +%Y%m%d_%H%M%S)}"
if [[ -e "results/$run_name" ]]; then
  printf 'Result already exists: %s\n' "$run_name" >&2
  exit 1
fi
python3 start_demo.py --headless --waypoints
trap 'python3 start_demo.py --stop' EXIT
ready=0
for attempt in 1 2 3 4 5; do
  if python3 evaluate_policy.py --probe; then ready=1; break; fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  printf 'Gazebo/ROS connection was not ready; inspect results/gazebo.log and bridge.log.\n' >&2
  exit 1
fi
python3 run_waypoints.py --name "$run_name"
printf 'Run complete. Read final_project/diff_drive_smoke/results/%s/summary.json\n' "$run_name"
